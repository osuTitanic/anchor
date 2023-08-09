
from .constants import RequestPacket, ResponsePacket

from .reader import Reader
from .writer import Writer

from . import decoder
from . import encoder

from ..packets import PACKETS

PACKETS[2013606][2] = RequestPacket
PACKETS[2013606][3] = ResponsePacket
