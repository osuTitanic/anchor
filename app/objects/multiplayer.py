
from __future__ import annotations

from typing import TYPE_CHECKING, Tuple, List
from datetime import datetime, timedelta
from threading import Thread, Timer
from dataclasses import dataclass
from queue import Queue
from copy import copy
from chio import (
    ScoreFrame as bScoreFrame,
    Match as bMatch,
    ScoringType,
    PacketType,
    SlotStatus,
    MatchType,
    TeamType,
    SlotTeam,
    Mods
)

if TYPE_CHECKING:
    from ..clients.osu import OsuClient
    from ..clients.base import Client
    from .channel import Channel

from app.common.database.repositories import beatmaps, events, matches
from app.common.constants import GameMode, EventType
from app.common.database import DBMatch

import logging
import config
import time
import app

class Slot:
    def __init__(self) -> None:
        self.last_frame: bScoreFrame | None = None
        self.player: "OsuClient" | None = None
        self.status = SlotStatus.Open
        self.team = SlotTeam.Neutral
        self.mods = Mods.NoMod
        self.has_failed = False
        self.loaded = False
        self.skipped = False

    def __repr__(self) -> str:
        return f'<Slot [{self.player.name if self.player else None}]: {self.status.name}>'
    
    @property
    def user_id(self) -> int:
        return self.player.id if self.player else -1

    @property
    def empty(self) -> bool:
        return self.player is None

    @property
    def is_playing(self) -> bool:
        return self.status == SlotStatus.Playing and self.loaded

    @property
    def has_map(self) -> bool:
        return self.status != SlotStatus.NoMap and self.has_player

    @property
    def has_player(self) -> bool:
        return self.player is not None

    @property
    def completed(self) -> bool:
        return self.status & SlotStatus.Complete and self.has_player

    @property
    def locked(self) -> bool:
        return self.status == SlotStatus.Locked

    def copy_from(self, other) -> None:
        self.player = other.player
        self.status = other.status
        self.team = other.team
        self.mods = other.mods

    def reset(self, new_status = SlotStatus.Open) -> None:
        self.player = None
        self.status = new_status
        self.team = SlotTeam.Neutral
        self.mods = Mods.NoMod
        self.loaded = False
        self.skipped = False
        self.has_failed = False

@dataclass(slots=True)
class MatchTimer:
    time: float
    thread: Thread

    @property
    def ending(self) -> datetime:
        return datetime.fromtimestamp(self.time)

    def start(self) -> None:
        self.thread.start()

