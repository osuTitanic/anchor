
from .. import (
    DefaultResponsePacket as ResponsePacket,
    DefaultRequestPacket as RequestPacket
)

from ..packets import PACKETS
from copy import deepcopy

# Inherit packets from 20130606
PACKETS[20130329] = deepcopy(PACKETS[20130606])
PACKETS[20130303] = deepcopy(PACKETS[20130606])

from .writer import Writer
from .reader import Reader

from . import decoder
from . import encoder
