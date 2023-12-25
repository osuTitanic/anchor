
from ..b1700.constants import (
    ResponsePacket,
    RequestPacket
)

from .writer import Writer

from .. import register_version

register_version(
    version=503,
    protocol_version=1,
    response_packets=ResponsePacket,
    request_packets=RequestPacket,
    inherit_from=504
)

register_version(
    version=487,
    protocol_version=1,
    response_packets=ResponsePacket,
    request_packets=RequestPacket,
    inherit_from=504
)

from . import encoder
