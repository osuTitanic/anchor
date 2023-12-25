
from ..b1700.constants import (
    ResponsePacket,
    RequestPacket
)

from .writer import Writer
from .reader import Reader

from .. import register_version

register_version(
    version=553,
    protocol_version=3,
    response_packets=ResponsePacket,
    request_packets=RequestPacket,
    inherit_from=558
)

register_version(
    version=536,
    protocol_version=3,
    response_packets=ResponsePacket,
    request_packets=RequestPacket,
    inherit_from=558
)

from . import encoder
from . import decoder
