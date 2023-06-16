
from typing import List, Optional, Tuple

from bancho.logging import Console, File
from bancho.constants import (
    MANIA_NOT_SUPPORTED,
    SPEED_MODS,
    ResponsePacket,
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

import logging
import bancho

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

        self.logger = logging.getLogger(f'multi_{self.id}')

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
        """Return the slots with no maps"""
        return [slot for slot in self.slots if slot.has_player and slot.status == SlotStatus.NoMap]

    @property
    def slots_withmap(self) -> List[Slot]:
        """Return the slots that have a map"""
        return [slot for slot in self.slots if slot not in self.slots_nomap and slot.has_player]

    @property
    def players(self) -> List[Player]:
        """Return all players"""
        return [slot.player for slot in self.player_slots]

    @property
    def players_withmap(self) -> List[Player]:
        """Return all players with a map"""
        return [slot.player for slot in self.slots_withmap]

    @property
    def url(self) -> str:
        """Url, used to join a match"""
        return f'osump://{self.id}/{self.password}'

    @property
    def embed(self) -> str:
        """Embed that will be sent on invite"""
        return f'[{self.url} {self.name}]'
    
    def enqueue_player_failed(self, slot_id: int):
        for player in self.players:
            player.handler.enqueue_match_player_failed(slot_id)

    def enqueue_player_skipped(self, slot_id: int):
        for player in self.players:
            player.handler.enqueue_match_player_skipped(slot_id)

    def enqueue_skip(self):
        for player in self.players:
            player.handler.enqueue_match_skip()

    def enqueue_score_update(self, data: bytes):
        players = self.players
        players.extend(
            bancho.services.players.in_lobby
        )

        for player in players:
            player.sendPacket(
                ResponsePacket.MATCH_SCORE_UPDATE,
                data
            )

    def check_mods(self, mods: List[Mod]) -> bool:
        return all(mod in self.mods for mod in mods)
    
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
            player.handler.enqueue_match(self, send_password=True, update=True)

        # Enqueue to lobby players
        if lobby:
            for player in bancho.services.players.in_lobby:
                player.handler.enqueue_match(self, update=True)

    def unready_players(self, expected = SlotStatus.Ready):
        for slot in self.slots:
            if slot.status == expected:
                slot.status = SlotStatus.NotReady

    def start(self):
        if self.player_count <= 1:
            # Player tries to start map with only himself
            return

        self.in_progress = True

        for slot in self.slots:
            if not slot.has_player:
                continue

            if self.mode == Mode.OsuMania and not slot.player.mania_support:
                slot.player.handler.enqueue_announcement(MANIA_NOT_SUPPORTED)
                slot.status = SlotStatus.NoMap
                continue

            slot.player.handler.enqueue_match_start(self)

            if slot.status != SlotStatus.NoMap:
                slot.status = SlotStatus.Playing

        self.logger.info('Match started')

        self.update()

    def check_mods(self, mods: List[Mod]) -> bool:
        return all(mod in self.mods for mod in mods)

    def remove_invalid_mods(self):
        # There is a bug, where NC and DT are enabled at the same time
        if self.check_mods([Mod.DoubleTime, Mod.Nightcore]):
            # It's most likely nightcore, that just got added
            self.mods.remove(Mod.DoubleTime)

        if self.check_mods([Mod.Easy, Mod.HardRock]):
            self.mods.remove(Mod.HardRock)

        if self.check_mods([Mod.HalfTime, Mod.DoubleTime]): 
            self.mods.remove(Mod.DoubleTime)

        if self.check_mods([Mod.HalfTime, Mod.Nightcore]): 
            self.mods.remove(Mod.Nightcore)

        if self.check_mods([Mod.NoFail, Mod.SuddenDeath]): 
            self.mods.remove(Mod.SuddenDeath)

        if self.check_mods([Mod.NoFail and Mod.Perfect]): 
            self.mods.remove(Mod.Perfect)

        if self.check_mods([Mod.Relax and Mod.Relax2]): 
            self.mods.remove(Mod.Relax2)

    def change_settings(self, new_match):
        if self.freemod != new_match.freemod:
            # Freemod state has been changed
            self.freemod = new_match.freemod
            self.logger.info(f'Freemod: {self.freemod}')

            if self.freemod:
                for slot in self.slots:
                    if slot.status.value & SlotStatus.HasPlayer.value:
                        # Set current mods to every player inside the match, if they are not speed mods
                        slot.mods = [mod for mod in self.mods if mod not in SPEED_MODS]

                        # Fix for older clients without freemod support
                        if slot.player.handler.protocol_version <= 15:
                            slot.mods = []
                
                # The speedmods are kept in the match mods
                self.mods = [mod for mod in self.mods if mod in SPEED_MODS]
            else:
                # Keep mods from host (Not on official servers)
                self.mods.extend(self.host_slot.mods)

                # Reset any mod from players
                for slot in self.slots:
                    slot.mods = [Mod.NoMod]

        if new_match.beatmap_id == -1:
            # Host is selecting new map, unready players
            self.logger.info('Host is selecting map...')

            self.beatmap_id = -1
            self.beatmap_hash = ""
            self.beatmap_name = ""
            self.previous_id = self.beatmap_id

        else:
            if self.previous_id != new_match.beatmap_id:
                # New map has been chosen
                self.chat.send_message(bancho.services.bot_player, f'Selected: {new_match.beatmap_name}')
                self.logger.info(f'Selected: {new_match.beatmap_name}')
                self.unready_players()

            # Lookup beatmap in database
            beatmap = bancho.services.database.beatmap_by_checksum(new_match.beatmap_hash)

            if beatmap:
                self.beatmap_id   = beatmap.id
                self.beatmap_hash = beatmap.md5
                self.beatmap_name = beatmap.full_name
                self.mode         = Mode(beatmap.mode)
            else:
                self.beatmap_id   = new_match.beatmap_id
                self.beatmap_hash = new_match.beatmap_hash
                self.beatmap_name = new_match.beatmap_name
                self.mode         = new_match.mode

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

        if self.scoring_type != new_match.scoring_type:
            # Changed scoring type
            self.scoring_type = new_match.scoring_type
            self.logger.info(f'Scoring type: {self.scoring_type.name}')

        if self.mode != new_match.mode:
            self.mode = new_match.mode
            self.logger.info(f'Mode: {self.mode.formatted}')

            if self.mode == Mode.OsuMania:
                for slot in self.slots:
                    if not slot.has_player:
                        continue
                    
                    if slot.player.mania_support:
                        continue
                    
                    slot.player.handler.enqueue_announcement(MANIA_NOT_SUPPORTED)

        if self.name != new_match.name:
            self.name = new_match.name
            self.logger.info(f'Name: {self.name}')

        self.update()
