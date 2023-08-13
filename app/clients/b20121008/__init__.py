
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
