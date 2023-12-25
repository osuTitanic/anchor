
from .constants import RequestPacket, ResponsePacket

from .reader import Reader
from .writer import Writer

from .. import register_version

register_version(
    version=20130815,
    protocol_version=18,
    request_packets=RequestPacket,
    response_packets=ResponsePacket
)

register_version(
    version=20130401,
    protocol_version=18,
    request_packets=RequestPacket,
    response_packets=ResponsePacket
)

from . import decoder
from . import encoder
