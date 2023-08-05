
from app.common.constants import PresenceFilter
from app.common.streams import StreamIn

from .constants import RequestPacket
from ..packets import PACKETS
from .reader import Reader

from typing import Callable

import app

def register(packet: RequestPacket) -> Callable:
    def wrapper(func) -> Callable:
        PACKETS[2013606][0][packet] = func
        return func

    return wrapper

@register(RequestPacket.PONG)
def pong(stream: StreamIn):
    return

@register(RequestPacket.EXIT)
def exit(stream: StreamIn):
    return stream.s32() == 1

@register(RequestPacket.RECEIVE_UPDATES)
def receive_updates(stream: StreamIn):
    return PresenceFilter(stream.s32())

@register(RequestPacket.PRESENCE_REQUEST)
def presence_request(stream: StreamIn):
    return Reader(stream).read_intlist()

@register(RequestPacket.PRESENCE_REQUEST_ALL)
def presence_request_all(stream: StreamIn):
    return

@register(RequestPacket.STATS_REQUEST)
def stats_request(stream: StreamIn):
    return Reader(stream).read_intlist()

@register(RequestPacket.REQUEST_STATUS)
def request_status(stream: StreamIn):
    return

@register(RequestPacket.CHANGE_STATUS)
def change_status(stream: StreamIn):
    return Reader(stream).read_status()

@register(RequestPacket.JOIN_CHANNEL)
def join_channel(stream: StreamIn):
    return stream.string()

@register(RequestPacket.LEAVE_CHANNEL)
def leave_channel(stream: StreamIn):
    return stream.string()

@register(RequestPacket.SEND_MESSAGE)
def send_message(stream: StreamIn):
    return Reader(stream).read_message()

@register(RequestPacket.SEND_PRIVATE_MESSAGE)
def send_message_private(stream: StreamIn):
    return Reader(stream).read_message()

@register(RequestPacket.SET_AWAY_MESSAGE)
def away_message(stream: StreamIn):
    return Reader(stream).read_message()

@register(RequestPacket.ADD_FRIEND)
def add_friend(stream: StreamIn):
    return stream.s32()

@register(RequestPacket.REMOVE_FRIEND)
def remove_friend(stream: StreamIn):
    return stream.s32()

@register(RequestPacket.BEATMAP_INFO)
def beatmap_info_request(stream: StreamIn):
    return Reader(stream).read_beatmap_request()

@register(RequestPacket.START_SPECTATING)
def start_spectating(stream: StreamIn):
    return stream.s32()

@register(RequestPacket.STOP_SPECTATING)
def stop_spectating(stream: StreamIn):
    return

@register(RequestPacket.SEND_FRAMES)
def send_frames(stream: StreamIn):
    return Reader(stream).read_replayframe_bundle()

@register(RequestPacket.CANT_SPECTATE)
def cant_spectate(stream: StreamIn):
    return

@register(RequestPacket.ERROR_REPORT)
def bancho_error(stream: StreamIn):
    return stream.string()

@register(RequestPacket.JOIN_LOBBY)
def join_lobby(stream: StreamIn):
    return

@register(RequestPacket.PART_LOBBY)
def leave_lobby(stream: StreamIn):
    return

@register(RequestPacket.CREATE_MATCH)
def create_match(stream: StreamIn):
    return Reader(stream).read_match()

@register(RequestPacket.JOIN_MATCH)
def join_match(stream: StreamIn):
    return Reader(stream).read_matchjoin()

@register(RequestPacket.LEAVE_MATCH)
def leave_match(stream: StreamIn):
    return

@register(RequestPacket.MATCH_CHANGE_SETTINGS)
def change_settings(stream: StreamIn):
    return Reader(stream).read_match()

@register(RequestPacket.MATCH_CHANGE_SLOT)
def change_slot(stream: StreamIn):
    return stream.s32()

@register(RequestPacket.MATCH_INVITE)
def invite(stream: StreamIn):
    return stream.s32()

@register(RequestPacket.TOURNAMENT_MATCH_INFO)
def tourney_match_info(stream: StreamIn):
    return stream.s32()

@register(RequestPacket.CHANGE_FRIENDONLY_DMS)
def friendonly_dms(stream: StreamIn):
    return stream.s32() == 1
