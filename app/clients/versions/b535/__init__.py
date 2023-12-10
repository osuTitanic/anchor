
from ..b1700.constants import (
    ResponsePacket,
    RequestPacket
)

from .writer import Writer
from .reader import Reader

from ...packets import PACKETS
from copy import deepcopy

# Inherit packets from 536
PACKETS[535] = deepcopy(PACKETS[536])
PACKETS[504] = deepcopy(PACKETS[536])

from . import encoder
from . import decoder
