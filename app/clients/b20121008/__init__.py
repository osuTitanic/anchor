
"""
This should be around protocol version 12, which is used by b20121008 up to b20120916.
It has some changes in the bBeatmapInfoReply.
"""

from .. import (
    DefaultResponsePacket as ResponsePacket,
    DefaultRequestPacket as RequestPacket
)

from .writer import Writer

from ..packets import PACKETS
from copy import deepcopy

# Inherit packets from 20121119
PACKETS[20121008] = deepcopy(PACKETS[20121119])
PACKETS[20120916] = deepcopy(PACKETS[20121119])

from . import encoder
