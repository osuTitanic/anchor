
from .constants import (
    ResponsePacket,
    RequestPacket
)

from .reader import Reader
from .writer import Writer

from .. import register_version

register_version(
    version=1700,
    protocol_version=6,
    response_packets=ResponsePacket,
    request_packets=RequestPacket,
    inherit_from=20120704
)

register_version(
    version=1152,
    protocol_version=6,
    response_packets=ResponsePacket,
    request_packets=RequestPacket,
    inherit_from=20120704
)

from . import encoder
from . import decoder
