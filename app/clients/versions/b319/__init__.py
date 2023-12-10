
from ..b323 import (
    ResponsePacket,
    RequestPacket
)

from .writer import Writer
from .reader import Reader

from .. import register_version

register_version(
    version=319,
    protocol_version=0,
    response_packets=ResponsePacket,
    request_packets=RequestPacket,
    inherit_from=323
)

register_version(
    version=282,
    protocol_version=0,
    response_packets=ResponsePacket,
    request_packets=RequestPacket,
    inherit_from=323
)

from . import encoder
from . import decoder
