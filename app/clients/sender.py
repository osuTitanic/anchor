
from typing import Optional, List
from abc import ABC

from app.common.constants import (
    Permissions
)

from app.common.objects import (
    ReplayFrameBundle,
    BeatmapInfoReply,
    UserPresence,
    UserStats,
    UserQuit,
    Channel,
    Match
)

class BaseSender(ABC):

    protocol_version = -1

    def __init__(self, player) -> None:
        self.player = player

    def send_login_reply(self, reply: int):
        ...

    def send_protocol_version(self, version: int):
        ...

    def send_ping(self):
        ...

    def send_announcement(self, message: str):
        ...

    def send_menu_icon(self, image: Optional[str], url: Optional[str]):
        ...

    def send_presence(self, presence: UserPresence):
        ...

    def send_stats(self, presence: UserStats):
        ...

    def send_player(self, player_id: int):
        ...

    def send_players(self, player_ids: List[int]):
        ...

    def send_exit(self, user_quit: UserQuit):
        ...

    def send_permissions(self, permissions: Permissions):
        ...

    def send_spectator_joined(self, player_id: int):
        ...

    def send_spectator_left(self, player_id: int):
        ...

    def send_frames(self, bundle: ReplayFrameBundle):
        ...

    def send_cant_spectate(self, player_id: int):
        ...

    def send_fellow_spectator(self, player_id: int):
        ...

    def send_fellow_spectator_left(self, player_id: int):
        ...

    def send_friends(self):
        ...

    def send_channel(self, channel: Channel):
        ...

    def send_channel_revoked(self, target: str):
        ...

    def send_channel_info_end(self):
        ...

    def send_message(self, message: str):
        ...

    def send_silence_info(self, remaining_time: int):
        ...

    def send_beatmaps(self, beatmaps: BeatmapInfoReply):
        ...

    def send_monitor(self):
        ...

    def send_lobby_join(self, player_id: int):
        ...

    def send_lobby_part(self, player_id: int):
        ...

    def send_match(self, match: Match):
        ...

    def send_match_disband(self, match_id: int):
        ...

    def send_matchjoin_fail(self):
        ...

    def send_matchjoin_success(self, match: Match):
        ...

    def send_match_transferhost(self):
        ...

    def send_match_complete(self):
        ...

    def send_match_all_players_loaded(self):
        ...

    def send_match_player_failed(self, slot_id: int):
        ...

    def send_match_player_skipped(self, slot_id: int):
        ...

    def send_match_start(self, match):
        ...

    def send_match_skip(self):
        ...
