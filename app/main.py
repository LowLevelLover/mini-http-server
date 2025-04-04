import socket

BUFF_SIZE = 1024


def main():
    server_socket = socket.create_server(("localhost", 4221), reuse_port=True)
    client, ip = server_socket.accept()  # wait for client

    req = client.recv(BUFF_SIZE).decode()
    req_line = req.split("\r\n")[0]
    [method, path, version] = req_line.split(" ")

    RESP_404 = b"HTTP/1.1 404 Not Found\r\n\r\n"
    RESP_200 = b"HTTP/1.1 200 OK\r\n\r\n"

    match path:
        case "/":
            client.sendall(RESP_200)
        case _:
            client.sendall(RESP_404)


if __name__ == "__main__":
    main()
