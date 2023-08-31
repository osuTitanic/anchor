
from .constants import (
    ResponsePacket,
    RequestPacket
)

from .writer import Writer
from .reader import Reader

from ..packets import PACKETS
from copy import deepcopy

# Inherit packets from 339
PACKETS[338] = deepcopy(PACKETS[339])

PACKETS[338][2] = RequestPacket
PACKETS[338][3] = ResponsePacket

from . import encoder
from . import decoder
