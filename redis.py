import asyncio
import time
import argparse


class KeyValueStore:
    """A simple in-memory key-value store"""

    def __init__(self):
        self.store = {}
        self.master_replid = "8371b4fb1155b71f4a04d3e1bc3e18c4a990aeeb"  # Hardcoded replication ID
        self.master_repl_offset = 0

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
        elif command == "info":
            arg = None
            if len(lines) > 4:
                arg = lines[4].decode().lower()
            return command, [arg] if arg else []
        return command, []


class ClientHandler:
    """Handles client connections and requests"""

    def __init__(self, key_value_store, command_parser: CommandParser, role='master'):
        self.key_value_store = key_value_store
        self.command_parser = command_parser
        self.role = role

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
        elif command == 'info':
            if args and args[0].lower() == 'replication':
                info_response = (
                    f"role:{self.role}\r\n"
                    f"master_replid:{self.key_value_store.master_replid}\r\n"
                    f"master_repl_offset:{self.key_value_store.master_repl_offset}"
                )
                return f"${len(info_response)}\r\n{info_response}\r\n"
            else:
                return "$0\r\n\r\n"
        return "+PONG\r\n"


def parse_arguments():
    parser = argparse.ArgumentParser(description='Redis-like server with support for custom ports and replication')
    parser.add_argument('--port', type=int, default=6379, help='Port number to start the Redis server on')
    parser.add_argument('--replicaof', nargs=2, metavar=('MASTER_HOST', 'MASTER_PORT'),
                        help='Run as a replica of the specified master server')
    args = parser.parse_args()
    return args.port, args.replicaof


async def main():
    port, replicaof = parse_arguments()  # Get the port number from command-line arguments
    role = 'slave' if replicaof else 'master'

    store = KeyValueStore()
    command_parser = CommandParser()
    handler = ClientHandler(store, command_parser, role=role)

    server = await asyncio.start_server(handler.handle, 'localhost', port)
    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(main())