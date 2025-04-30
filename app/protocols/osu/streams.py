
from twisted.internet.protocol import Protocol

class ByteStream:
    """Helper class for streams in twisted."""

    def __init__(self, client: Protocol) -> None:
        self.client = client
        self.offset = 0
        self.data = b""

    def __add__(self, data: bytes) -> "ByteStream":
        self.append(data)
        return self

    def __repr__(self):
        return f"{self.data}"

    def write(self, data: bytes) -> None:
        self.client.enqueue(data)

    def read(self, size: int = -1) -> bytes:
        if size < 0:
            return self.readall()

        if self.offset + size > len(self.data):
            raise OverflowError(f"{size} exceeds available data {len(self.data) - self.offset}")

        data = self.data[self.offset:self.offset + size]
        self.offset += size
        return data

    def readall(self) -> bytes:
        data = self.data[self.offset:]
        self.offset = len(self.data)
        return data

    def append(self, data: bytes) -> None:
        self.data += data

    def seek(self, offset: int) -> None:
        self.offset = offset

    def available(self) -> int:
        return len(self.data) - self.offset

    def reset(self) -> None:
        self.data = self.data[self.offset:]
        self.offset = 0

    def clear(self) -> None:
        self.data = b""
        self.offset = 0

    def count(self, byte: bytes) -> int:
        return self.data.count(byte)
    
    def split(self, byte: bytes, maxsplit: int = -1) -> tuple[bytes, ...]:
        parts = self.data.split(byte, maxsplit)
        return parts
