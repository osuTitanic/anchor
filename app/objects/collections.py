
from __future__ import annotations

from app.clients import (
    DefaultResponsePacket,
    DefaultRequestPacket
)

from enum import Enum
from typing import (
    Iterable,
    Iterator,
    List,
    Set
)

from ..http import HttpPlayer
from .player import Player

import app

class Players(List[Player]):
    def __iter__(self) -> Iterator[Player]:
        return super().__iter__()

    @property
    def ids(self) -> Set[int]:
        return {p.id for p in self}

    @property
    def in_lobby(self) -> List[Player]:
        return [p for p in self if p.in_lobby]

    @property
    def tourney_clients(self) -> List[Player]:
        return [p for p in self if p.is_tourney_client]

    @property
    def normal_clients(self) -> List[Player]:
        return [p for p in self if not p.is_tourney_client]

    @property
    def http_clients(self) -> List[HttpPlayer]:
        return [p for p in self if isinstance(p, HttpPlayer)]

    def append(self, player: Player) -> None:
        """Append a player to the collection"""
        self.send_player(player)
        if player.id not in self.ids or player.is_tourney_client:
            return super().append(player)

    def remove(self, player: Player) -> None:
        """Remove a player from the collection"""
        try:
            return super().remove(player)
        except ValueError:
            pass

    def enqueue(self, data: bytes, immune = []) -> None:
        """Send raw data to all players"""
        for p in self:
            if p not in immune:
                p.enqueue(data)

    def by_id(self, id: int) -> Player | None:
        """Get a player by id"""
        if id == 1:
            return app.session.bot_player

        for p in self.normal_clients:
            if p.id == id:
                return p

        for p in self.tourney_clients:
            if p.id == id:
                return p

        return None

    def by_name(self, name: str) -> Player | None:
        """Get a player by name"""
        if name == app.session.bot_player.name:
            return app.session.bot_player

        for p in self.normal_clients:
            if p.name == name:
                return p

        for p in self.tourney_clients:
            if p.name == name:
                return p

        return None

    def by_token(self, token: str) -> Player | None:
        """Get a player by token"""
        for p in self.http_clients:
            if p.token == token:
                return p

        return None

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

    def send_presence(self, player: Player):
        for p in self:
            p.enqueue_presence(player)

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

class Channels(List[Channel]):
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

        if c not in self: return super().append(c)

    def remove(self, c: Channel) -> None:
        """Remove a channel from the collection"""
        if not c:
            return

        # Revoke channel to all users
        for p in c.users:
            p.revoke_channel(c.display_name)

        if c in self: return super().remove(c)

    def extend(self, channels: Iterable[Channel]) -> None:
        return super().extend(channels)

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

# TODO: IRC Players
