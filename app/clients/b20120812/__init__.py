
"""
This is protocol version 10, which was used in b20120812 and earlier.
There are changes in the bStatusUpdate and bMatch types.
"""

from .. import (
    DefaultResponsePacket as ResponsePacket,
    DefaultRequestPacket as RequestPacket
)

from .reader import Reader
from .writer import Writer

from ..packets import PACKETS
from copy import deepcopy

# Inherit packets from 20121008
PACKETS[20120812] = deepcopy(PACKETS[20121008])

from . import encoder
from . import decoder
