
from ... import (
    DefaultResponsePacket as ResponsePacket,
    DefaultRequestPacket as RequestPacket
)

from ...packets import PACKETS
from copy import deepcopy

# Inherit packets from 20130815
PACKETS[20130329] = deepcopy(PACKETS[20130815])
PACKETS[20130118] = deepcopy(PACKETS[20130815])

from .writer import Writer
from .reader import Reader

from . import decoder
from . import encoder
