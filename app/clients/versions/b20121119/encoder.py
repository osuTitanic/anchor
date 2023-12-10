
from app.common.objects import bUserPresence

from .. import register_encoder
from . import ResponsePacket
from . import Writer

from typing import Callable

def register(packet: ResponsePacket) -> Callable:
    def wrapper(func) -> Callable:
        register_encoder(20121119, packet, func)
        register_encoder(20121030, packet, func)
        return func

    return wrapper

@register(ResponsePacket.USER_PRESENCE)
def presence(presence: bUserPresence):
    writer = Writer()
    writer.write_presence(presence)
    return writer.stream.get()
