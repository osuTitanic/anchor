
from twisted.internet.protocol import Protocol

class ByteStream:
    """Helper class for streams in twisted"""

    __slots__ = ('client', 'offset', 'buffer')

    def __init__(self, client: Protocol) -> None:
        self.client = client
        self.offset = 0
        self.buffer = bytearray()

    def __repr__(self):
        return self.buffer.__repr__()

    def __len__(self):
        return len(self.buffer)

    def __iadd__(self, data: bytes) -> "ByteStream":
        self.append(data)
        return self

    def write(self, data: bytes) -> None:
        self.client.enqueue(data)

    def read(self, size: int = -1) -> bytearray:
        if size < 0:
            return self.readall()

        if self.offset + size > len(self.buffer):
            raise OverflowError(f"{size} exceeds available data {len(self.buffer) - self.offset}")

        result = self.buffer[self.offset:self.offset + size]
        self.offset += size
        return result

    def readall(self) -> bytearray:
        result = self.buffer[self.offset:]
        self.offset = len(self.buffer)
        return result

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

    def split(self, byte: bytes, maxsplit: int = -1) -> tuple[bytearray, ...]:
        return self.buffer.split(byte, maxsplit)
