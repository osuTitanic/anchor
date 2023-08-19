
from typing import Optional, Tuple, List

from app.common.constants import (
    MatchScoringTypes,
    MatchTeamTypes,
    SlotStatus,
    MatchType,
    SlotTeam,
    GameMode,
    Mods
)

from app.common.database.repositories import beatmaps
from app.common.objects import bMatch, bSlot

from .channel import Channel
from .player import Player

import logging
import time
import app

class Slot:
    def __init__(self) -> None:
        self.player: Optional[Player] = None
        self.status  = SlotStatus.Open
        self.team    = SlotTeam.Neutral
        self.mods    = Mods.NoMod
        self.loaded  = False
        self.skipped = False

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

    def copy_from(self, other) -> None:
        self.player = other.player
        self.status = other.status
        self.team   = other.team
        self.mods   = other.mods

    def reset(self, new_status = SlotStatus.Open) -> None:
        self.player  = None
        self.status  = new_status
        self.team    = SlotTeam.Neutral
        self.mods    = Mods.NoMod
        self.loaded  = False
        self.skipped = False

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

        self.mods = Mods.NoMod
        self.mode = mode
        self.seed = seed

        self.type          = MatchType.Standard
        self.scoring_type  = MatchScoringTypes.Score
        self.team_type     = MatchTeamTypes.HeadToHead
        self.freemod       = False
        self.in_progress   = False

        self.slots = [Slot() for _ in range(8)]

        self.chat: Optional[Channel] = None

        self.logger = logging.getLogger(f'multi_{self.id}')
        self.last_activity = time.time()

    @classmethod
    def from_bancho_match(cls, bancho_match: bMatch):
        return Match(
            bancho_match.id,
            bancho_match.name,
            bancho_match.password,
            app.session.players.by_id(
                bancho_match.host_id
            ),
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
    def host_slot(self) -> Optional[Slot]:
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
        return [slot.loaded for slot in self.slots if slot.has_map]

    def get_slot(self, player: Player) -> Optional[Slot]:
        for slot in self.slots:
            if player is slot.player:
                return slot

        return None

    def get_slot_id(self, player: Player) -> Optional[int]:
        for index, slot in enumerate(self.slots):
            if player is slot.player:
                return index

        return None

    def get_slot_with_id(self, player: Player) -> Optional[Tuple[Slot, int]]:
        for index, slot in enumerate(self.slots):
            if player is slot.player:
                return slot, index

        return None, None

    def get_free(self) -> Optional[int]:
        for index, slot in enumerate(self.slots):
            if slot.status == SlotStatus.Open:
                return index

        return None

    def get_player(self, name: str) -> Optional[Player]:
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

        # Enqueue to lobby players
        if lobby:
            for player in app.session.players.in_lobby:
                player.enqueue_match(
                    self.bancho_match,
                    update=True
                )

    def unready_players(self, expected = SlotStatus.Ready):
        for slot in self.slots:
            if slot.status == expected:
                slot.status = SlotStatus.NotReady

    def change_settings(self, new_match: bMatch):
        if self.freemod != new_match.freemod:
            # Freemod state has been changed
            self.unready_players()
            self.freemod = new_match.freemod
            self.logger.info(f'Freemod: {self.freemod}')

            if self.freemod:
                for slot in self.slots:
                    if slot.status.value & SlotStatus.HasPlayer.value:
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

            self.beatmap_id = -1
            self.beatmap_hash = ""
            self.beatmap_name = ""

        if self.beatmap_hash != new_match.beatmap_checksum:
            # New map has been chosen
            self.logger.info(f'Selected: {new_match.beatmap_text}')
            self.unready_players()

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
            # TODO: Check osu! mania support

        if self.name != new_match.name:
            self.name = new_match.name
            self.logger.info(f'Name: {self.name}')

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

    def close(self):
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

    def start(self):
        if self.player_count <= 0:
            self.logger.warning('Host tried to start match without any players')
            return

        self.in_progress = True

        for slot in self.slots:
            if not slot.has_player:
                continue

            # TODO: Check osu! mania support

            slot.player.enqueue_match_start(self.bancho_match)

            if slot.status != SlotStatus.NoMap:
                slot.status = SlotStatus.Playing

        self.logger.info('Match started')
        self.update()

    def abort(self):
        self.unready_players(SlotStatus.Playing)
        self.in_progress = False

        # Players that have been playing this round
        players = [
            slot.player for slot in self.slots
            if slot.status.value & SlotStatus.Complete.value
            and slot.has_player
        ]

        for player in players:
            player.enqueue_match_complete()

        self.update()
