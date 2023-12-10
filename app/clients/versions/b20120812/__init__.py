
from ... import (
    DefaultResponsePacket as ResponsePacket,
    DefaultRequestPacket as RequestPacket
)

from .reader import Reader
from .writer import Writer

from .. import register_version

register_version(
    version=20120812,
    protocol_version=10,
    response_packets=ResponsePacket,
    request_packets=RequestPacket,
    inherit_from=20120916
)

from . import encoder
from . import decoder
