
from app.common.objects import bBeatmapInfoReply

from ..packets import PACKETS
from . import ResponsePacket
from .writer import Writer

from typing import Callable

def register(packet: ResponsePacket) -> Callable:
    def wrapper(func) -> Callable:
        PACKETS[20121008][1][packet] = func
        PACKETS[20120916][1][packet] = func
        return func

    return wrapper

@register(ResponsePacket.BEATMAP_INFO_REPLY)
def beatmap_info_reply(reply: bBeatmapInfoReply):
    writer = Writer()
    writer.write_beatmap_info_reply(reply)
    return writer.stream.get()
