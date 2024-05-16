
from app.common.streams import StreamIn

from .. import register_decoder
from . import RequestPacket
from . import Reader

from typing import Callable

def register(packet: RequestPacket) -> Callable:
    def wrapper(func) -> Callable:
        register_decoder(20121223, packet, func)
        register_decoder(20121203, packet, func)
        return func

    return wrapper

@register(RequestPacket.SEND_MESSAGE)
def message(stream: StreamIn):
    return Reader(stream).read_message()

@register(RequestPacket.SEND_PRIVATE_MESSAGE)
def private_message(stream: StreamIn):
    return Reader(stream).read_message()
