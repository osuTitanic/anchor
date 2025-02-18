
from __future__ import annotations
from enum import Enum
from typing import (
    Iterable,
    Iterator,
    List,
    Set
)

from ..http import HttpPlayer
from .player import Player

import threading
import app

class Players(Set[Player | HttpPlayer]):
    def __init__(self):
        self.lock = threading.Lock()
        super().__init__()

    def __iter__(self) -> Iterator[Player]:
        with self.lock:
            players = iter(list(super().__iter__()))
        return players

    def __len__(self) -> int:
        with self.lock:
            return len(list(super().__iter__()))

    def __contains__(self, player: Player) -> bool:
        with self.lock:
            return super().__contains__(player)

    def __repr__(self) -> str:
        with self.lock:
            return f'<Players ({len(self)})>'

    @property
    def ids(self) -> Set[int]:
        return {p.id for p in self}

    @property
    def in_lobby(self) -> Set[Player]:
        return {p for p in self if p.in_lobby}

    @property
    def tourney_clients(self) -> Set[Player]:
        return {p for p in self if p.is_tourney_client}

    @property
    def normal_clients(self) -> Set[Player]:
        return {p for p in self if not p.is_tourney_client}

    @property
    def http_clients(self) -> Set[HttpPlayer]:
        return {p for p in self if isinstance(p, HttpPlayer)}

    @property
    def tcp_clients(self) -> Set[Player]:
        return {p for p in self if not isinstance(p, HttpPlayer)}

    def add(self, player: Player) -> None:
        """Append a player to the collection"""
        self.send_player(player)
        return super().add(player)

    def remove(self, player: Player) -> None:
        """Remove a player from the collection"""
        try:
            return super().remove(player)
        except (ValueError, KeyError):
            pass

    def enqueue(self, data: bytes, immune = []) -> None:
        """Send raw data to all players"""
        for p in self:
            if p not in immune:
                p.enqueue(data)

    def by_id(self, id: int) -> Player | None:
        """Get a player by id"""
        return next(
            (p for p in self if p.id == id),
            (app.session.banchobot if id == 1 else None)
        )

    def by_name(self, name: str) -> Player | None:
        """Get a player by name"""
        return next(
            (p for p in self if p.name == name),
            (app.session.banchobot if name == app.session.banchobot.name else None)
        )

    def by_token(self, token: str) -> Player | None:
        """Get a player by token"""
        return next(
            (p for p in self.http_clients if p.token == token),
            None
        )

    def get_all_tourney_clients(self, id: int) -> List[Player]:
        """Get all tourney clients for a player id"""
        return [p for p in self.tourney_clients if p.id == id]

    def get_rank_duplicates(self, rank: int, mode: int) -> List[Player]:
        """Get all players with the specified rank"""
        return [p for p in self if p.rank == rank and p.status.mode == mode]

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

