
from app.common.objects import bMessage

from .. import register_encoder
from . import ResponsePacket
from . import Writer

from typing import Callable

def register(packet: ResponsePacket) -> Callable:
    def wrapper(func) -> Callable:
        register_encoder(20121223, packet, func)
        register_encoder(20121203, packet, func)
        return func

    return wrapper

@register(ResponsePacket.SEND_MESSAGE)
def message(message: bMessage):
    writer = Writer()
    writer.write_message(message)
    return writer.stream.get()
