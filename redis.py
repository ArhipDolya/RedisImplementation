import socket
import asyncio


async def handle_client(reader, writer):
    pong = b"+PONG\r\n"

    while True:
        data = await reader.read(1024)
        if not data:
            break
        writer.write(pong)
        await writer.drain()
    writer.close()


async def main():
    server = await asyncio.start_server(handle_client, "localhost", 6379)

    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(main())