class Match:
    def __init__(
        self,
        id: int,
        name: str,
        password: str,
        host: "OsuClient",
        beatmap_id: int = -1,
        beatmap_name: str = "",
        beatmap_hash: str = "",
        mode: GameMode = GameMode.Osu,
        seed: int = 0,
        persistant: bool = False
    ) -> None:
        self.id = id
        self.name = name
        self.password = password
        self.host = host

        self.beatmap_id = beatmap_id
        self.beatmap_text = beatmap_name
        self.beatmap_checksum = beatmap_hash
        self.previous_beatmap_id = beatmap_id
        self.previous_beatmap_name = beatmap_name
        self.previous_beatmap_hash = beatmap_hash

        self.mods = Mods.NoMod
        self.mode = mode
        self.seed = seed
        self.type = MatchType.Standard
        self.scoring_type = ScoringType.Score
        self.team_type = TeamType.HeadToHead
        self.persistent = persistant
        self.in_progress = False
        self.freemod = False

        self.slots = [Slot() for _ in range(config.MULTIPLAYER_MAX_SLOTS)]
        self.score_queue: Queue[bScoreFrame] = Queue()
        self.referee_players: List[int] = []
        self.banned_players: List[int] = []

        self.countdown: MatchTimer | None = None
        self.starting: MatchTimer | None = None
        self.completion_timer: Timer | None = None
        self.score_thread: Thread | None = None
        self.db_match: DBMatch | None = None
        self.chat: "Channel" | None = None

        self.logger = logging.getLogger(f'multi_{self.id}')
        self.last_activity = time.time()

    @classmethod
    def from_bancho_match(cls, match: bMatch, host: "OsuClient"):
        return Match(
            match.id,
            match.name,
            match.password,
            host,
            match.beatmap_id,
            match.beatmap_text,
            match.beatmap_checksum,
            match.mode,
            match.seed
        )

    @property
    def players(self) -> List["OsuClient"]:
        """Return all players"""
        return [slot.player for slot in self.player_slots]

    @property
    def url(self) -> str:
        """Url, used to join a match"""
        return f'osump://{self.id}/{self.password.replace(" ", "_") if self.password else ""}'

    @property
    def embed(self) -> str:
        """Embed that will be sent on invite"""
        return f'[{self.url} {self.name}]'
    
    @property
    def host_id(self) -> int:
        return self.host.id if self.host else 0

    @property
    def host_slot(self) -> Slot | None:
        for slot in self.slots:
            if slot.status.value & SlotStatus.HasPlayer.value and slot.player is self.host:
                return slot

        return None

    @property
    def ffa(self) -> bool:
        return True if self.team_type in [TeamType.TagTeamVs, TeamType.TeamVs] else False

    @property
    def player_slots(self) -> List[Slot]:
        return [slot for slot in self.slots if slot.has_player]

    @property
    def player_count(self) -> int:
        return len(self.player_slots)

    @property
    def loaded_players(self) -> List[bool]:
        # NOTE: Clients in version b323 and below don't have the
        #       MATCH_LOAD_COMPLETE packet so we can just ignore them
        return [
            slot.loaded
            for slot in self.slots
            if (
                slot.status == SlotStatus.Playing and
                slot.player.info.version.date > 323
            )
        ]

    def get_slot(self, player: "OsuClient") -> Slot | None:
        for slot in self.slots:
            if player is slot.player:
                return slot

        return None

    def get_slot_id(self, player: "OsuClient") -> int | None:
        for index, slot in enumerate(self.slots):
            if player is slot.player:
                return index

        return None

    def get_slot_with_id(self, player: "OsuClient") -> Tuple[Slot, int | None]:
        for index, slot in enumerate(self.slots):
            if player is slot.player:
                return slot, index

        return None, None

    def get_free(self) -> int | None:
        for index, slot in enumerate(self.slots):
            if slot.status == SlotStatus.Open:
                return index

        return None

    def get_player(self, name: str) -> "OsuClient" | None:
        safe_name = name.lower().replace(" ", "_")

        for player in self.players:
            if player.safe_name == safe_name:
                return player

        return None

    def update(self, lobby=True) -> None:
        # Enqueue to our players
        for player in self.players:
            player.enqueue_packet(PacketType.BanchoMatchUpdate, self)

        if not lobby:
            return

        # Clear password for lobby players
        match_password = copy(self.password)

        if self.password:
            self.password = " "

        # Enqueue to lobby players
        for player in app.session.players.osu_in_lobby:
            player.enqueue_packet(PacketType.BanchoMatchUpdate, self)

        # Re-apply password
        self.password = match_password

    def unready_players(self, expected = SlotStatus.Ready):
        for slot in self.slots:
            if slot.status != expected:
                continue

            slot.status = SlotStatus.NotReady
            slot.has_failed = False
            slot.skipped = False
            slot.loaded = False

    def change_settings(self, new_match: bMatch):
        if self.freemod != new_match.freemod:
            # Freemod state has been changed
            self.unready_players()
            self.freemod = new_match.freemod
            self.logger.info(f'Freemod: {self.freemod}')

            if self.freemod:
                for slot in self.slots:
                    if not (slot.status.value & SlotStatus.HasPlayer.value):
                        continue

                    # Set current mods to every player inside the match, if they are not speed mods
                    slot.mods = self.mods & ~Mods.SpeedMods

                    # TODO: Fix for older clients without freemod support
                    # slot.mods = []

                # The speedmods are kept in the match mods
                self.mods = self.mods & ~Mods.FreeModAllowed
            else:
                # Keep mods from host
                self.mods |= self.host_slot.mods

                # Reset any mod from players
                for slot in self.slots:
                    slot.mods = Mods.NoMod

        if new_match.beatmap_id <= 0:
            # Host is selecting new map
            self.logger.info('Host is selecting map...')
            self.unready_players()

            self.previous_beatmap_id = self.beatmap_id
            self.previous_beatmap_hash = self.beatmap_checksum
            self.previous_beatmap_name = self.beatmap_text

            self.beatmap_id = -1
            self.beatmap_checksum = ""
            self.beatmap_text = ""

        if self.beatmap_checksum != new_match.beatmap_checksum:
            # New map has been chosen
            self.logger.info(f'Selected: {new_match.beatmap_text}')
            self.unready_players()

            # Unready players with no beatmap
            self.unready_players(SlotStatus.NoMap)

            # Lookup beatmap in database
            beatmap = beatmaps.fetch_by_checksum(new_match.beatmap_checksum)

            if beatmap:
                self.beatmap_id       = beatmap.id
                self.beatmap_text     = beatmap.full_name
                self.beatmap_checksum = beatmap.md5
                self.mode             = GameMode(beatmap.mode)
                beatmap_text          = beatmap.link
            else:
                self.beatmap_id       = new_match.beatmap_id
                self.beatmap_checksum = new_match.beatmap_checksum
                self.beatmap_text     = new_match.beatmap_text
                self.mode             = new_match.mode
                beatmap_text          = new_match.beatmap_text

            self.chat.send_message(
                app.session.banchobot,
                f'Selected: {beatmap_text}'
            )

        if self.team_type != new_match.team_type:
            # Changed team type
            if new_match.team_type in (
                TeamType.HeadToHead,
                TeamType.TagCoop
            ):
                new_team = SlotTeam.Neutral
            else:
                new_team = SlotTeam.Red

            for slot in self.slots:
                if slot.has_player:
                    slot.team = new_team

            self.team_type = new_match.team_type

            self.logger.info(f'Team type: {self.team_type.name}')

        if self.type != new_match.type:
            # Changed match type
            self.type = new_match.type
            self.logger.info(f'Match type: {self.type.name}')

        if self.scoring_type != new_match.scoring_type:
            # Changed scoring type
            self.scoring_type = new_match.scoring_type
            self.logger.info(f'Scoring type: {self.scoring_type.name}')

        if self.mode != new_match.mode:
            self.mode = new_match.mode
            self.logger.info(f'Mode: {self.mode.formatted}')

        if self.name != new_match.name:
            self.name = new_match.name
            self.logger.info(f'Name: {self.name}')

            # Update match name
            matches.update(
                self.db_match.id,
                {"name": self.name}
            )

        self.update()

    def kick_player(self, player: "OsuClient"):
        player.enqueue_packet(PacketType.BanchoMatchDisband, self.id)
        player.enqueue_channel_revoked(self.chat.resolve_name(player))
        self.chat.remove(player)
        player.match = None

        if (slot := self.get_slot(player)):
            slot.reset()

        if player == self.host and not self.persistent:
            # Transfer host to next player
            for slot in self.slots:
                if slot.has_player:
                    self.host = slot.player
                    self.host.enqueue_packet(PacketType.BanchoMatchTransferHost)

            events.create(
                self.db_match.id,
                type=EventType.Host,
                data={
                    'new': {'id': self.host_id, 'name': self.host.name},
                    'previous': {'id': player.id, 'name': player.name}
                }
            )

        self.logger.info(f'{player.name} was kicked from the match')
        self.update()

        if all(slot.empty for slot in self.slots) and not self.persistent:
            self.close()
            self.logger.info('Match was disbanded.')
            return

        if not matches.exists(self.db_match.id):
            # Match was already closed
            return

        events.create(
            self.db_match.id,
            type=EventType.Kick,
            data={
                'user_id': player.id,
                'name': player.name
            }
        )

    def ban_player(self, player: "OsuClient"):
        self.banned_players.append(player.id)

        if player in self.players:
            self.kick_player(player)

    def unban_player(self, player: "OsuClient"):
        if player.id in self.banned_players:
            self.banned_players.remove(player.id)

    def close(self):
        # Shutdown pending match timer
        self.starting = None

        if self.in_progress:
            for player in self.players:
                player.enqueue_packet(PacketType.BanchoMatchComplete)

        for player in self.players:
            self.kick_player(player)

            if player.id in self.referee_players and self in player.referee_matches:
                # Remove referee player from this match
                player.referee_matches.remove(self)

        for player in app.session.players.osu_in_lobby:
            player.enqueue_packet(PacketType.BanchoMatchDisband, self.id)

        app.session.matches.remove(self)
        app.session.channels.remove(self.chat)

        if not self.db_match:
            return

        last_game = events.fetch_last_by_type(
            self.db_match.id,
            type=EventType.Result
        )

        if not last_game:
            # No games were played
            matches.delete(self.db_match.id)
            return

        matches.update(self.db_match.id, {'ended_at': datetime.now()})
        events.create(self.db_match.id, type=EventType.Disband)

    def start(self):
        if self.player_count <= 0:
            self.logger.warning('Host tried to start match without any players')
            return

        if self.in_progress:
            self.logger.warning('Host tried to start match, but it was already in progress')
            return

        for slot in self.slots:
            if not slot.has_player:
                continue

            if slot.status == SlotStatus.NotReady:
                continue

            if slot.status != SlotStatus.NoMap:
                slot.status = SlotStatus.Playing

        playing_slots = [
            slot for slot in self.player_slots
            if slot.status == SlotStatus.Playing
        ]

        if not playing_slots:
            self.logger.info('Could not start match, because no one was ready.')
            self.chat.send_message(
                app.session.banchobot,
                'Match was not started, because no players were ready.'
            )
            return

        self.logger.info('Match started')
        self.in_progress = True
        self.update()

        for slot in playing_slots:
            slot.player.enqueue_packet(PacketType.BanchoMatchStart, self)

        self.chat.send_message(
            app.session.banchobot,
            'The match has started. Good luck, have fun!'
        )

        # Start score update loop
        self.schedule_score_updates()

        events.create(
            self.db_match.id,
            type=EventType.Start,
            data={
                'beatmap_id': self.beatmap_id,
                'beatmap_text': self.beatmap_text,
                'beatmap_hash': self.beatmap_checksum,
                'mode': self.mode.value,
                'team_mode': self.team_type.value,
                'scoring_mode': self.scoring_type.value,
                'mods': self.mods.value,
                'freemod': self.freemod,
                'host': self.host_id,
                'start_time': str(datetime.now())
            }
        )

    def abort(self):
        # Players that have been playing this round
        players = [
            slot.player for slot in self.slots
            if slot.status.value & SlotStatus.Playing.value
            and slot.has_player
        ]

        self.in_progress = False
        self.unready_players(SlotStatus.Playing)
        self.update()

        # The join success packet will reset the players to the setup screen
        for player in players:
            player.enqueue_packet(PacketType.BanchoMatchJoinSuccess, self)

        start_event = events.fetch_last_by_type(
            player.match.db_match.id,
            type=EventType.Start
        )

        events.create(
            player.match.db_match.id,
            type=EventType.Abort,
            data={
                'beatmap_id': self.beatmap_id,
                'beatmap_text': self.beatmap_text,
                'beatmap_hash': self.beatmap_checksum,
                'end_time': str(datetime.now()),
                'start_time': (
                    start_event.data['start_time']
                    if start_event else time.time()
                )
            }
        )

    def finish(self):
        if self.completion_timer:
            # Cancel the completion timer
            self.completion_timer.cancel()
            self.completion_timer = None

        # Get players that have been playing this round
        players = [
            slot.player for slot in self.slots
            if slot.completed
        ]

        self.unready_players(SlotStatus.Complete)
        self.in_progress = False

        for p in players:
            p.enqueue_packet(PacketType.BanchoMatchComplete)

        self.logger.info('Match finished')
        self.update()

        self.chat.send_message(
            app.session.banchobot,
            'The match has finished!'
        )

        start_event = events.fetch_last_by_type(
            self.db_match.id,
            type=EventType.Start
        )

        if not start_event:
            return

        ranking_type = {
            ScoringType.Score: lambda s: s.last_frame.total_score,
            ScoringType.Accuracy: lambda s: s.last_frame.accuracy(self.mode),
            ScoringType.Combo: lambda s: s.last_frame.max_combo
        }[self.scoring_type]

        slots = [slot for slot in self.slots if slot.last_frame]
        slots.sort(key=ranking_type, reverse=True)

        match_results = [
            (rank, slot)
            for rank, slot in enumerate(slots)
            if (slot != None) and (slot.player != None)
        ]

        if not match_results:
            return

        events.create(
            self.db_match.id,
            type=EventType.Result,
            data={
                'beatmap_id': self.beatmap_id,
                'beatmap_text': self.beatmap_text,
                'beatmap_hash': self.beatmap_checksum,
                'mode': self.mode.value,
                'team_mode': self.team_type.value,
                'scoring_mode': self.scoring_type.value,
                'mods': self.mods.value,
                'freemod': self.freemod,
                'host': self.host_id,
                'start_time': start_event.data['start_time'],
                'end_time': str(datetime.now()),
                'results': [
                    {
                        'player': {
                            'id': slot.player.id,
                            'name': slot.player.name,
                            'country': slot.player.object.country,
                            'team': slot.team.value,
                            'mods': slot.mods.value
                        },
                        'score': {
                            'c300': slot.last_frame.total_300,
                            'c100': slot.last_frame.total_100,
                            'c50': slot.last_frame.total_50,
                            'cGeki': slot.last_frame.total_geki,
                            'cKatu': slot.last_frame.total_katu,
                            'cMiss': slot.last_frame.total_miss,
                            'score': slot.last_frame.total_score,
                            'accuracy': round(slot.last_frame.accuracy(self.mode) * 100, 2),
                            'max_combo': slot.last_frame.max_combo,
                            'perfect': slot.last_frame.perfect,
                            'failed': slot.has_failed,
                            'grade': slot.last_frame.rank(self.mode, slot.mods).name
                        },
                        'place': rank + 1
                    }
                    for rank, slot in match_results
                ]
            }
        )

    def send_referee_message(self, message: str, sender: "Client") -> None:
        for referee in self.referee_players:
            if referee_client := app.session.players.by_id_osu(referee):
                referee_client.enqueue_message(
                    message,
                    sender,
                    self.chat.name
                )

            if referee_client := app.session.players.by_id_irc(referee):
                referee_client.enqueue_message(
                    message,
                    sender,
                    self.chat.name
                )

    def execute_start_timer(self) -> None:
        if not self.starting:
            self.logger.warning('Tried to execute starting timer, but match was not starting.')
            return

        remaining_time = round(self.starting.time - time.time())
        intervals = [60, 30, 10, 5, 4, 3, 2, 1]

        if remaining_time in intervals:
            intervals.remove(remaining_time)

        self.logger.debug(
            f'Match countdown starting: {remaining_time} seconds left'
        )

        for interval in intervals:
            if remaining_time < interval:
                continue

            until_next_message = remaining_time - interval

            while until_next_message > 0:
                if not self.starting:
                    # Timer was cancelled
                    return

                time.sleep(1)
                until_next_message -= 1

            remaining_time = round(self.starting.time - time.time())

            self.chat.send_message(
                app.session.banchobot,
                f'Match starts in {remaining_time} {"seconds" if remaining_time != 1 else "second"}.'
            )

            self.logger.debug(f'Match countdown running: {remaining_time} seconds left')

        time.sleep(1)
        self.starting = None
        self.start()

    def execute_countdown(self) -> None:
        if not self.countdown:
            self.logger.warning('Tried to execute countdown, but timer was not present.')
            return

        remaining_time = round(self.countdown.time - time.time())
        intervals = [60, 30, 10, 5, 4, 3, 2, 1]
    
        if remaining_time in intervals:
            intervals.remove(remaining_time)

        self.logger.debug(
            f'Countdown running: {remaining_time} seconds left'
        )

        for interval in intervals:
            if remaining_time < interval:
                continue

            until_next_message = remaining_time - interval

            while until_next_message > 0:
                if not self.countdown:
                    # Timer was cancelled
                    return

                time.sleep(1)
                until_next_message -= 1

            remaining_time = round(self.countdown.time - time.time())

            self.chat.send_message(
                app.session.banchobot,
                f'Countdown ends in {remaining_time} {"seconds" if remaining_time != 1 else "second"}.'
            )

            self.logger.debug(f'Countdown running: {remaining_time} seconds left')

        time.sleep(1)
        self.countdown = None

        self.chat.send_message(
            app.session.banchobot,
            'Countdown finished.'
        )

    def schedule_score_updates(self) -> None:
        if not self.in_progress:
            return

        if self.score_thread and self.score_thread.is_alive():
            # Let's hope this never happens, it *should* never happen
            self.logger.warning('Score thread is still running, aborting...')
            return

        self.score_thread = Thread(
            target=self.process_score_updates,
            name=f'Match {self.id} Score Processor',
            daemon=True
        )
        self.score_thread.start()

    def process_score_updates(self) -> None:
        # Wait for first score frame, without timeout
        scoreframe = self.score_queue.get()
        target_players = self.players

        if not scoreframe:
            self.logger.warning('Score processor started without any score frame.')
            return

        # Broadcast first score frame and proceed to loop
        for p in target_players:
            p.enqueue_packet(PacketType.BanchoMatchScoreUpdate, scoreframe)

        self.last_activity = time.time()

        while self.in_progress or not self.score_queue.empty():
            try:
                scoreframe = self.score_queue.get(timeout=6)
            except Exception:
                continue

            if not scoreframe:
                continue

            for p in target_players:
                p.enqueue_packet(PacketType.BanchoMatchScoreUpdate, scoreframe)

        self.logger.info('Score processor finished.')
        self.score_thread = None

    def schedule_finish_timeout(self) -> None:
        if self.completion_timer:
            return

        self.completion_timer = Timer(12, self.finish_timeout)
        self.completion_timer.start()

    def finish_timeout(self) -> None:
        self.completion_timer = None

        if not self.in_progress:
            return

        for slot in self.player_slots:
            if not slot.is_playing:
                continue

            # Force-update slot status to complete
            slot.status = SlotStatus.Complete

        # Force-finish the match
        self.update()
        self.finish()
