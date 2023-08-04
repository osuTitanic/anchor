
from typing import Optional

from app.common.constants import (
    MatchScoringTypes,
    MatchTeamTypes,
    SlotStatus,
    MatchType,
    SlotTeam,
    GameMode,
    Mods
)

from .channel import Channel
from .player import Player

import logging

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
        mode: GameMode
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

        self.type          = MatchType.Standard
        self.scoring_type  = MatchScoringTypes.Score
        self.team_type     = MatchTeamTypes.HeadToHead
        self.freemod       = False
        self.in_progress   = False

        self.slots = [Slot() for _ in range(8)]

        self.chat: Optional[Channel] = None

        self.logger = logging.getLogger(f'multi_{self.id}')
