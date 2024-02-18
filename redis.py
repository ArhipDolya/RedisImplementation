import asyncio
import time

class KeyValueStore:
    """A simple in-memory key-value store"""
    def __init__(self):
        self.store = {}

    def set(self, key, value, px=None):
        expiry = time.time() * 1000 + px if px is not None else None
        self.store[key] = (value, expiry)

    def get(self, key):
        item = self.store.get(key, None)
        if item is not None:
            value, expiry = item
            if expiry is None or expiry > time.time() * 1000:
                return value
            else:
                del self.store[key]
        return None

class CommandParser:
    """Parses RESP data into commands and arguments"""
    async def parse(self, response):
        lines = response.split(b"\r\n")
        command = lines[2].decode().lower()
        if command == "echo":
            message = lines[4].decode()
            return command, [message]
        elif command == "set":
            key = lines[4].decode()
            value = lines[6].decode()
            px = None
            if len(lines) > 8 and lines[8].decode().lower() == "px":
                try:
                    px = int(lines[10].decode())
                except ValueError:
                    pass
            return command, [key, value, px]
        elif command == "get":
            key = lines[4].decode()
            return command, [key]
        return command, []

class ClientHandler:
    """Handles client connections and requests"""
    def __init__(self, key_value_store, command_parser: CommandParser):
        self.key_value_store = key_value_store
        self.command_parser = command_parser

    async def handle(self, reader, writer):
        while True:
            data = await reader.read(1024)
            if not data:
                break
            command, args = await self.command_parser.parse(data)
            response = self.process_command(command, args)
            writer.write(response.encode())
            await writer.drain()
        writer.close()

    def process_command(self, command, args):
        if command == "echo":
            return f"${len(args[0])}\r\n{args[0]}\r\n"
        elif command == "set":
            key, value = args[:2]
            px = args[2] if len(args) > 2 else None
            self.key_value_store.set(key, value, px)
            return "+OK\r\n"
        elif command == "get":
            key = args[0]
            value = self.key_value_store.get(key)
            if value is not None:
                return f"${len(value)}\r\n{value}\r\n"
            else:
                return "$-1\r\n"
        return "+PONG\r\n"

async def main():
    store = KeyValueStore()
    command_parser = CommandParser()
    handler = ClientHandler(store, command_parser)

    server = await asyncio.start_server(handler.handle, 'localhost', 6379)
    async with server:
        await server.serve_forever()

if __name__ == "__main__":
    asyncio.run(main())