
from app.common.objects import bReplayFrameBundle

from ..packets import PACKETS
from . import ResponsePacket
from . import Writer

from typing import Callable

def register(packet: ResponsePacket) -> Callable:
    def wrapper(func) -> Callable:
        PACKETS[20130329][1][packet] = func
        PACKETS[20130303][1][packet] = func
        return func

    return wrapper

@register(ResponsePacket.SPECTATE_FRAMES)
def spectate_frames(bundle: bReplayFrameBundle):
    writer = Writer()
    writer.write_replayframe_bundle(bundle)
    return writer.stream.get()
