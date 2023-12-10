
from ..b1700.constants import (
    ResponsePacket,
    RequestPacket
)

from .writer import Writer
from .reader import Reader

from ...packets import PACKETS
from copy import deepcopy

# Inherit packets from 558
PACKETS[553] = deepcopy(PACKETS[558])
PACKETS[536] = deepcopy(PACKETS[558])

from . import encoder
from . import decoder
