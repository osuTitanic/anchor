
from app.common.streams import StreamIn

from . import RequestPacket
from . import PACKETS
from . import Reader

from typing import Callable

def register(packet: RequestPacket) -> Callable:
    def wrapper(func) -> Callable:
        PACKETS[337][0][packet] = func
        PACKETS[323][0][packet] = func
        return func

    return wrapper

@register(RequestPacket.CHANGE_STATUS)
def change_status(stream: StreamIn):
    return Reader(stream).read_status()
