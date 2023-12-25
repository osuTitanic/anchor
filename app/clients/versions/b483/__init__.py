
from ..b1700.constants import (
    ResponsePacket,
    RequestPacket
)

from .writer import Writer
from .reader import Reader

from .. import register_version

register_version(
    version=483,
    protocol_version=0,
    response_packets=ResponsePacket,
    request_packets=RequestPacket,
    inherit_from=487
)

register_version(
    version=402,
    protocol_version=0,
    response_packets=ResponsePacket,
    request_packets=RequestPacket,
    inherit_from=487
)

from . import encoder
from . import decoder
