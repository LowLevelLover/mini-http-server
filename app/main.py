import asyncio
import socket
import logging

from collections import UserDict
from typing import Self, override

BUFF_SIZE = 1024
RESP_404 = b"HTTP/1.1 404 Not Found\r\n\r\n"
RESP_200 = b"HTTP/1.1 200 OK\r\n\r\n"
HOST = "localhost"
PORT = 4221

# Initialize Logger
logging.basicConfig(
    level=logging.INFO,  # Change to DEBUG for more details
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
    def from_list(cls, headers_raw: list[str]) -> Self:
        headers: dict[str, str] = {}
        for header in headers_raw:
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
    body: str | None

    def __init__(
        self, req_line: HttpReqLine, headers: HttpHeaders, body: str | None = None
    ) -> None:
        if body is not None and len(body.strip()) == 0:
            body = None

        self.req_line = req_line
        self.headers = headers
        self.body = body

    @classmethod
    def from_str(cls, text: str) -> Self:
        [first, *second, last] = text.splitlines()

        req_line = HttpReqLine.from_str(first)
        headers = HttpHeaders.from_list(second)

        return cls(req_line, headers, last)


def echo_handler(text: str):
    headers = HttpHeaders(
        {"Content-Type": "text/plain", "Content-Length": str(len(text))}
    )
    return b"\r\n".join([b"HTTP/1.1 200 OK", headers.to_bytes(), text.encode("utf-8")])


def user_agent_handler(req: HttpRequest):
    user_agent = req.headers.get("User-Agent")
    if user_agent is None:
        raise LookupError("User-Agent is not in headers")

    headers = HttpHeaders(
        {"Content-Type": "text/plain", "Content-Length": str(len(user_agent))}
    )

    return b"\r\n".join(
        [b"HTTP/1.1 200 OK", headers.to_bytes(), user_agent.encode("utf-8")]
    )


async def handle_client(client: socket.socket, loop: asyncio.AbstractEventLoop):
    addr: tuple[str, int] = client.getpeername()  # (address, port) for AF_INET
    logger.info(f"[CONNECTED] {addr[0]}:{addr[1]}")

    try:
        while True:
            req = await loop.sock_recv(client, BUFF_SIZE)
            if not req:
                break

            req = req.decode()
            logger.info(f"[RECEIVED from {addr[0]}:{addr[1]}] {req!r}")

            http_request = HttpRequest.from_str(req)

            match http_request.req_line.path.split("/")[1:]:
                case [""]:
                    await loop.sock_sendall(client, RESP_200)

                case ["echo", text]:
                    await loop.sock_sendall(client, echo_handler(text))

                case ["user-agent"]:
                    await loop.sock_sendall(client, user_agent_handler(http_request))

                case _:
                    await loop.sock_sendall(client, RESP_404)
    except Exception as e:
        logger.exception(f"[ERROR] {e}")

    finally:
        logger.info(f"[DISCONNECTED] {addr[0]}:{addr[1]}")
        client.close()


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
