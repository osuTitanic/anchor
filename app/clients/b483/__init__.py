
from ..b1700.constants import (
    ResponsePacket,
    RequestPacket
)

from .writer import Writer
from .reader import Reader

from ..packets import PACKETS
from copy import deepcopy

# Inherit packets from 487
PACKETS[483] = deepcopy(PACKETS[487])

from . import encoder
from . import decoder
