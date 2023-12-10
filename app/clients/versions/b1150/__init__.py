
from ..b1700.constants import (
    ResponsePacket,
    RequestPacket
)

from .writer import Writer

from .. import register_version

register_version(
    version=1150,
    protocol_version=4,
    response_packets=ResponsePacket,
    request_packets=RequestPacket,
    inherit_from=1152
)

register_version(
    version=679,
    protocol_version=4,
    response_packets=ResponsePacket,
    request_packets=RequestPacket,
    inherit_from=1152
)

from . import encoder
