
from .constants import RequestPacket, ResponsePacket

from .reader import Reader
from .writer import Writer

from . import decoder
from . import encoder

from ...packets import PACKETS

PACKETS[20130815][2] = RequestPacket
PACKETS[20130815][3] = ResponsePacket
PACKETS[20130401][2] = RequestPacket
PACKETS[20130401][3] = ResponsePacket
