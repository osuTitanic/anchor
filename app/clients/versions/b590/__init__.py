
from ..b1700.constants import (
    ResponsePacket,
    RequestPacket
)

from .writer import Writer
from .reader import Reader

from .. import register_version

register_version(
    version=590,
    protocol_version=4,
    request_packets=RequestPacket,
    response_packets=ResponsePacket,
    inherit_from=591
)

register_version(
    version=558,
    protocol_version=4,
    request_packets=RequestPacket,
    response_packets=ResponsePacket,
    inherit_from=591
)

from . import encoder
from . import decoder
