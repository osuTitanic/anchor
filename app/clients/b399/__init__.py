
from ..b1700.constants import (
    ResponsePacket,
    RequestPacket
)

from .writer import Writer
from .reader import Reader

from ..packets import PACKETS
from copy import deepcopy

# Inherit packets from 402
PACKETS[399] = deepcopy(PACKETS[402])

from . import encoder
from . import decoder
