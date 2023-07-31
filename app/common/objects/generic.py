
from app.common.streams import StreamIn

from dataclasses import dataclass
from enum import Enum

@dataclass
class BanchoPacket:
    packet: Enum
    compression: bool
    payload: StreamIn
