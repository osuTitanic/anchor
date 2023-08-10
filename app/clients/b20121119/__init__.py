
"""
Protocol version 11 is supported from b20121119 to b20121030.
It has a few changes regarding user presence.
"""

from .. import (
    DefaultResponsePacket as ResponsePacket,
    DefaultRequestPacket as RequestPacket
)

from .writer import Writer

from ..packets import PACKETS
from copy import deepcopy

# Inherit packets from 20121223
PACKETS[20121119] = deepcopy(PACKETS[20121223])
PACKETS[20121030] = deepcopy(PACKETS[20121223])

from . import encoder
