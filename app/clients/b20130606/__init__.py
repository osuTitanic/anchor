
"""
b20130606/b20130716 is the latest supported version for tcp bancho, according to osekai snapshot builds.
After that, the clients switch to the http based bancho protocol, which is still used to this day.
"""

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
