
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
            self.player.id if self.player else -1,
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
        self.mods    = Mods
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
        self.previous_id  = self.beatmap_id

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
    def player_slots(self) -> List[Slot]:
        return [slot for slot in self.slots if slot.has_player]

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

    def update(self, lobby=True) -> None:
        # Enqueue to our players
        for player in self.players:
            player.enqueue_match(
                self.bancho_match,
                update=True
            )

        # Enqueue to lobby players
        if lobby:
            for player in app.session.players.in_lobby:
                player.enqueue_match(
                    self.bancho_match,
                    update=True
                )
