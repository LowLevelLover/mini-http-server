import socket
from collections import UserDict
from typing import Self, override

BUFF_SIZE = 1024
RESP_404 = b"HTTP/1.1 404 Not Found\r\n\r\n"
RESP_200 = b"HTTP/1.1 200 OK\r\n\r\n"


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
    return b"\r\n".join(
        [b"HTTP/1.1 200 OK", headers.to_bytes(), text.encode("utf-8")]
    )

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


def main():
    server_socket = socket.create_server(("localhost", 4221), reuse_port=True)
    client = server_socket.accept()[0]  # wait for client

    req = client.recv(BUFF_SIZE).decode()

    http_request = HttpRequest.from_str(req)

    match http_request.req_line.path.split("/")[1:]:
        case [""]:
            client.sendall(RESP_200)

        case ["echo", text]:
            client.sendall(echo_handler(text))

        case ["user-agent"]:
            client.sendall(user_agent_handler(http_request))

        case _:
            client.sendall(RESP_404)


if __name__ == "__main__":
    main()
