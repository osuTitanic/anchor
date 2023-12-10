
from ..b1700.constants import (
    ResponsePacket,
    RequestPacket
)

from .writer import Writer
from .reader import Reader

from ...packets import PACKETS
from copy import deepcopy

# Inherit packets from 591
PACKETS[590] = deepcopy(PACKETS[591])
PACKETS[558] = deepcopy(PACKETS[591])

from . import encoder
from . import decoder
