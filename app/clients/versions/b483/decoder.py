
from app.common.streams import StreamIn

from . import RequestPacket
from . import PACKETS
from . import Reader

from typing import Callable

def register(packet: RequestPacket) -> Callable:
    def wrapper(func) -> Callable:
        PACKETS[483][0][packet] = func
        PACKETS[402][0][packet] = func
        return func

    return wrapper

@register(RequestPacket.CREATE_MATCH)
def create_match(stream: StreamIn):
    return Reader(stream).read_match()

@register(RequestPacket.MATCH_CHANGE_SETTINGS)
def change_settings(stream: StreamIn):
    return Reader(stream).read_match()

@register(RequestPacket.MATCH_CHANGE_PASSWORD)
def change_password(stream: StreamIn):
    return Reader(stream).read_match().password

@register(RequestPacket.CHANGE_STATUS)
def change_status(stream: StreamIn):
    return Reader(stream).read_status()

@register(RequestPacket.BEATMAP_INFO)
def beatmap_info(stream: StreamIn):
    return Reader(stream).read_beatmap_request()

@register(RequestPacket.MATCH_SCORE_UPDATE)
def score_update(stream: StreamIn):
    return Reader(stream).read_scoreframe()

@register(RequestPacket.SEND_FRAMES)
def send_frames(stream: StreamIn):
    return Reader(stream).read_replayframe_bundle()
