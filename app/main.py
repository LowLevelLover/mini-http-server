import socket


def main():
    server_socket = socket.create_server(("localhost", 4221), reuse_port=True)
    client, ip = server_socket.accept()  # wait for client

    response = b"HTTP/1.1 200 OK\r\n\r\n"
    client.sendall(response)


if __name__ == "__main__":
    main()
