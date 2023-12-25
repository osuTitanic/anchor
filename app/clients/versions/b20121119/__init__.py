
from ... import (
    DefaultResponsePacket as ResponsePacket,
    DefaultRequestPacket as RequestPacket
)

from .writer import Writer

from .. import register_version

register_version(
    version=20121119,
    protocol_version=12,
    response_packets=ResponsePacket,
    request_packets=RequestPacket,
    inherit_from=20121203
)

register_version(
    version=20121030,
    protocol_version=12,
    response_packets=ResponsePacket,
    request_packets=RequestPacket,
    inherit_from=20121203
)

from . import encoder
