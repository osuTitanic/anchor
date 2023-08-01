
from typing import Set, List, Iterator, Optional

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
        # TODO: Enqueue player to others
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

# TODO: Channels
# TODO: IRC Players
# TODO: Matches