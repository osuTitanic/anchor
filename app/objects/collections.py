
from __future__ import annotations
from enum import Enum
from typing import (
    MutableMapping,
    Iterator,
    Tuple,
    Dict,
    List,
    Set
)

from app.protocols.osu.http import HttpOsuClient
from app.objects.locks import LockedDict
from app.clients.base import Client
from app.clients.osu import OsuClient
from app.clients.irc import IrcClient

class Players(MutableMapping[int | str, Client]):
    def __init__(self):
        # Lookup by id & name for osu! and irc clients
        self.irc_id_mapping: LockedDict[int, IrcClient] = LockedDict()
        self.irc_name_mapping: LockedDict[str, IrcClient] = LockedDict()
        self.osu_id_mapping: LockedDict[int, OsuClient] = LockedDict()
        self.osu_name_mapping: LockedDict[str, OsuClient] = LockedDict()

        # osu! specific
        self.osu_token_mapping: LockedDict[str, HttpOsuClient] = LockedDict()
        self.osu_tournament_clients: Set[OsuClient] = set()
        self.osu_in_lobby: Set[OsuClient] = set()

    @property
    def osu_clients(self) -> Tuple[OsuClient]:
        return tuple(self.osu_id_mapping.values())

    @property
    def irc_clients(self) -> Tuple[IrcClient]:
        return tuple(self.irc_id_mapping.values())
    
    @property
    def tcp_osu_clients(self) -> Tuple[OsuClient]:
        """Get all tcp osu! clients"""
        return tuple(p for p in self.osu_id_mapping.values() if p.protocol == 'tcp')
    
    @property
    def http_osu_clients(self) -> Tuple[HttpOsuClient]:
        """Get all http osu! clients"""
        return tuple(p for p in self.osu_token_mapping.values())

    def __repr__(self) -> str:
        return '<Players>'

    def __len__(self):
        return len(self.osu_id_mapping) + len(self.irc_id_mapping)

    def __setitem__(self, _, value: Client) -> None:
        """Set a player in the collection"""
        return self.add(value)

    def __getitem__(self, key: int | str) -> Client | None:
        """Get a player by id or name"""
        if isinstance(key, int):
            return self.by_id(key)
        elif isinstance(key, str):
            return self.by_name(key)
        return None

    def __delitem__(self, key: int | str) -> None:
        """Remove a player from the collection"""
        player = None

        if isinstance(key, int):
            player = self.by_id(key)
        elif isinstance(key, str):
            player = self.by_name(key)

        if player is not None:
            self.remove(player)

    def __iter__(self):
        snapshot_osu = list(self.osu_id_mapping.values())
        snapshot_irc = list(self.irc_id_mapping.values())
        return iter(snapshot_osu + snapshot_irc)

    def __contains__(self, player: Client) -> bool:
        """Check if a player is in the collection"""
        if isinstance(player, OsuClient):
            return player.id in self.osu_id_mapping
        elif isinstance(player, IrcClient):
            return player.id in self.irc_id_mapping
        return False

    def get(self, value: int | str) -> Client:
        """Get a player by id or name"""
        return self[value]

    def add(self, player: Client) -> None:
        """Append a player to the collection"""
        if isinstance(player, OsuClient):
            self.add_osu(player)
        elif isinstance(player, IrcClient):
            self.add_irc(player)

    def remove(self, player: Client) -> None:
        """Remove a player from the collection"""
        if isinstance(player, OsuClient):
            self.remove_osu(player)
        elif isinstance(player, IrcClient):
            self.remove_irc(player)

    def add_osu(self, player: OsuClient | HttpOsuClient) -> None:
        """Append a player to the collection"""
        self.osu_id_mapping[abs(player.id)] = player
        self.osu_name_mapping[player.name] = player

        if player.protocol == 'http':
            self.osu_token_mapping[player.token] = player

        if player.is_tourney_client:
            self.osu_tournament_clients.add(player)

        self.send_player(player)

    def remove_osu(self, player: OsuClient | HttpOsuClient) -> None:
        """Remove a player from the collection"""
        if player.in_lobby:
            self.remove_from_collection('in_lobby', player)

        if player.is_tourney_client:
            self.remove_from_collection('tourney_clients', player)

        self.remove_from_mapping('osu_id_mapping', abs(player.id))
        self.remove_from_mapping('osu_name_mapping', player.name)

        if player.protocol == 'http':
            self.remove_from_mapping('osu_token_mapping', player.token)

    def add_irc(self, player: IrcClient) -> None:
        """Append a player to the collection"""
        self.irc_id_mapping[player.id] = player
        self.irc_name_mapping[player.name] = player
        self.send_player(player)

    def remove_irc(self, player: IrcClient) -> None:
        """Remove a player from the collection"""
        self.remove_from_mapping('irc_id_mapping', player.id)
        self.remove_from_mapping('irc_name_mapping', player.name)

    def remove_from_mapping(self, name: str, key: str) -> None:
        try:
            del getattr(self, name)[key]
        except (KeyError, ValueError, AttributeError):
            pass

    def remove_from_collection(self, name: str, player: Client) -> None:
        """Remove a player from the collection"""
        try:
            getattr(self, name).remove(player)
        except (KeyError, ValueError, AttributeError):
            pass

    def by_id(self, id: int) -> Client | None:
        """Get a player by id"""
        return (
            self.osu_id_mapping.get(id, None) or
            self.irc_id_mapping.get(id, None)
        )

    def by_name(self, name: str) -> Client | None:
        """Get a player by name"""
        return (
            self.osu_name_mapping.get(name, None) or
            self.irc_name_mapping.get(name, None)
        )

    def by_name_safe(self, name: str) -> Client | None:
        """Get a player by underscored name"""
        return (
            self.osu_name_mapping.get(name, None) or
            self.osu_name_mapping.get(name.replace('_', ' '), None) or
            self.irc_name_mapping.get(name, None) or
            self.irc_name_mapping.get(name.replace('_', ' '), None)
        )

    def by_token(self, token: str) -> Client | None:
        """Get an osu! player by token"""
        return self.osu_token_mapping.get(token, None)

    def by_id_osu(self, id: int) -> OsuClient | None:
        """Get an osu! player by id"""
        return self.osu_id_mapping.get(id, None)
    
    def by_name_osu(self, name: str) -> OsuClient | None:
        """Get an osu! player by name"""
        return self.osu_name_mapping.get(name, None)

    def by_id_irc(self, id: int) -> IrcClient | None:
        """Get an irc player by id"""
        return self.irc_id_mapping.get(id, None)
    
    def by_name_irc(self, name: str) -> IrcClient | None:
        """Get an irc player by name"""
        return self.irc_name_mapping.get(name, None)

    def by_rank(self, rank: int, mode: int) -> List[Client]:
        """Get all players with the specified rank"""
        return [p for p in self.osu_clients if p.rank == rank and p.status.mode == mode]

    def tournament_clients(self, id: int) -> List[OsuClient]:
        """Get all connected tournament clients for a player"""
        return [p for p in self.osu_tournament_clients if p.id == id]

    def clear_tournament_clients(self, id: int) -> None:
        """Clear all tourney clients by player id"""
        for p in self.tournament_clients(id):
            self.remove(p)

    def send_packet(self, packet: Enum, *args) -> None:
        for p in self.osu_clients:
            p.enqueue_packet(packet, *args)

    def send_player(self, player: Client) -> None:
        for p in self:
            p.enqueue_player(player)

    def send_player_bundle(self, players: List[Client]) -> None:
        for p in self:
            p.enqueue_players(players)

    def send_presence(self, player: Client, update: bool = False) -> None:
        for p in self.osu_clients:
            p.enqueue_presence(player, update)

    def send_stats(self, player: OsuClient) -> None:
        for p in self.osu_clients:
            p.enqueue_stats(player)

    def send_announcement(self, message: str) -> None:
        for p in self:
            p.enqueue_announcement(message)

    def send_user_quit(self, player: Client) -> None:
        for p in self:
            p.enqueue_user_quit(player)

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

    @property
    def persistent(self) -> List[Match]:
        """All persistent matches"""
        return [m for m in self if m and m.persistent]

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
