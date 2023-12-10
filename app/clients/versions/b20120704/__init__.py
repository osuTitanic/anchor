
from ... import (
    DefaultResponsePacket as ResponsePacket,
    DefaultRequestPacket as RequestPacket
)

from .writer import Writer

from .. import register_version

register_version(
    version=20120704,
    protocol_version=7,
    response_packets=ResponsePacket,
    request_packets=RequestPacket,
    inherit_from=20120725
)

register_version(
    version=1807,
    protocol_version=7,
    response_packets=ResponsePacket,
    request_packets=RequestPacket,
    inherit_from=20120725
)

from . import encoder
