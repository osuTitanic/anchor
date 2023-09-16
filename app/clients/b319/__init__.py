
from ..b323 import (
    ResponsePacket,
    RequestPacket
)

from .writer import Writer
from .reader import Reader

from ..packets import PACKETS
from copy import deepcopy

# Inherit packets from 319
PACKETS[319] = deepcopy(PACKETS[323])

from . import encoder
from . import decoder
