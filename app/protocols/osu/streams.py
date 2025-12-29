
from twisted.internet.protocol import Protocol

class ByteStream:
    """Helper class for streams in twisted"""

    __slots__ = ('client', 'offset', 'buffer')

    def __init__(self, client: Protocol) -> None:
        self.client = client
        self.offset = 0
        self.buffer = bytearray()

    @property
    def data(self) -> bytes:
        return bytes(self.buffer)

    def __add__(self, data: bytes) -> "ByteStream":
        self.append(data)
        return self

    def __repr__(self):
        return f"{bytes(self.buffer)}"

    def write(self, data: bytes) -> None:
        self.client.enqueue(data)

    def read(self, size: int = -1) -> bytes:
        if size < 0:
            return self.readall()

        if self.offset + size > len(self.buffer):
            raise OverflowError(f"{size} exceeds available data {len(self.buffer) - self.offset}")

        data = bytes(self.buffer[self.offset:self.offset + size])
        self.offset += size
        return data

    def readall(self) -> bytes:
        data = bytes(self.buffer[self.offset:])
        self.offset = len(self.buffer)
        return data

    def append(self, data: bytes) -> None:
        self.buffer.extend(data)

    def seek(self, offset: int) -> None:
        self.offset = offset

    def available(self) -> int:
        return len(self.buffer) - self.offset

    def reset(self) -> None:
        del self.buffer[:self.offset]
        self.offset = 0

    def clear(self) -> None:
        self.buffer.clear()
        self.offset = 0

    def count(self, byte: bytes) -> int:
        return self.buffer.count(byte)
    
    def split(self, byte: bytes, maxsplit: int = -1) -> tuple[bytes, ...]:
        parts = bytes(self.buffer).split(byte, maxsplit)
        return parts
