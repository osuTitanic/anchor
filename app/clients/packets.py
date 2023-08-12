
from enum import IntEnum
from typing import Dict

class PacketEnum(IntEnum):
    ...

    def __eq__(self, other: IntEnum) -> bool:
        return self.name == other.name

    def __hash__(self) -> int:
        return hash(self.name)

PACKETS: Dict[int, list] = {
    20130815: [{}, {}, PacketEnum, PacketEnum], # 18
    20130401: [{}, {}, PacketEnum, PacketEnum], # 18
    20130329: [{}, {}, PacketEnum, PacketEnum], # 17
                                                # 16 ?
    20130118: [{}, {}, PacketEnum, PacketEnum], # 15
                                                # 14 ?
    20121223: [{}, {}, PacketEnum, PacketEnum], # 13
    20121203: [{}, {}, PacketEnum, PacketEnum], # 13
    20121119: [{}, {}, PacketEnum, PacketEnum], # 12
    20121030: [{}, {}, PacketEnum, PacketEnum], # 12
    20121008: [{}, {}, PacketEnum, PacketEnum], # 11
    20120916: [{}, {}, PacketEnum, PacketEnum], # 11
    20120812: [{}, {}, PacketEnum, PacketEnum], # 10
    20120725: [{}, {}, PacketEnum, PacketEnum], # 8
    20120704: [{}, {}, PacketEnum, PacketEnum], # 7
    1807:     [{}, {}, PacketEnum, PacketEnum]  # 7
}
