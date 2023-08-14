
from .constants import (
    ResponsePacket,
    RequestPacket
)

from .reader import Reader
from .writer import Writer

from ..packets import PACKETS
from copy import deepcopy

# Inherit packets from 20120704
PACKETS[1700] = deepcopy(PACKETS[20120704])
PACKETS[1152] = deepcopy(PACKETS[20120704])
# PACKETS[1807] = deepcopy(PACKETS[20120704]) ?

PACKETS[1700][2] = RequestPacket
PACKETS[1700][3] = ResponsePacket
PACKETS[1152][2] = RequestPacket
PACKETS[1152][3] = ResponsePacket

from . import encoder
from . import decoder
