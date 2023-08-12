
from .constants import RequestPacket, ResponsePacket

from .reader import Reader
from .writer import Writer

from . import decoder
from . import encoder

from ..packets import PACKETS

PACKETS[20130606][2] = RequestPacket
PACKETS[20130606][3] = ResponsePacket
PACKETS[20130418][2] = RequestPacket
PACKETS[20130418][3] = ResponsePacket
