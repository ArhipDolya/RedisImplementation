import socket


def main():
    pong = b"+PONG\r\n"

    server_socket = socket.create_server(("localhost", 6379), reuse_port=True)
    client, client_address = server_socket.accept()

    with client:
        client.recv(1024)
        client.send(pong)


if __name__ == "__main__":
    main()
