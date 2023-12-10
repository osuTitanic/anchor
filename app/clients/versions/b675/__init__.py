
from ..b1700.constants import (
    ResponsePacket,
    RequestPacket
)

from .writer import Writer

from ...packets import PACKETS
from copy import deepcopy

# Inherit packets from 679
PACKETS[675] = deepcopy(PACKETS[679])
PACKETS[591] = deepcopy(PACKETS[679])

from . import encoder
