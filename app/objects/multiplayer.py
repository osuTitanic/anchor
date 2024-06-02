
from __future__ import annotations

from twisted.python.failure import Failure
from twisted.internet import threads

from dataclasses import dataclass
from typing import Tuple, List
from datetime import datetime
from threading import Thread
from queue import Queue

from app.common.constants import (
    MatchScoringTypes,
    MatchTeamTypes,
    SlotStatus,
    EventType,
    MatchType,
    SlotTeam,
    GameMode,
    Mods
)

from app.common.database.repositories import beatmaps, events, matches
from app.common.objects import bMatch, bSlot, bScoreFrame
from app.common.database import DBMatch
from app.common import officer

from .channel import Channel
from .player import Player

import logging
import config
import time
import app

class Slot:
    def __init__(self) -> None:
        self.last_frame: bScoreFrame | None = None
        self.player: Player | None = None
        self.status     = SlotStatus.Open
        self.team       = SlotTeam.Neutral
        self.mods       = Mods.NoMod
        self.has_failed = False
        self.loaded     = False
        self.skipped    = False

    def __repr__(self) -> str:
        return f'<Slot [{self.player.name if self.player else None}]: {self.status.name}>'

    @property
    def bancho_slot(self) -> bSlot:
        return bSlot(
            self.player.id if self.has_player else -1,
            self.status,
            self.team,
            self.mods
        )

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
        self.team   = other.team
        self.mods   = other.mods

    def reset(self, new_status = SlotStatus.Open) -> None:
        self.player     = None
        self.status     = new_status
        self.team       = SlotTeam.Neutral
        self.mods       = Mods.NoMod
        self.loaded     = False
        self.skipped    = False
        self.has_failed = False

@dataclass(slots=True)
class StartingTimers:
    time: float
    thread: Thread

