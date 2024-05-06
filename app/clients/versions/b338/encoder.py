
from app.common.constants import Permissions
from app.common.streams import StreamOut
from app.common.objects import (
    bReplayFrameBundle,
    bBeatmapInfoReply,
    bUserPresence,
    bScoreFrame,
    bUserStats,
    bUserQuit,
    bChannel,
    bMessage,
    bMatch
)

from .. import register_encoder

from .constants import ResponsePacket
from . import Writer

from typing import List, Optional, Callable

def register(packet: ResponsePacket) -> Callable:
    def wrapper(func) -> Callable:
        register_encoder(338, packet, func)
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

@register(ResponsePacket.LOGIN_PERMISSIONS)
def send_permissions(permissions: Permissions):
    return int(permissions.value).to_bytes(
        length=4,
        byteorder='little',
        signed=True
    )

@register(ResponsePacket.FRIENDS_LIST)
def friends(player_id: List[int]):
    writer = Writer()
    writer.write_intlist(player_id)
    return writer.stream.get()

@register(ResponsePacket.PING)
def send_ping():
    return b'' # bruh

@register(ResponsePacket.ANNOUNCE)
def send_announcement(message: str):
    stream = StreamOut()
    stream.string(message)
    return stream.get()

@register(ResponsePacket.GET_ATTENSION)
def open_chat():
    return b''

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

@register(ResponsePacket.MONITOR)
def monitor():
    return b''

@register(ResponsePacket.USER_STATS)
def send_stats(stats: bUserStats, presence: Optional[bUserPresence] = None):
    # Add cap for total score to prevent client from crashing
    stats.tscore = min(stats.tscore, 17705429347)

    writer = Writer()
    if presence:
        writer.write_presence(presence, stats)
    else:
        writer.write_stats(stats)
    return writer.stream.get()

@register(ResponsePacket.IRC_JOIN)
def send_irc_player(username: int):
    stream = StreamOut()
    stream.string(username)
    return stream.get()

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
def send_exit(user_quit: bUserQuit):
    writer = Writer()
    writer.write_quit(user_quit)
    return writer.stream.get()

@register(ResponsePacket.IRC_CHANGE_USERNAME)
def irc_nick(previous: str, after: str):
    stream = StreamOut()
    stream.string(f'{previous}>>>>{after}')
    return stream.get()

@register(ResponsePacket.IRC_QUIT)
def irc_quit(username: str):
    stream = StreamOut()
    stream.string(username)
    return stream.get()

@register(ResponsePacket.CHANNEL_AVAILABLE)
def channel_available(channel: bChannel):
    writer = Writer()
    writer.write_channel(channel)
    return writer.stream.get()

@register(ResponsePacket.CHANNEL_AVAILABLE_AUTOJOIN)
def channel_available_autojoin(channel: bChannel):
    writer = Writer()
    writer.write_channel(channel)
    return writer.stream.get()

@register(ResponsePacket.CHANNEL_INFO_COMPLETE)
def channel_info_complete():
    return b''

@register(ResponsePacket.CHANNEL_JOIN_SUCCESS)
def channel_join_success(target: str):
    stream = StreamOut()
    stream.string(target)
    return stream.get()

@register(ResponsePacket.CHANNEL_REVOKED)
def channel_revoked(target: str):
    stream = StreamOut()
    stream.string(target)
    return stream.get()

@register(ResponsePacket.SEND_MESSAGE)
def send_message(msg: bMessage):
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
def spectate_frames(bundle: bReplayFrameBundle):
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

@register(ResponsePacket.LOBBY_JOIN)
def lobby_join(player_id: int):
    return int(player_id).to_bytes(
        length=4,
        byteorder='little',
        signed=True
    )

@register(ResponsePacket.LOBBY_PART)
def lobby_part(player_id: int):
    return int(player_id).to_bytes(
        length=4,
        byteorder='little',
        signed=True
    )

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

@register(ResponsePacket.DISBAND_MATCH)
def disband_match(match_id: int):
    return int(match_id).to_bytes(
        length=4,
        byteorder='little',
        signed=True
    )

@register(ResponsePacket.MATCH_JOIN_SUCCESS)
def match_join_success(match: bMatch):
    writer = Writer()
    writer.write_match(match)
    return writer.stream.get()

@register(ResponsePacket.MATCH_JOIN_FAIL)
def match_join_fail():
    return b''

@register(ResponsePacket.MATCH_CHANGE_PASSWORD)
def match_change_password(new_password: str):
    stream = StreamOut()
    stream.string(new_password)
    return stream.get()

@register(ResponsePacket.MATCH_START)
def match_start(match: bMatch):
    writer = Writer()
    writer.write_match(match)
    return writer.stream.get()

@register(ResponsePacket.MATCH_SCORE_UPDATE)
def score_update(score_frame: bScoreFrame):
    writer = Writer()
    writer.write_scoreframe(score_frame)
    return writer.stream.get()

@register(ResponsePacket.MATCH_TRANSFER_HOST)
def transfer_host():
    return b''

@register(ResponsePacket.MATCH_ALL_PLAYERS_LOADED)
def all_players_loaded():
    return b''

@register(ResponsePacket.MATCH_PLAYER_FAILED)
def match_player_failed(slot_id: int):
    return int(slot_id).to_bytes(
        length=4,
        byteorder='little',
        signed=True
    )

@register(ResponsePacket.MATCH_PLAYER_SKIPPED)
def match_player_skipped(slot_id: int):
    return int(slot_id).to_bytes(
        length=4,
        byteorder='little',
        signed=True
    )

@register(ResponsePacket.MATCH_SKIP)
def match_skip():
    return b''

@register(ResponsePacket.MATCH_COMPLETE)
def match_complete():
    return b''

@register(ResponsePacket.INVITE)
def match_invite(msg: bMessage):
    writer = Writer()
    writer.write_message(msg)
    return writer.stream.get()

@register(ResponsePacket.BEATMAP_INFO_REPLY)
def beatmap_info_reply(reply: bBeatmapInfoReply):
    writer = Writer()
    writer.write_beatmap_info_reply(reply)
    return writer.stream.get()

@register(ResponsePacket.SILENCE_INFO)
def silence_info(time: int):
    return int(time).to_bytes(
        length=4,
        byteorder='little',
        signed=True
    )

@register(ResponsePacket.USER_SILENCED)
def user_silenced(player_id: int):
    return int(player_id).to_bytes(
        length=4,
        byteorder='little',
        signed=True
    )

@register(ResponsePacket.USER_DM_BLOCKED)
def dm_blocked(msg: bMessage):
    writer = Writer()
    writer.write_message(msg)
    return writer.stream.get()

@register(ResponsePacket.TARGET_IS_SILENCED)
def target_silenced(msg: bMessage):
    writer = Writer()
    writer.write_message(msg)
    return writer.stream.get()

@register(ResponsePacket.VERSION_UPDATE)
def version_update():
    return b''

@register(ResponsePacket.VERSION_UPDATE_FORCED)
def version_update_forced():
    return b''

@register(ResponsePacket.SWITCH_SERVER)
def switch_to_backup():
    return b''

@register(ResponsePacket.RESTART)
def restarting(retry_in_ms: int):
    return int(retry_in_ms).to_bytes(
        length=4,
        byteorder='little',
        signed=True
    )
