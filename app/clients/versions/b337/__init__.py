
from ..b338.constants import (
    ResponsePacket,
    RequestPacket
)

from .writer import Writer
from .reader import Reader

from .. import register_version

register_version(
    version=337,
    protocol_version=0,
    response_packets=ResponsePacket,
    request_packets=RequestPacket,
    inherit_from=338
)

register_version(
    version=334,
    protocol_version=0,
    response_packets=ResponsePacket,
    request_packets=RequestPacket,
    inherit_from=338
)

from . import encoder
from . import decoder
