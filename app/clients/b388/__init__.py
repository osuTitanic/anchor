
from ..b1700.constants import (
    ResponsePacket,
    RequestPacket
)

from ..packets import PACKETS
from copy import deepcopy

# Inherit packets from 392
PACKETS[388] = deepcopy(PACKETS[392])
PACKETS[339] = deepcopy(PACKETS[392])

from . import encoder
