
from app.common.streams import StreamIn

from .. import register_decoder
from . import RequestPacket
from . import Reader

from typing import Callable

def register(packet: RequestPacket) -> Callable:
    def wrapper(func) -> Callable:
        register_decoder(20130329, packet, func)
        register_decoder(20130118, packet, func)
        return func

    return wrapper

@register(RequestPacket.SEND_FRAMES)
def send_frames(stream: StreamIn):
    return Reader(stream).read_replayframe_bundle()
