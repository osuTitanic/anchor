
from app.common.streams import StreamIn

from .. import register_decoder
from . import RequestPacket
from . import Reader

from typing import Callable

def register(packet: RequestPacket) -> Callable:
    def wrapper(func) -> Callable:
        register_decoder(337, packet, func)
        register_decoder(334, packet, func)
        return func

    return wrapper

@register(RequestPacket.CHANGE_STATUS)
def change_status(stream: StreamIn):
    return Reader(stream).read_status()
