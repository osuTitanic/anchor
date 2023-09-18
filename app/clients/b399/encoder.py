
from app.common.objects import bMatch

from typing import Callable

from . import ResponsePacket
from . import PACKETS
from . import Writer

def register(packet: ResponsePacket) -> Callable:
    def wrapper(func) -> Callable:
        PACKETS[399][1][packet] = func
        PACKETS[392][1][packet] = func
        return func

    return wrapper

@register(ResponsePacket.NEW_MATCH)
def new_match(match: bMatch):
    writer = Writer()
    writer.write_match(match)
    return writer.stream.get()

@register(ResponsePacket.UPDATE_MATCH)
def update_match(match: bMatch):
    writer = Writer()
    writer.write_match(match)
    return writer.stream.get()

@register(ResponsePacket.MATCH_JOIN_SUCCESS)
def match_join_success(match: bMatch):
    writer = Writer()
    writer.write_match(match)
    return writer.stream.get()

@register(ResponsePacket.MATCH_START)
def match_start(match: bMatch):
    writer = Writer()
    writer.write_match(match)
    return writer.stream.get()
