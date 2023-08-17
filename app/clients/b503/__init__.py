
from ..b1700.constants import (
    ResponsePacket,
    RequestPacket
)

from .writer import Writer

from ..packets import PACKETS
from copy import deepcopy

# Inherit packets from 536
PACKETS[503] = deepcopy(PACKETS[504])

from . import encoder
