
from app.common.streams import StreamIn

from ..packets import PACKETS
from . import RequestPacket
from .reader import Reader

from typing import Callable

def register(packet: RequestPacket) -> Callable:
    def wrapper(func) -> Callable:
        PACKETS[20130329][0][packet] = func
        PACKETS[20130303][0][packet] = func
        return func

    return wrapper

@register(RequestPacket.SEND_FRAMES)
def send_frames(stream: StreamIn):
    return Reader(stream).read_replayframe_bundle()
