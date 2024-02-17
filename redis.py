import socket
import asyncio


async def parse_response(response):
    """Parse RESP data and return the command and its arguments"""
    lines = response.split(b"\r\n")
    command = lines[2].decode().lower()  # Convert command to lowercase to make it case-insensitive
    if command == "echo":
        # Extract the message to echo, which is the next line in the array
        message = lines[4].decode()
        return command, message

    return command, None


async def handle_client(reader, writer):
    pong = b"+PONG\r\n"

    while True:
        data = await reader.read(1024)
        if not data:
            break
        command, message = await parse_response(data)
        if command == "echo":
            response = f"${len(message)}\r\n{message}\r\n"
        else:
            response = "+PONG\r\n"
        writer.write(response.encode())
        await writer.drain()
    writer.close()


async def main():
    server = await asyncio.start_server(handle_client, 'localhost', 6379)
    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(main())