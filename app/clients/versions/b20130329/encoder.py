
from app.common.objects import bReplayFrameBundle

from .. import register_encoder
from . import ResponsePacket
from . import Writer

from typing import Callable

def register(packet: ResponsePacket) -> Callable:
    def wrapper(func) -> Callable:
        register_encoder(20130329, packet, func)
        register_encoder(20130118, packet, func)
        return func

    return wrapper

@register(ResponsePacket.SPECTATE_FRAMES)
def spectate_frames(bundle: bReplayFrameBundle):
    writer = Writer()
    writer.write_replayframe_bundle(bundle)
    return writer.stream.get()
