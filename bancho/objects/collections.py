
from typing import (
    Iterable,
    Optional,
    Iterator,
    List,
    Set
)

from ..constants import ResponsePacket
from .channel    import Channel

class Channels(List[Channel]):
    def __iter__(self) -> Iterator[Channel]:
        return super().__iter__()

    @property
    def names(self) -> Set[str]:
        return {c.display_name for c in self}

    @property
    def topics(self) -> Set[str]:
        return {c.topic for c in self}
    
    def by_name(self, name: str) -> Optional[Channel]:
        for c in self:
            if c.name == name:
                return c
        return None
    
    def append(self, c: Channel) -> None:
        if c: return super().append(c)

    def remove(self, c: Channel) -> None:
        if c: return super().remove(c)

    def extend(self, channels: Iterable[Channel]) -> None:
        return super().extend(channels)

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

    def append(self, player: Player) -> None:
        self.enqueue_player(player)
        if player not in self: return super().append(player)
    
    def remove(self, player: Player) -> None:
        self.exit(player)
        if player in self: return super().remove(player)

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

    def exit(self, player: Player):
        if not player.restricted:
            for p in self:
                p.handler.enqueue_exit(player)

    def enqueue_stats(self, player: Player):
        if player.restricted:
            return
        
        for p in self:
            p.handler.enqueue_stats(player)

    def enqueue_player(self, player: Player):
        for p in self:
            if p is not player:
                p.handler.enqueue_player(player)
    
    def enqueue_channel(self, channel):
        for p in self:
            p.handler.enqueue_channel(channel)
