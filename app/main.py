import asyncio
import gzip
from pathlib import Path
import socket
import logging

from collections import UserDict
import sys
from typing import Self, override

BUFF_SIZE = 1024
HOST = "localhost"
PORT = 4221

RESP_404 = b"HTTP/1.1 404 Not Found\r\n\r\n"
RESP_200 = b"HTTP/1.1 200 OK\r\n\r\n"
RESP_201 = b"HTTP/1.1 201 Created\r\n\r\n"

# Initialize Logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


class HttpReqLine:
    __slots__: list[str] = ["method", "path", "version"]

    method: str
    path: str
    version: str

    def __init__(self, method: str, path: str, version: str) -> None:
        self.method = method
        self.path = path
        self.version = version

    @classmethod
    def from_str(cls, text: str) -> Self:
        parts = text.strip().split(" ")
        if len(parts) != 3:
            raise ValueError(f"Invalid HTTP request line: {text}")

        return cls(*parts)

    @override
    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}(method={self.method!r}, "
            f"path={self.path!r}, http_version={self.version!r})"
        )


class HttpHeaders(UserDict[str, str]):
    @classmethod
    def from_list(cls, headers_raw: list[bytes]) -> Self:
        headers: dict[str, str] = {}
        for header in headers_raw:
            header = header.decode("utf-8")
            if ":" not in header:
                continue
            key, value = header.split(":", 1)
            headers[key.strip()] = value.strip()
        return cls(headers)

    @override
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.data!r})"

    def to_bytes(self) -> bytes:
        return b"".join(
            f"{key}: {value}\r\n".encode("utf-8") for key, value in self.data.items()
        )


class HttpRequest:
    __slots__: list[str] = ["req_line", "headers", "body"]

    req_line: HttpReqLine
    headers: HttpHeaders
    body: bytes | None

    def __init__(
        self, req_line: HttpReqLine, headers: HttpHeaders, body: bytes | None = None
    ) -> None:
        if body is not None and len(body.strip()) == 0:
            body = None

        self.req_line = req_line
        self.headers = headers
        self.body = body

    @classmethod
    def from_str(cls, text: bytes) -> Self:
        [first, *second, last] = text.splitlines()

        req_line = HttpReqLine.from_str(first.decode("utf-8"))
        headers = HttpHeaders.from_list(second)

        return cls(req_line, headers, last)

    @override
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(req_line={self.req_line!r}, headers={self.headers!r}, body={self.body!r})"


class HttpResponse:
    __slots__: list[str] = ["status", "headers", "body"]

    status: str
    headers: HttpHeaders
    body: bytes

    def __init__(
        self,
        status: str,
        headers: HttpHeaders,
        body: bytes | None = None,
        compression: str | None = None,
    ) -> None:
        self.status = status
        self.headers = headers

        if compression is not None and "gzip" in compression:
            self.body = gzip.compress(body or b"")
            self.headers["Content-Length"] = str(len(self.body))
            self.headers["Content-Encoding"] = "gzip"
        else:
            self.body = body or b""
            self.headers["Content-Length"] = str(len(self.body))

    def to_bytes(self):
        status_line = f"HTTP/1.1 {self.status}".encode("utf-8")
        return b"\r\n".join([status_line, self.headers.to_bytes(), self.body])

    @override
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(status={self.status!r}, headers={self.headers!r}, body={self.body!r})"


def echo_handler(text: bytes, req_headers: HttpHeaders) -> bytes:
    headers = HttpHeaders(
        {"Content-Type": "text/plain", "Content-Length": str(len(text))}
    )
    resp = HttpResponse(
        "200 OK", headers, body=text, compression=req_headers.get("Accept-Encoding")
    )
    return resp.to_bytes()


def user_agent_handler(req: HttpRequest):
    user_agent = req.headers.get("User-Agent")
    if user_agent is None:
        raise LookupError("User-Agent is not in headers")

    headers = HttpHeaders(
        {"Content-Type": "text/plain", "Content-Length": str(len(user_agent))}
    )

    resp = HttpResponse("200 OK", headers, user_agent.encode("utf-8"))
    return resp.to_bytes()


def files_get_handler(file_name: str, req_headers: HttpHeaders):
    directory = get_directory()
    if directory is None:
        return RESP_404

    try:
        with open(directory + file_name, "rb") as f:
            content = f.read()
            headers = HttpHeaders(
                {
                    "Content-Type": "application/octet-stream",
                    "Content-Length": str(len(content)),
                }
            )

            resp = HttpResponse(
                "200 OK",
                headers,
                body=content,
                compression=req_headers.get("Accept-Encoding"),
            )
            return resp.to_bytes()

    except FileNotFoundError:
        return RESP_404


def files_post_handler(file_name: str, content: bytes):
    directory = get_directory()
    if directory is None:
        raise ValueError("The directory of files path is not provided")

    Path(directory).mkdir(parents=True, exist_ok=True)

    with open(directory + file_name, "wb") as f:
        _ = f.write(content)
        return RESP_201


async def handle_client(client: socket.socket, loop: asyncio.AbstractEventLoop):
    addr: tuple[str, int] = client.getpeername()  # (address, port) for AF_INET
    logger.info(f"[CONNECTED] {addr[0]}:{addr[1]}")

    try:
        while True:
            req = await loop.sock_recv(client, BUFF_SIZE)
            logger.info(f"[RECEIVED from {addr[0]}:{addr[1]}] {req!r}")

            if req == b"":
                break

            http_request = HttpRequest.from_str(req)

            match http_request.req_line.path.split("/")[1:]:
                case [""]:
                    await loop.sock_sendall(client, RESP_200)

                case ["echo", text]:
                    await loop.sock_sendall(
                        client, echo_handler(text.encode("utf-8"), http_request.headers)
                    )

                case ["user-agent"]:
                    await loop.sock_sendall(client, user_agent_handler(http_request))

                case ["files", file_name] if http_request.req_line.method == "GET":
                    await loop.sock_sendall(
                        client, files_get_handler(file_name, http_request.headers)
                    )

                case ["files", file_name] if http_request.req_line.method == "POST":
                    await loop.sock_sendall(
                        client, files_post_handler(file_name, http_request.body or b"")
                    )

                case _:
                    await loop.sock_sendall(client, RESP_404)

            if (
                http_request.headers.get("Connection") == "close"
                or http_request.req_line.version != "HTTP/1.1"
            ):
                break

    except Exception as e:
        logger.exception(f"[ERROR] {e}")

    finally:
        logger.info(f"[DISCONNECTED] {addr[0]}:{addr[1]}")
        client.close()


def get_directory():
    if len(sys.argv) == 3 and sys.argv[1] == "--directory":
        return sys.argv[2]


async def main():
    server = socket.create_server((HOST, PORT), family=socket.AF_INET, reuse_port=True)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.setblocking(False)

    loop = asyncio.get_running_loop()
    logger.info(f"[SERVER STARTED] Listening on {HOST}:{PORT}")

    while True:
        sock = await loop.sock_accept(server)
        client = sock[0]
        client.setblocking(False)

        _ = asyncio.create_task(handle_client(client, loop))


if __name__ == "__main__":
    asyncio.run(main())
