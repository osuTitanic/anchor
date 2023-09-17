
from app.common.objects import bMessage
from app.common.streams import StreamIn

from . import RequestPacket
from . import PACKETS
from . import Reader

from typing import Callable

def register(packet: RequestPacket) -> Callable:
    def wrapper(func) -> Callable:
        PACKETS[319][0][packet] = func
        PACKETS[282][0][packet] = func
        return func

    return wrapper

@register(RequestPacket.SEND_MESSAGE)
def read_message(stream: StreamIn):
    return bMessage(
        sender='',
        content=stream.string(),
        target='#osu'
    )

@register(RequestPacket.SEND_PRIVATE_MESSAGE)
def read_private_message(stream: StreamIn):
    return Reader(stream).read_message()
