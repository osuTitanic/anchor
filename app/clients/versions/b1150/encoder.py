
from app.common.objects import bUserStats, bUserPresence

from typing import Callable, Optional

from . import ResponsePacket
from . import PACKETS
from . import Writer

def register(packet: ResponsePacket) -> Callable:
    def wrapper(func) -> Callable:
        PACKETS[1150][1][packet] = func
        PACKETS[679][1][packet] = func
        return func

    return wrapper

@register(ResponsePacket.LOGIN_REPLY)
def send_login_reply(reply: int):
    if reply < -3:
        # Login Errors < -3 are not supported
        reply = -1

    return int(reply).to_bytes(
        length=4,
        byteorder='little',
        signed=True
    )

@register(ResponsePacket.USER_STATS)
def send_stats(stats: bUserStats, presence: Optional[bUserPresence] = None):
    writer = Writer()
    if presence:
        writer.write_presence(presence, stats)
    else:
        writer.write_stats(stats)
    return writer.stream.get()
