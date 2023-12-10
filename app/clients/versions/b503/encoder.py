
from app.common.objects import bBeatmapInfoReply

from .. import register_encoder
from . import ResponsePacket
from . import Writer

from typing import Callable

def register(packet: ResponsePacket) -> Callable:
    def wrapper(func) -> Callable:
        register_encoder(503, packet, func)
        register_encoder(487, packet, func)
        return func

    return wrapper

@register(ResponsePacket.BEATMAP_INFO_REPLY)
def beatmap_info_reply(reply: bBeatmapInfoReply):
    writer = Writer()
    writer.write_beatmap_info_reply(reply)
    return writer.stream.get()
