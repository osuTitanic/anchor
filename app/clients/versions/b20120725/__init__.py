
from ... import (
    DefaultResponsePacket as ResponsePacket,
    DefaultRequestPacket as RequestPacket
)

from .. import register_version

from .writer import Writer

register_version(
    version=20120725,
    protocol_version=8,
    request_packets=RequestPacket,
    response_packets=ResponsePacket,
    inherit_from=20120812
)

from . import encoder
