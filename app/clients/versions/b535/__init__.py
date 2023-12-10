
from ..b1700.constants import (
    ResponsePacket,
    RequestPacket
)

from .writer import Writer
from .reader import Reader

from .. import register_version

register_version(
    version=535,
    protocol_version=2,
    response_packets=ResponsePacket,
    request_packets=RequestPacket,
    inherit_from=536
)

register_version(
    version=504,
    protocol_version=2,
    response_packets=ResponsePacket,
    request_packets=RequestPacket,
    inherit_from=536
)

from . import encoder
from . import decoder
