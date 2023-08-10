
from enum import IntEnum
from typing import Dict

class PacketEnum(IntEnum):
    ...

    def __eq__(self, other: IntEnum) -> bool:
        return self.name == other.name

    def __hash__(self) -> int:
        return hash(self.name)

PACKETS: Dict[int, list] = {
    20130606: [{}, {}, PacketEnum, PacketEnum],
    20130418: [{}, {}, PacketEnum, PacketEnum],
    20130329: [{}, {}, PacketEnum, PacketEnum],
    20130303: [{}, {}, PacketEnum, PacketEnum]
    # Implement more clients here ...
}
