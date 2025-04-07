
from __future__ import annotations
from enum import Enum
from typing import (
    Iterable,
    Iterator,
    Tuple,
    Dict,
    List,
    Set
)

from ..http import HttpPlayer
from .player import Player

class Players:
    def __init__(self):
        self.id_mapping: Dict[int, Player] = {}
        self.name_mapping: Dict[str, Player] = {}
        self.token_mapping: Dict[str, Player] = {}
        self.tourney_clients: List[Player] = []
        self.in_lobby: List[Player] = []

    def __repr__(self) -> str:
        return f'<Players ({len(self)})>'

    def __iter__(self):
        return iter(self.id_mapping.values())

    def __len__(self):
        return len(self.id_mapping)
    
    def __getitem__(self, key: int | str) -> Player | None:
        """Get a player by id or name"""
        if isinstance(key, int):
            return self.by_id(key)
        elif isinstance(key, str):
            return self.by_name(key)
        return None
    
    def __contains__(self, player: Player | HttpPlayer) -> bool:
        """Check if a player is in the collection"""
        if isinstance(player, Player):
            return player.id in self.id_mapping
        elif isinstance(player, HttpPlayer):
            return player.token in self.token_mapping
        return False

    @property
    def http_clients(self) -> Tuple[HttpPlayer]:
        return tuple(p for p in self.token_mapping.values())

    @property
    def tcp_clients(self) -> Tuple[Player]:
        return tuple(p for p in self if p.protocol == 'tcp')

    def get(self, value: int | str) -> Player | None:
        """Get a player by id or name"""
        return self[value]

    def add(self, player: Player | HttpPlayer) -> None:
        """Append a player to the collection"""
        self.id_mapping[abs(player.id)] = player
        self.name_mapping[player.name] = player
        self.send_player(player)

        if isinstance(player, HttpPlayer):
            self.token_mapping[player.token] = player

        if player.is_tourney_client:
            self.tourney_clients.append(player)

    def remove(self, player: Player | HttpPlayer) -> None:
        """Remove a player from the collection"""
        try:
            del self.id_mapping[abs(player.id)]
            del self.name_mapping[player.name]
            del self.token_mapping[player.token]

            if player.in_lobby:
                self.in_lobby.remove(player)

            if player.is_tourney_client:
                self.tourney_clients.remove(player)
        except (ValueError, KeyError, AttributeError):
            pass

    def by_id(self, id: int) -> Player | None:
        """Get a player by id"""
        return self.id_mapping.get(id, None)

    def by_name(self, name: str) -> Player | None:
        """Get a player by name"""
        return self.name_mapping.get(name, None)

    def by_token(self, token: str) -> Player | None:
        """Get a player by token"""
        return self.token_mapping.get(token, None)

    def enqueue(self, data: bytes, immune = []) -> None:
        """Send raw data to all players"""
        for p in self:
            if p not in immune:
                p.enqueue(data)

    def get_all_tourney_clients(self, id: int) -> Tuple[Player]:
        """Get all tourney clients for a player id"""
        return tuple(p for p in self.tourney_clients if p.id == id)

    def get_rank_duplicates(self, rank: int, mode: int) -> Tuple[Player]:
        """Get all players with the specified rank"""
        return tuple(p for p in self if p.rank == rank and p.status.mode == mode)

    def send_packet(self, packet: Enum, *args):
        for p in self:
            p.send_packet(packet, *args)

    def send_player(self, player: Player):
        for p in self:
            p.enqueue_player(player)

    def send_player_bundle(self, players: List[Player]):
        for p in self:
            p.enqueue_players(players)

    def send_presence(self, player: Player, update: bool = False):
        for p in self:
            p.enqueue_presence(player, update)

    def send_stats(self, player: Player):
        for p in self:
            p.enqueue_stats(player)

    def announce(self, message: str):
        for p in self:
            p.enqueue_announcement(message)

    def send_user_quit(self, user_quit):
        for p in self:
            try:
                p.enqueue_quit(user_quit)
            except AttributeError:
                continue

from .channel import Channel

class Channels(Set[Channel]):
    def __iter__(self) -> Iterator[Channel]:
        return super().__iter__()

    @property
    def public(self) -> Set[Channel]:
        """All publicly available channels"""
        return {c for c in self if c.public}

    def by_name(self, name: str) -> Channel | None:
        """Get a channel by name"""
        return next((c for c in self if c.name == name), None)

    def append(self, c: Channel) -> None:
        """Append a channel to the collection"""
        if not c:
            return

        if c not in self:
            return super().add(c)

    def remove(self, c: Channel) -> None:
        """Remove a channel from the collection"""
        if not c:
            return

        # Revoke channel to all users
        for p in c.users:
            p.revoke_channel(c.display_name)

        if c in self:
            return super().remove(c)

    def extend(self, channels: Iterable[Channel]) -> None:
        return super().update(channels)

from .multiplayer import Match

class Matches(List[Match | None]):
    def __init__(self) -> None:
        super().__init__([None])

    def __iter__(self) -> Iterator[Match]:
        return super().__iter__()

    def __repr__(self) -> str:
        return f'[{", ".join(match.name for match in self if match)}]'

    @property
    def active(self) -> List[Match]:
        """All currently active matches"""
        return [m for m in self if m]

    def get_free(self) -> int | None:
        """Get a free match slot"""
        for index, match in enumerate(self):
            if match is None:
                return index

        # Current match collection is full
        # Create new match slot
        super().append(None)

        return (len(self) - 1)

    def append(self, match: Match) -> bool:
        """Add match to collection and returns if successful"""
        if (free := self.get_free()) is not None:
            # Add match to list if free slot was found
            match.id = free
            self[free] = match
            return True

        return False

    def remove(self, match: Match) -> None:
        """Remove match from collection and remove all trailing, inactive matches from the collection."""
        for index, m in enumerate(self):
            if match == m:
                self[index] = None
                break

        # Remove all inactive trailing matches
        for index in range(len(self) - 1, -1, -1):
            if self[index] is not None:
                break

            # Remove inactive match
            self.pop(index)

    def exists(self, match_id: int) -> bool:
        """Check if a match exists"""
        try:
            return self[match_id] is not None
        except IndexError:
            return False

