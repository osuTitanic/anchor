
from ..b1700.constants import (
    ResponsePacket,
    RequestPacket
)

from .writer import Writer

from .. import register_version

register_version(
    version=675,
    protocol_version=4,
    response_packets=ResponsePacket,
    request_packets=RequestPacket,
    inherit_from=679
)

register_version(
    version=591,
    protocol_version=4,
    response_packets=ResponsePacket,
    request_packets=RequestPacket,
    inherit_from=679
)

from . import encoder
