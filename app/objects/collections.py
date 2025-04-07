
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

from .locks import ReadWriteLock
from ..http import HttpPlayer
from .player import Player

class Players:
    def __init__(self):
        self.id_mapping: Dict[int, Player] = {}
        self.name_mapping: Dict[str, Player] = {}
        self.token_mapping: Dict[str, Player] = {}
        self.tourney_clients: List[Player] = []
        self.in_lobby: List[Player] = []
        self.lock = ReadWriteLock()

    @property
    def tcp_clients(self) -> Tuple[Player]:
        return tuple(p for p in self if p.protocol == 'tcp')

    @property
    def http_clients(self) -> Tuple[HttpPlayer]:
        with self.lock.read_context():
            snapshot = tuple(self.token_mapping.values())
        return snapshot

    def __repr__(self) -> str:
        return '<Players>'

    def __len__(self):
        with self.lock.read_context():
            return len(self.id_mapping)

    def __setitem__(self, _, value: Player | HttpPlayer) -> None:
        """Set a player in the collection"""
        return self.add(value)

    def __getitem__(self, key: int | str) -> Player | None:
        """Get a player by id or name"""
        if isinstance(key, int):
            return self.by_id(key)
        elif isinstance(key, str):
            return self.by_name(key)
        return None

    def __iter__(self):
        with self.lock.read_context():
            snapshot = list(self.id_mapping.values())
        return iter(snapshot)

    def __contains__(self, player: Player | HttpPlayer) -> bool:
        """Check if a player is in the collection"""
        with self.lock.read_context():
            if isinstance(player, Player):
                return player.id in self.id_mapping
            elif isinstance(player, HttpPlayer):
                return player.token in self.token_mapping
            return False

    def get(self, value: int | str) -> Player | None:
        """Get a player by id or name"""
        return self[value]

    def add(self, player: Player | HttpPlayer) -> None:
        """Append a player to the collection"""
        with self.lock.write_context():
            self.id_mapping[abs(player.id)] = player
            self.name_mapping[player.name] = player

            if isinstance(player, HttpPlayer):
                self.token_mapping[player.token] = player

            if player.is_tourney_client:
                self.tourney_clients.append(player)
                
        self.send_player(player)

    def remove(self, player: Player | HttpPlayer) -> None:
        """Remove a player from the collection"""
        with self.lock.write_context():
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
        with self.lock.read_context():
            return self.id_mapping.get(id, None)

    def by_name(self, name: str) -> Player | None:
        """Get a player by name"""
        with self.lock.read_context():
            return self.name_mapping.get(name, None)

    def by_token(self, token: str) -> Player | None:
        """Get a player by token"""
        with self.lock.read_context():
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

class Channels(Dict[str, Channel]):
    def __repr__(self) -> str:
        return '<Channels>'

    @property
    def public(self) -> List[Channel]:
        """All publicly available channels"""
        return [c for c in self.values() if c.public]

    def by_name(self, name: str) -> Channel | None:
        """Get a channel by name"""
        return self.get(name, None)

    def add(self, c: Channel) -> None:
        """Append a channel to the collection"""
        if not c:
            return

        self[c.name] = c

    def remove(self, c: Channel) -> None:
        """Remove a channel from the collection"""
        if not c:
            return

        for p in c.users:
            p.revoke_channel(c.display_name)

        if c.name in self:
            del self[c.name]

from .multiplayer import Match

class Matches(List[Match | None]):
    def __init__(self) -> None:
        super().__init__([None])

    def __iter__(self) -> Iterator[Match]:
        return super().__iter__()

    def __repr__(self) -> str:
        return f'<Matches ({len(self)})>'

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
