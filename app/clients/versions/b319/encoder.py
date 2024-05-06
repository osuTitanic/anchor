
from typing import Callable

from app.common.objects import (
    bUserPresence,
    bUserStats,
    bUserQuit,
    bMessage,
)

from .. import register_encoder
from . import ResponsePacket
from . import Writer

def register(packet: ResponsePacket) -> Callable:
    def wrapper(func) -> Callable:
        register_encoder(319, packet, func)
        register_encoder(282, packet, func)
        return func

    return wrapper

@register(ResponsePacket.USER_STATS)
def send_stats(stats: bUserStats, presence: bUserPresence, update: bool = False):
    # Add cap for total score to prevent client from crashing
    stats.tscore = min(stats.tscore, 17705429347)

    writer = Writer()
    writer.write_presence(presence, stats, update)
    return writer.stream.get()

@register(ResponsePacket.SEND_MESSAGE)
def send_message(msg: bMessage):
    writer = Writer()
    writer.write_message(msg)
    return writer.stream.get()

@register(ResponsePacket.USER_QUIT)
def quit(state: bUserQuit):
    writer = Writer()
    writer.write_quit(state)
    return writer.stream.get()
