
from ... import (
    DefaultResponsePacket as ResponsePacket,
    DefaultRequestPacket as RequestPacket
)

from .writer import Writer

from .. import register_version

register_version(
    version=20121008,
    protocol_version=11,
    response_packets=ResponsePacket,
    request_packets=RequestPacket,
    inherit_from=20121030
)

register_version(
    version=20120916,
    protocol_version=11,
    response_packets=ResponsePacket,
    request_packets=RequestPacket,
    inherit_from=20121030
)

from . import encoder
