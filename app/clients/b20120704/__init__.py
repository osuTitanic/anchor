
from .. import (
    DefaultResponsePacket as ResponsePacket,
    DefaultRequestPacket as RequestPacket
)

from .writer import Writer

from ..packets import PACKETS
from copy import deepcopy

# Inherit packets from 20120725
PACKETS[20120704] = deepcopy(PACKETS[20120725])

from . import encoder
