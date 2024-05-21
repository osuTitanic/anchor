
from app.common.objects import bBeatmapInfoReply

from typing import Callable

from .. import register_encoder

from . import ResponsePacket
from ..b399 import Writer

def register(packet: ResponsePacket) -> Callable:
    def wrapper(func) -> Callable:
        register_encoder(388, packet, func)
        register_encoder(339, packet, func)
        return func

    return wrapper

@register(ResponsePacket.BEATMAP_INFO_REPLY)
def beatmap_info_reply(reply: bBeatmapInfoReply):
    for info in reply.beatmaps:
        # Approved status does not exist
        info.ranked = {
            -1: -1,
            0: 0,
            1: 1,
            2: 1
        }[info.ranked]

    writer = Writer()
    writer.write_beatmap_info_reply(reply)
    return writer.stream.get()
