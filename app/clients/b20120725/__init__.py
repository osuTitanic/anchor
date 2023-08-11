
"""
b20120725 uses protocol version 8, as far as I am aware.
It has some changes in the bChannel type.
"""

from .. import (
    DefaultResponsePacket as ResponsePacket,
    DefaultRequestPacket as RequestPacket
)

from .writer import Writer

from ..packets import PACKETS
from copy import deepcopy

# Inherit packets from 20120812
PACKETS[20120725] = deepcopy(PACKETS[20120812])

from . import encoder
