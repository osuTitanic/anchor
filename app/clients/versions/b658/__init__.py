
from ..b1700.constants import (
    ResponsePacket,
    RequestPacket
)

from .. import register_version

register_version(
    version=658,
    protocol_version=4,
    response_packets=ResponsePacket,
    request_packets=RequestPacket,
    inherit_from=675
)

register_version(
    version=591,
    protocol_version=4,
    response_packets=ResponsePacket,
    request_packets=RequestPacket,
    inherit_from=675
)

from . import encoder
