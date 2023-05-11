
from typing import List, Optional

from bancho.constants import (
    MatchScoringTypes,
    MatchTeamTypes,
    SlotStatus,
    MatchType,
    SlotTeam,
    Mode,
    Mod
)

from .channel import Channel
from .player  import Player

class Slot:
    def __init__(self) -> None:
        self.player: Optional[Player] = None
        self.status  = SlotStatus.Open
        self.team    = SlotTeam.Neutral
        self.mods    = [Mod.NoMod]
        self.loaded  = False
        self.skipped = False

    def __repr__(self) -> str:
        return f'<Slot[{self.player}]: {self.status.name}>'

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
        self.mods    = [Mod.NoMod]
        self.loaded  = False
        self.skipped = False

class Match:
    def __init__(self, id: int, name: str, password: str, host: Player, beatmap_id: int, beatmap_name: str, beatmap_hash: str, mode: Mode) -> None:
        self.id       = id
        self.name     = name
        self.password = password
        
        self.host = host

        self.beatmap_id   = beatmap_id
        self.beatmap_name = beatmap_name
        self.beatmap_hash = beatmap_hash
        self.previous_id  = self.beatmap_id
        
        self.mods: List[Mod] = [Mod.NoMod]
        self.mode: Mode      = mode
        
        self.type          = MatchType.Standard
        self.scoring_type  = MatchScoringTypes.Score
        self.team_type     = MatchTeamTypes.HeadToHead
        self.freemod       = False
        self.in_progress   = False

        self.slots         = [Slot() for _ in range(8)]

        self.chat: Optional[Channel] = None

    @property
    def host_slot(self) -> Optional[Slot]:
        for slot in self.slots:
            if slot.status.value & SlotStatus.HasPlayer.value and slot.player is self.host:
                return slot

        return None

    @property
    def player_slots(self) -> List[Slot]:
        return [slot for slot in self.slots if slot.has_player]

    @property
    def player_count(self) -> int:
        return len(self.player_slots)

    @property
    def ffa(self) -> bool:
        return True if self.team_type in [MatchTeamTypes.TagTeamVs, MatchTeamTypes.TeamVs] else False

    @property
    def slots_nomap(self) -> List[Slot]:
        slots: List[Slot] = []
        for slot in self.slots:
            if slot.has_player:
                if slot.status == SlotStatus.NoMap:
                    slots.append(slot)
        return slots

    @property
    def slots_withmap(self) -> List[Slot]:
        return [slot for slot in self.slots if slot not in self.slots_nomap and slot.has_player]

    @property
    def players(self) -> List[Player]:
        return [slot.player for slot in self.player_slots]

    @property
    def players_withmap(self) -> List[Player]:
        return [slot.player for slot in self.slots_withmap]

    @property
    def url(self):
        return f'osump://{self.id}/{self.password}'

    @property
    def embed(self):
        return f'[{self.url} {self.name}]'
    
    def enqueue_player_failed(self, slot_id: int):
        for player in self.players:
            player.handler.enqueue_match_player_failed(slot_id)

    def enqueue_player_skipped(self, slot_id: int):
        for player in self.players:
            player.handler.enqueue_match_player_skip(slot_id)

    def enqueue_skip(self):
        for player in self.players:
            player.handler.eneuque_match_skip()

    def check_mods(self, mods: List[Mod]) -> bool:
        return all(mod in self.mods for mod in mods)
