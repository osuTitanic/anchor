
from app.common.streams import StreamOut
from app.common.objects import (
    ReplayFrameBundle,
    UserPresence,
    UserStats,
    UserQuit,
    Message
)

from .constants import ResponsePacket
from ..packets import PACKETS
from .writer import Writer

from typing import List, Optional, Callable

def register(packet: ResponsePacket) -> Callable:
    def wrapper(func) -> Callable:
        PACKETS[2013606][1][packet] = func
        return func

    return wrapper

@register(ResponsePacket.LOGIN_REPLY)
def send_login_reply(reply: int):
    return int(reply).to_bytes(
        length=4,
        byteorder='little',
        signed=True
    )

@register(ResponsePacket.PROTOCOL_VERSION)
def send_protocol_version(version: int):
    return int(version).to_bytes(
        length=4,
        byteorder='little',
        signed=True
    )

@register(ResponsePacket.PING)
def send_ping():
    return # bruh

@register(ResponsePacket.ANNOUNCE)
def send_announcement(message: str):
    stream = StreamOut()
    stream.string(message)
    return stream.get()

@register(ResponsePacket.GET_ATTENSION)
def open_chat():
    return

@register(ResponsePacket.MENU_ICON)
def send_menu_icon(image: Optional[str], url: Optional[str]):
    stream = StreamOut()
    stream.string(
        '|'.join([
            f'{image if image else ""}',
            f'{url if url else ""}'
        ])
    )
    return stream.get()

@register(ResponsePacket.USER_PRESENCE)
def send_presence(presence: UserPresence):
    writer = Writer()
    writer.write_presence(presence)
    return writer.stream.get()

@register(ResponsePacket.USER_STATS)
def send_stats(stats: UserStats):
    writer = Writer()
    writer.write_stats(stats)
    return writer.stream.get()

@register(ResponsePacket.USER_PRESENCE_SINGLE)
def send_player(player_id: int):
    return int(player_id).to_bytes(
        length=4,
        byteorder='little',
        signed=True
    )

@register(ResponsePacket.USER_PRESENCE_BUNDLE)
def send_players(player_ids: List[int]):
    writer = Writer()
    writer.write_intlist(player_ids)
    return writer.stream.get()

@register(ResponsePacket.USER_QUIT)
def send_exit(user_quit: UserQuit):
    writer = Writer()
    writer.write_quit(user_quit)
    return writer.stream.get()

@register(ResponsePacket.IRC_CHANGE_USERNAME)
def irc_nick(previous: str, after: str):
    stream = StreamOut()
    stream.string(f'{previous}>>>>{after}')
    return stream.get()

@register(ResponsePacket.IRC_QUIT)
def irc_quit(*args):
    pass # TODO: Only used in older clients

@register(ResponsePacket.SEND_MESSAGE)
def send_message(msg: Message):
    writer = Writer()
    writer.write_message(msg)
    return writer.stream.get()

@register(ResponsePacket.SPECTATOR_JOINED)
def spectator_joined(player_id: int):
    return int(player_id).to_bytes(
        length=4,
        byteorder='little',
        signed=True
    )

@register(ResponsePacket.SPECTATOR_LEFT)
def spectator_left(player_id: int):
    return int(player_id).to_bytes(
        length=4,
        byteorder='little',
        signed=True
    )

@register(ResponsePacket.SPECTATE_FRAMES)
def spectate_frames(bundle: ReplayFrameBundle):
    writer = Writer()
    writer.write_replayframe_bundle(bundle)
    return writer.stream.get()

@register(ResponsePacket.CANT_SPECTATE)
def cant_spectate(player_id: int):
    return int(player_id).to_bytes(
        length=4,
        byteorder='little',
        signed=True
    )

@register(ResponsePacket.FELLOW_SPECTATOR_JOINED)
def fellow_spectator_joined(player_id: int):
    return int(player_id).to_bytes(
        length=4,
        byteorder='little',
        signed=True
    )

@register(ResponsePacket.FELLOW_SPECTATOR_LEFT)
def fellow_spectator_left(player_id: int):
    return int(player_id).to_bytes(
        length=4,
        byteorder='little',
        signed=True
    )

@register(ResponsePacket.VERSION_UPDATE)
def version_update():
    return
