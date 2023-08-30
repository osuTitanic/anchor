
from enum import IntEnum
from typing import Dict

class PacketEnum(IntEnum):
    ...

    def __eq__(self, other: IntEnum) -> bool:
        return self.name == other.name

    def __hash__(self) -> int:
        return hash(self.name)

# Here is an overview of all supported packet versions
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
    1807:     [{}, {}, PacketEnum, PacketEnum], # 7
    1700:     [{}, {}, PacketEnum, PacketEnum], # 6
    1152:     [{}, {}, PacketEnum, PacketEnum], # 6
                                                # 5 ?
    1150:     [{}, {}, PacketEnum, PacketEnum], # 4
    679:      [{}, {}, PacketEnum, PacketEnum], # 4
    675:      [{}, {}, PacketEnum, PacketEnum], # 4 (UserStats)
    591:      [{}, {}, PacketEnum, PacketEnum], # 4 (UserStats)
    590:      [{}, {}, PacketEnum, PacketEnum], # 4 (NoMatchPasswords)
    558:      [{}, {}, PacketEnum, PacketEnum], # 4 (NoMatchPasswords)
    553:      [{}, {}, PacketEnum, PacketEnum], # 3
    536:      [{}, {}, PacketEnum, PacketEnum], # 3
    535:      [{}, {}, PacketEnum, PacketEnum], # 2
    504:      [{}, {}, PacketEnum, PacketEnum], # 2
    503:      [{}, {}, PacketEnum, PacketEnum], # 1
    487:      [{}, {}, PacketEnum, PacketEnum], # 1
    483:      [{}, {}, PacketEnum, PacketEnum], # 0
    402:      [{}, {}, PacketEnum, PacketEnum], # 0
    399:      [{}, {}, PacketEnum, PacketEnum], # 0 (NoHostId)
    392:      [{}, {}, PacketEnum, PacketEnum], # 0 (NoHostId)
    388:      [{}, {}, PacketEnum, PacketEnum]  # 0 (NoApprovedStatus)
}