class Match:
    def __init__(
        self,
        id: int,
        name: str,
        password: str,
        host: Player,
        beatmap_id: int,
        beatmap_name: str,
        beatmap_hash: str,
        mode: GameMode,
        seed: int = 0
    ) -> None:
        self.id       = id
        self.name     = name
        self.password = password
        self.host = host

        self.beatmap_id   = beatmap_id
        self.beatmap_name = beatmap_name
        self.beatmap_hash = beatmap_hash

        self.previous_beatmap_id   = beatmap_id
        self.previous_beatmap_name = beatmap_name
        self.previous_beatmap_hash = beatmap_hash

        self.mods = Mods.NoMod
        self.mode = mode
        self.seed = seed

        self.type         = MatchType.Standard
        self.scoring_type = MatchScoringTypes.Score
        self.team_type    = MatchTeamTypes.HeadToHead
        self.freemod      = False
        self.in_progress  = False

        self.slots = [Slot() for _ in range(config.MULTIPLAYER_MAX_SLOTS)]
        self.banned_players = []

        self.starting: StartingTimers | None = None
        self.db_match: DBMatch | None = None
        self.chat: Channel | None = None

        self.logger = logging.getLogger(f'multi_{self.id}')
        self.last_activity = time.time()
        self.score_queue = Queue()

    @classmethod
    def from_bancho_match(cls, bancho_match: bMatch, host_player: Player):
        return Match(
            bancho_match.id,
            bancho_match.name,
            bancho_match.password,
            host_player,
            bancho_match.beatmap_id,
            bancho_match.beatmap_text,
            bancho_match.beatmap_checksum,
            bancho_match.mode,
            bancho_match.seed
        )

    @property
    def bancho_match(self) -> bMatch:
        return bMatch(
            self.id,
            self.in_progress,
            self.type,
            self.mods,
            self.name,
            self.password,
            self.beatmap_name,
            self.beatmap_id,
            self.beatmap_hash,
            [s.bancho_slot for s in self.slots],
            self.host.id,
            self.mode,
            self.scoring_type,
            self.team_type,
            self.freemod,
            self.seed
        )

    @property
    def players(self) -> List[Player]:
        """Return all players"""
        return [slot.player for slot in self.player_slots]

    @property
    def url(self) -> str:
        """Url, used to join a match"""
        return f'osump://{self.id}/{self.password}'

    @property
    def embed(self) -> str:
        """Embed that will be sent on invite"""
        return f'[{self.url} {self.name}]'

    @property
    def host_slot(self) -> Slot | None:
        for slot in self.slots:
            if slot.status.value & SlotStatus.HasPlayer.value and slot.player is self.host:
                return slot

        return None

    @property
    def ffa(self) -> bool:
        return True if self.team_type in [MatchTeamTypes.TagTeamVs, MatchTeamTypes.TeamVs] else False

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
                slot.player.client.version.date > 323
            )
        ]

    def get_slot(self, player: Player) -> Slot | None:
        for slot in self.slots:
            if player is slot.player:
                return slot

        return None

    def get_slot_id(self, player: Player) -> int | None:
        for index, slot in enumerate(self.slots):
            if player is slot.player:
                return index

        return None

    def get_slot_with_id(self, player: Player) -> Tuple[Slot, int | None]:
        for index, slot in enumerate(self.slots):
            if player is slot.player:
                return slot, index

        return None, None

    def get_free(self) -> int | None:
        for index, slot in enumerate(self.slots):
            if slot.status == SlotStatus.Open:
                return index

        return None

    def get_player(self, name: str) -> Player | None:
        for player in self.players:
            if player.name == name:
                return player

        return None

    def update(self, lobby=True) -> None:
        # Enqueue to our players
        for player in self.players:
            player.enqueue_match(
                self.bancho_match,
                send_password=True,
                update=True
            )

        if not lobby:
            return

        # Enqueue to lobby players
        for player in app.session.players.in_lobby:
            player.enqueue_match(
                self.bancho_match,
                update=True
            )

    def unready_players(self, expected = SlotStatus.Ready):
        for slot in self.slots:
            if slot.status != expected:
                continue

            slot.status = SlotStatus.NotReady
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
            self.previous_beatmap_hash = self.beatmap_hash
            self.previous_beatmap_name = self.beatmap_name

            self.beatmap_id = -1
            self.beatmap_hash = ""
            self.beatmap_name = ""

        if self.beatmap_hash != new_match.beatmap_checksum:
            # New map has been chosen
            self.logger.info(f'Selected: {new_match.beatmap_text}')
            self.unready_players()

            # Unready players with no beatmap
            self.unready_players(SlotStatus.NoMap)

            # Lookup beatmap in database
            beatmap = beatmaps.fetch_by_checksum(new_match.beatmap_checksum)

            if beatmap:
                self.beatmap_id   = beatmap.id
                self.beatmap_hash = beatmap.md5
                self.beatmap_name = beatmap.full_name
                self.mode         = GameMode(beatmap.mode)
                beatmap_text      = beatmap.link
            else:
                self.beatmap_id   = new_match.beatmap_id
                self.beatmap_hash = new_match.beatmap_checksum
                self.beatmap_name = new_match.beatmap_text
                self.mode         = new_match.mode
                beatmap_text      = new_match.beatmap_text

            self.chat.send_message(
                app.session.bot_player,
                f'Selected: {beatmap_text}'
            )

        if self.team_type != new_match.team_type:
            # Changed team type
            if new_match.team_type in (
                MatchTeamTypes.HeadToHead,
                MatchTeamTypes.TagCoop
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
                {
                    "name": self.name
                }
            )

        self.update()

    def kick_player(self, player: Player):
        player.enqueue_match_disband(self.id)
        player.revoke_channel('#multiplayer')
        self.chat.remove(player)
        player.match = None

        if (slot := self.get_slot(player)):
            slot.reset()

        self.logger.info(
            f'{player.name} was kicked from the match'
        )

        events.create(
            self.db_match.id,
            type=EventType.Kick,
            data={
                'user_id': player.id,
                'name': player.name
            }
        )

        if player == self.host:
            # Transfer host to next player
            for slot in self.slots:
                if slot.status.value & SlotStatus.HasPlayer.value:
                    self.host = slot.player
                    self.host.enqueue_match_transferhost()

            events.create(
                self.db_match.id,
                type=EventType.Host,
                data={
                    'new': {'id': self.host.id, 'name': self.host.name},
                    'previous': {'id': player.id, 'name': player.name}
                }
            )

        self.update()

    def ban_player(self, player: Player):
        self.banned_players.append(player.id)

        if player in self.players:
            self.kick_player(player)

    def unban_player(self, player: Player):
        if player.id in self.banned_players:
            self.banned_players.remove(player.id)

    def close(self):
        # Shutdown pending match timer
        self.starting = None

        app.session.matches.remove(self)

        if self.in_progress:
            for player in self.players:
                player.enqueue_match_complete()

        for player in self.players:
            self.kick_player(player)
            self.chat.remove(player)
            player.enqueue_match_disband(self.id)
            player.match = None

        for player in app.session.players.in_lobby:
            player.enqueue_match_disband(self.id)

        app.session.channels.remove(self.chat)

        last_game = events.fetch_last_by_type(
            self.db_match.id,
            type=EventType.Result
        )

        if not last_game:
            # No games were played
            matches.delete(self.db_match.id)
        else:
            matches.update(self.db_match.id, {'ended_at': datetime.now()})
            events.create(self.db_match.id, type=EventType.Disband)

    def start(self):
        if self.player_count <= 0:
            self.logger.warning('Host tried to start match without any players')
            return

        for slot in self.slots:
            if not slot.has_player:
                continue

            if slot.status == SlotStatus.NotReady:
                continue

            slot.player.enqueue_match_start(self.bancho_match)

            if slot.status != SlotStatus.NoMap:
                slot.status = SlotStatus.Playing

        playing_slots = [s for s in self.player_slots if s.status == SlotStatus.Playing]

        if not playing_slots:
            self.logger.info('Could not start match, because no one was ready.')
            return

        self.in_progress = True
        self.score_queue = Queue()

        # Execute score queue
        threads.deferToThread(self._process_score_queue) \
               .addErrback(self._score_queue_callback)

        self.logger.info('Match started')
        self.update()

        events.create(
            self.db_match.id,
            type=EventType.Start,
            data={
                'beatmap_id': self.beatmap_id,
                'beatmap_text': self.beatmap_name,
                'beatmap_hash': self.beatmap_hash,
                'mode': self.mode.value,
                'team_mode': self.team_type.value,
                'scoring_mode': self.scoring_type.value,
                'mods': self.mods.value,
                'freemod': self.freemod,
                'host': self.host.id,
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

        self.unready_players(SlotStatus.Playing)
        self.in_progress = False

        # The join success packet will reset the players to the setup screen
        for player in players:
            player.enqueue_matchjoin_success(self.bancho_match)

        start_event = events.fetch_last_by_type(
            player.match.db_match.id,
            type=EventType.Start
        )

        events.create(
            player.match.db_match.id,
            type=EventType.Abort,
            data={
                'beatmap_id': self.beatmap_id,
                'beatmap_text': self.beatmap_name,
                'beatmap_hash': self.beatmap_hash,
                'start_time': start_event.data['start_time'],
                'end_time': str(datetime.now())
            }
        )

        self.update()

    def execute_timer(self) -> None:
        if not self.starting:
            self.logger.warning('Tried to execute timer, but match was not starting.')
            return

        remaining_time = round(self.starting.time - time.time())
        intervals = [60, 30, 10, 5, 4, 3, 2, 1]

        if remaining_time in intervals:
            intervals.remove(remaining_time)

        self.logger.debug(f'Match timer starting: {remaining_time} seconds left')

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
                app.session.bot_player,
                f'Match starting in {remaining_time} {"seconds" if remaining_time != 1 else "second"}.'
            )

            self.logger.debug(f'Match timer running: {remaining_time} seconds left')

        time.sleep(1)

        self.chat.send_message(
            app.session.bot_player,
            'Match was started. Good luck!'
        )

        self.starting = None
        self.start()

    def _process_score_queue(self) -> None:
        # NOTE: When the score packets don't get sent in the
        #       right order, the match scoreboard will lock
        #       up and the match cannot be finished.

        # Wait until all players have loaded
        while not all(self.loaded_players):
            if not self.in_progress:
                # Match was aborted
                return
            time.sleep(0.5)

        while self.in_progress:
            scoreframe = self.score_queue.get()

            for p in self.players:
                p.enqueue_score_update(scoreframe)

            for p in app.session.players.in_lobby:
                p.enqueue_score_update(scoreframe)

            self.score_queue.task_done()

    def _score_queue_callback(self, error: Failure) -> None:
        officer.call(
            f'Failed to process score queue: "{error.getErrorMessage()}"',
            exc_info=error.value
        )
