
from ..b1700.constants import (
    ResponsePacket,
    RequestPacket
)

from .writer import Writer
from .reader import Reader

from ..packets import PACKETS
from copy import deepcopy

# Inherit packets from 338
PACKETS[337] = deepcopy(PACKETS[338])

from . import encoder
from . import decoder
