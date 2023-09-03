
from ..b338.constants import (
    ResponsePacket,
    RequestPacket
)

from .writer import Writer
from .reader import Reader

from ..packets import PACKETS
from copy import deepcopy

# Inherit packets from 334
PACKETS[323] = deepcopy(PACKETS[334])

from . import encoder
from . import decoder
