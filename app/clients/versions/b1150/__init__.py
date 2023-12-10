
from ..b1700.constants import (
    ResponsePacket,
    RequestPacket
)

from .writer import Writer

from ...packets import PACKETS
from copy import deepcopy

# Inherit packets from 1700
PACKETS[1150] = deepcopy(PACKETS[1700])
PACKETS[679] = deepcopy(PACKETS[1700])

from . import encoder
