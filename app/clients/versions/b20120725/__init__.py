
from ... import (
    DefaultResponsePacket as ResponsePacket,
    DefaultRequestPacket as RequestPacket
)

from .writer import Writer

from ...packets import PACKETS
from copy import deepcopy

# Inherit packets from 20120812
PACKETS[20120725] = deepcopy(PACKETS[20120812])

from . import encoder
