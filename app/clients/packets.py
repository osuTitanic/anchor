
from typing import Dict, Callable, Tuple
from enum import Enum

from .b20130606 import PacketSender as b20130606

from .sender import BaseSender

PACKETS: Dict[
    int,
    Tuple[Dict[Enum, Callable], BaseSender]
] = {
    2013606: ({}, b20130606)
    # Implement more clients here ...
}
