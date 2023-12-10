
from ... import (
    DefaultResponsePacket as ResponsePacket,
    DefaultRequestPacket as RequestPacket
)

from .. import register_version

register_version(
    version=20121223,
    protocol_version=13,
    request_packets=RequestPacket,
    response_packets=ResponsePacket,
    inherit_from=20130118
)

register_version(
    version=20121203,
    protocol_version=13,
    request_packets=RequestPacket,
    response_packets=ResponsePacket,
    inherit_from=20130118
)

# TODO: sender_id in bMessage was removed here
