
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
