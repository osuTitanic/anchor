
from ..b1700.constants import (
    ResponsePacket,
    RequestPacket
)

from .. import register_version

register_version(
    version=388,
    protocol_version=0,
    request_packets=RequestPacket,
    response_packets=ResponsePacket,
    inherit_from=392
)

register_version(
    version=339,
    protocol_version=0,
    request_packets=RequestPacket,
    response_packets=ResponsePacket,
    inherit_from=392
)

from . import encoder
