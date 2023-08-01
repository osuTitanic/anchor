
from typing import Dict, Callable, Tuple
from enum import IntEnum

class PacketEnum(IntEnum):
    ...

    def __eq__(self, other: IntEnum) -> bool:
        return self.name == other.name

    def __hash__(self) -> int:
        return hash(self.name)

PACKETS: Dict[
    int,
    Tuple[
        Dict[PacketEnum, Callable], # RequestPackets
        Dict[PacketEnum, Callable]  # ResponsePackets
    ]
] = {
    2013606: ({}, {})
    # Implement more clients here ...
}
