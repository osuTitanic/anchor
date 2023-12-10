
from ... import (
    DefaultResponsePacket as ResponsePacket,
    DefaultRequestPacket as RequestPacket
)

from .. import register_version

from .writer import Writer
from .reader import Reader

register_version(
    version=20130329,
    protocol_version=17,
    response_packets=ResponsePacket,
    request_packets=RequestPacket,
    inherit_from=20130815
)

register_version(
    version=20130118,
    protocol_version=17,
    response_packets=ResponsePacket,
    request_packets=RequestPacket,
    inherit_from=20130815
)

from . import decoder
from . import encoder
