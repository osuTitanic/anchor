
from app.clients import (
    DefaultResponsePacket,
    DefaultRequestPacket
)

from enum import Enum
from typing import (
    Iterable,
    Iterator,
    Optional,
    List,
    Set
)

from .player import Player

class Players(List[Player]):
    def __iter__(self) -> Iterator[Player]:
        return super().__iter__()
    
    @property
    def ids(self) -> Set[int]:
        return {p.id for p in self}

    @property
    def restricted(self) -> Set[Player]:
        return {p for p in self if p.restricted}

    @property
    def unrestricted(self) -> Set[Player]:
        return {p for p in self if not p.restricted}
    
    @property
    def in_lobby(self) -> Set[Player]:
        return {p for p in self if p.in_lobby}

    def append(self, player: Player) -> None:
        self.send_player(player)
        if player.id not in self.ids:
            return super().append(player)
    
    def remove(self, player: Player) -> None:
        try:
            return super().remove(player)
        except ValueError:
            pass

    def enqueue(self, data: bytes, immune = []) -> None:
        for p in self:
            if p not in immune:
                p.enqueue(data)
    
    def by_id(self, id: int) -> Optional[Player]:
        for p in self:
            if p.id == id:
                return p
        return None

    def by_name(self, name: str) -> Optional[Player]:
        for p in self:
            if p.name == name:
                return p
        return None

    def send_packet(self, packet: Enum, *args):
        for p in self:
            p.send_packet(packet, *args)

    def send_player(self, player: Player):
        self.send_packet(
            DefaultResponsePacket.USER_PRESENCE_SINGLE,
            player.id
        )

    def send_player_bundle(self, players: List[Player]):
        self.send_packet(
            DefaultResponsePacket.USER_PRESENCE_BUNDLE,
            [player.id for player in players]
        )

    def send_presence(self, player: Player):
        self.send_packet(
            DefaultResponsePacket.USER_PRESENCE,
            player.user_presence
        )

    def send_stats(self, player: Player):
        self.send_packet(
            DefaultResponsePacket.USER_STATS,
            player.user_stats
        )

from .channel import Channel

class Channels(List[Channel]):
    def __iter__(self) -> Iterator[Channel]:
        return super().__iter__()

    @property
    def names(self) -> Set[str]:
        return {c.display_name for c in self}

    @property
    def topics(self) -> Set[str]:
        return {c.topic for c in self}

    @property
    def public(self) -> Set[Channel]:
        return {c for c in self if c.public}

    def by_name(self, name: str) -> Optional[Channel]:
        for c in self:
            if c.name == name:
                return c
        return None

    def append(self, c: Channel) -> None:
        if not c:
            return

        if c not in self: return super().append(c)

    def remove(self, c: Channel) -> None:
        if not c:
            return

        # Revoke channel to all users
        for p in c.users:
            p.revoke_channel(c.display_name)

        if c in self: return super().remove(c)

    def extend(self, channels: Iterable[Channel]) -> None:
        return super().extend(channels)

from .multiplayer import Match

class Matches(List[Optional[Match]]):
    def __init__(self) -> None:
        super().__init__([None] * 64)

    def __iter__(self) -> Iterator[Match]:
        return super().__iter__()

    def __repr__(self) -> str:
        return f'[{", ".join(match.name for match in self if match)}]'

    def get_free(self) -> Optional[int]:
        for index, match in enumerate(self):
            if match is None:
                return index
        return None

    def append(self, match: Match) -> bool:
        if (free := self.get_free()) is not None:
            # Add match to list if free slot was found
            match.id = free
            self[free] = match

            return True
        else:
            return False

    def remove(self, match: Match) -> None:
        for index, _match in enumerate(self):
            if match is _match:
                self[index] = None
                break

# TODO: IRC Players
