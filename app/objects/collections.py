
from itertools import chain
from threading import RLock
from typing import Any
from collections.abc import (
    MutableMapping,
    ValuesView,
    ItemsView,
    Iterable,
    Iterator,
    KeysView
)

from app.objects.locks import LockedDict, LockedSet
from app.protocols.osu.http import HttpOsuClient
from app.common.cache import activity
from app.clients.base import Client
from app.clients.osu import OsuClient
from app.clients.irc import IrcClient
from chio import UserQuit

class Players(MutableMapping[int | str, Client]):
    def __init__(self) -> None:
        self.lock = RLock()

        # Lookup by id & name for osu! clients
        self.osu_id_mapping: LockedDict[int, OsuClient] = LockedDict()
        self.osu_name_mapping: LockedDict[str, OsuClient] = LockedDict()
        self.osu_safe_name_mapping: LockedDict[str, OsuClient] = LockedDict()

        # osu! specific
        self.osu_token_mapping: LockedDict[str, HttpOsuClient] = LockedDict()
        self.osu_tournament_clients: LockedSet[OsuClient] = LockedSet()
        self.osu_in_lobby: LockedSet[OsuClient] = LockedSet()

        # Every connected irc client (multiple sessions per-user allowed)
        self.irc_clients_set: LockedSet[IrcClient] = LockedSet()

        # Helper mappings for irc clients
        self.irc_id_mapping: LockedDict[int, IrcClient] = LockedDict()
        self.irc_name_mapping: LockedDict[str, IrcClient] = LockedDict()
        self.irc_safe_name_mapping: LockedDict[str, IrcClient] = LockedDict()

    @property
    def osu_clients(self) -> Iterable[OsuClient]:
        with self.lock:
            return self.osu_id_mapping.values_snapshot()

    @property
    def irc_clients(self) -> Iterable[IrcClient]:
        with self.lock:
            return self.irc_clients_set.snapshot_list()

    @property
    def http_osu_clients(self) -> Iterable[HttpOsuClient]:
        with self.lock:
            return self.osu_token_mapping.values_snapshot()

    @property
    def tcp_osu_clients(self) -> Iterable[OsuClient]:
        with self.lock:
            return [
                p for p in self.osu_id_mapping.values_snapshot()
                if p.protocol == 'tcp'
            ]

    @property
    def ws_osu_clients(self) -> Iterable[OsuClient]:
        with self.lock:
            return [
                p for p in self.osu_id_mapping.values_snapshot()
                if p.protocol == 'ws'
            ]

    def __repr__(self) -> str:
        return '<Players>'

    def __len__(self):
        with self.lock:
            return len(self.osu_id_mapping) + len(self.irc_id_mapping)

    def __setitem__(self, _, value: Client) -> None:
        """Set a player in the collection"""
        return self.add(value)

    def __getitem__(self, key: int | str) -> Client | None:  # type: ignore[override]
        """Get a player by id or name"""
        with self.lock:
            if isinstance(key, int):
                return self.by_id(key)
            elif isinstance(key, str):
                return self.by_name(key)
            return None

    def __delitem__(self, key: int | str) -> None:
        """Remove a player from the collection"""
        with self.lock:
            player = None

            if isinstance(key, int):
                player = self.by_id(key)
            elif isinstance(key, str):
                player = self.by_name(key)

            if player is not None:
                self.remove(player)

    def __iter__(self):
        with self.lock:
            snapshot_osu = self.osu_id_mapping.values_snapshot()
            snapshot_irc = self.irc_clients_set.snapshot_list()
        return chain(snapshot_osu, snapshot_irc)

    def __contains__(self, player: object) -> bool:
        """Check if a player is in the collection"""
        with self.lock:
            if isinstance(player, OsuClient):
                return player.id in self.osu_id_mapping
            elif isinstance(player, IrcClient):
                return player in self.irc_clients_set
            return False

    def get(self, value: int | str, default: Any = None) -> Client:
        """Get a player by id or name"""
        return self[value] or default

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
        with self.lock:
            self.osu_id_mapping[player.id] = player
            self.osu_name_mapping[player.name] = player
            self.osu_safe_name_mapping[player.safe_name] = player

            if player.protocol == 'http':
                assert isinstance(player, HttpOsuClient)
                self.osu_token_mapping[player.token] = player

            if player.is_tourney_client:
                self.osu_tournament_clients.add(player)

        self.send_player_to_osu(player)

    def remove_osu(self, player: OsuClient | HttpOsuClient) -> None:
        """Remove a player from the collection"""
        with self.lock:
            if player.in_lobby:
                self.remove_from_collection('osu_in_lobby', player)

            if player.is_tourney_client:
                self.remove_from_collection('osu_tournament_clients', player)

            self.remove_from_mapping('osu_id_mapping', player.id)
            self.remove_from_mapping('osu_name_mapping', player.name)
            self.remove_from_mapping('osu_safe_name_mapping', player.safe_name)

            if player.protocol == 'http':
                assert isinstance(player, HttpOsuClient)
                self.remove_from_mapping('osu_token_mapping', player.token)

    def add_irc(self, player: IrcClient) -> None:
        """Append a player to the collection"""
        with self.lock:
            self.irc_clients_set.add(player)
            self.irc_id_mapping[player.id] = player
            self.irc_name_mapping[player.name] = player
            self.irc_safe_name_mapping[player.safe_name] = player
        self.send_player_to_osu(player)

    def remove_irc(self, player: IrcClient) -> None:
        """Remove a player from the collection"""
        with self.lock:
            self.irc_clients_set.discard(player)
            self.remove_from_mapping('irc_id_mapping', player.id)
            self.remove_from_mapping('irc_name_mapping', player.name)
            self.remove_from_mapping('irc_safe_name_mapping', player.safe_name)

            # Check if other session remain & assign them to mapping
            other_irc_session = next((session for session in self.irc_clients if session.id == player.id), None)

            if not other_irc_session:
                # User has logged out of all irc sessions
                return

            # Set new "primary" irc session
            self.irc_id_mapping[player.id] = other_irc_session
            self.irc_name_mapping[player.name] = other_irc_session
            self.irc_safe_name_mapping[player.safe_name] = other_irc_session

    def remove_from_mapping(self, name: str, key: Any) -> None:
        with self.lock:
            try:
                del getattr(self, name)[key]
            except (KeyError, ValueError, AttributeError):
                pass

    def remove_from_collection(self, name: str, player: Client) -> None:
        """Remove a player from the collection"""
        with self.lock:
            try:
                getattr(self, name).remove(player)
            except (KeyError, ValueError, AttributeError):
                pass

    def by_id(self, id: int) -> Client | None:
        """Get a player by id"""
        with self.lock:
            return (
                self.osu_id_mapping.get(id, None) or
                self.irc_id_mapping.get(id, None)
            )

    def by_name(self, name: str) -> Client | None:
        """Get a player by name"""
        with self.lock:
            return (
                self.osu_name_mapping.get(name, None) or
                self.irc_name_mapping.get(name, None)
            )

    def by_name_safe(self, name: str) -> Client | None:
        """Get a player by a lowercased & underscored name"""
        safe_name = name.lower().replace(' ', '_')
        with self.lock:
            return (
                self.osu_safe_name_mapping.get(safe_name, None) or
                self.irc_safe_name_mapping.get(safe_name, None)
            )

    def by_name_or_id(self, input: str) -> Client | None:
        """Get a player by name or id"""
        if client := self.by_name_safe(input):
            return client

        id_string = input.removeprefix('#')

        if not id_string.isdigit():
            return None

        return self.by_id(int(id_string))

    def by_token(self, token: str) -> Client | None:
        """Get an osu! player by token"""
        with self.lock:
            return self.osu_token_mapping.get(token, None)

    def by_id_osu(self, id: int) -> OsuClient | None:
        """Get an osu! player by id"""
        with self.lock:
            return self.osu_id_mapping.get(id, None)

    def by_name_osu(self, name: str) -> OsuClient | None:
        """Get an osu! player by name"""
        with self.lock:
            return self.osu_name_mapping.get(name, None)

    def by_id_irc(self, id: int) -> IrcClient | None:
        """Get an irc player by id"""
        with self.lock:
            return self.irc_id_mapping.get(id, None)

    def by_id_irc_all(self, id: int) -> list[IrcClient]:
        """Get all connected IRC clients for this user id"""
        with self.lock:
            return [p for p in self.irc_clients_set if p.id == id]

    def by_name_irc(self, name: str) -> IrcClient | None:
        """Get an irc player by name"""
        with self.lock:
            return self.irc_name_mapping.get(name, None)

    def by_name_irc_all(self, name: str) -> list[IrcClient]:
        with self.lock:
            return [p for p in self.irc_clients_set if p.name == name]

    def tournament_clients(self, id: int) -> list[OsuClient]:
        """Get all connected tournament clients for a player"""
        with self.lock:
            return [
                p for p in self.osu_tournament_clients.snapshot_list()
                if p.id == id
            ]

    def clear_tournament_clients(self, id: int) -> None:
        """Clear all tourney clients by player id"""
        for p in self.tournament_clients(id):
            self.remove(p)

    def by_rank(self, rank: int, mode: int) -> list[Client]:
        """Get all players with the specified rank & mode"""
        with self.lock:
            return [
                p for p in self.osu_id_mapping.values_snapshot()
                if mode == p.status.mode
                and rank == p.rankings.get('global')
            ]

    def update_usercount(self) -> None:
        with self.lock:
            osu_count = len(self.osu_id_mapping)
            irc_count = len(self.irc_id_mapping)

        activity.set_all(
            osu_count,
            irc_count
        )

    def send_packet(self, packet, *args) -> None:
        for p in self.osu_clients:
            p.enqueue_packet(packet, *args)

    def send_player_to_osu(self, player: Client) -> None:
        for p in self.osu_clients:
            p.enqueue_player(player)

    def send_player_bundle(self, players: list[Client]) -> None:
        for p in self:
            p.enqueue_players(players)

    def send_presence(self, player: Client) -> None:
        for p in self.osu_clients:
            p.enqueue_presence(player)

    def send_stats(self, player: OsuClient) -> None:
        for p in self.osu_clients:
            if not p.io.requires_status_updates:
                # Client will request the stats
                # themselves, when pressing F9
                continue

            p.enqueue_stats(player)

    def send_stats_forced(self, player: OsuClient) -> None:
        for p in self.osu_clients:
            p.enqueue_stats(player)

    def apply_ranking(self, ranking: str = 'global') -> None:
        for p in self.osu_clients:
            p.apply_ranking(ranking)

    def send_announcement(self, message: str) -> None:
        for p in self:
            p.enqueue_announcement(message)

    def send_user_quit(self, quit: UserQuit) -> None:
        for p in self:
            p.enqueue_user_quit(quit)

    def send_channel(self, channel: "Channel") -> None:
        for p in self.osu_clients:
            if channel.can_read(p):
                p.enqueue_channel(channel)

from .channel import Channel

class Channels(MutableMapping[str, Channel]):
    def __init__(self) -> None:
        self.lock = RLock()
        self.map: dict[str, Channel] = {}
        self.public: LockedSet[Channel] = LockedSet()

    def __repr__(self) -> str:
        with self.lock:
            return f'<Channels ({len(self.map)})>'

    def __getitem__(self, key: str) -> Channel:
        with self.lock:
            return self.map[key]

    def __setitem__(self, key: str, channel: Channel) -> None:
        with self.lock:
            previous = self.map.get(key)

            if previous and previous.public:
                self.public.discard(previous)

            self.map[key] = channel

            if channel.public:
                self.public.add(channel)

    def __delitem__(self, key: str) -> None:
        with self.lock:
            channel = self.map.pop(key)

            if channel.public:
                self.public.discard(channel)

    def __iter__(self) -> Iterator[str]:
        with self.lock:
            return iter(list(self.map))

    def __len__(self) -> int:
        with self.lock:
            return len(self.map)

    def __contains__(self, key: object) -> bool:
        with self.lock:
            return key in self.map

    def values(self) -> ValuesView[Channel]:
        with self.lock:
            return dict(self.map).values()

    def items(self) -> ItemsView[str, Channel]:
        with self.lock:
            return dict(self.map).items()

    def keys(self) -> KeysView[str]:
        with self.lock:
            return dict(self.map).keys()

    def by_name(self, name: str) -> Channel | None:
        """Get a channel by name"""
        with self.lock:
            return self.map.get(name)

    def add(self, c: Channel) -> None:
        """Append a channel to the collection"""
        if not c:
            return

        with self.lock:
            self[c.name] = c

    def remove(self, c: Channel | None) -> None:
        """Remove a channel from the collection"""
        if not c:
            return

        users = c.users.snapshot_list()

        with self.lock:
            if c.name in self.map:
                del self[c.name]

        for p in users:
            p.enqueue_channel_revoked(c.display_name)
            p.channels.discard(c)

from .multiplayer import Match

class Matches:
    def __init__(self) -> None:
        self.lock = RLock()
        self.map: list[Match | None] = [None]

    def __repr__(self) -> str:
        with self.lock:
            return f'<Matches ({len(self.map)})>'

    def __iter__(self) -> Iterator[Match | None]:
        with self.lock:
            return iter(list(self.map))

    def __getitem__(self, index: int) -> Match | None:
        with self.lock:
            return self.map[index]

    def __len__(self) -> int:
        with self.lock:
            return len(self.map)

    @property
    def active(self) -> list[Match]:
        """All currently active matches"""
        with self.lock:
            return [m for m in self.map if m]

    @property
    def persistent(self) -> list[Match]:
        """All persistent matches"""
        with self.lock:
            return [m for m in self.map if m and m.persistent]

    def get_free(self) -> int | None:
        """Get a free match slot"""
        with self.lock:
            return self.find_available_index()

    def append(self, match: Match) -> bool:
        """Add match to collection and returns if successful"""
        with self.lock:
            free = self.find_available_index()
            match.id = free
            self.map[free] = match
            self.update_mp_count()
            return True

    def remove(self, match: Match) -> None:
        """Remove match from collection and remove all trailing, inactive matches from the collection"""
        with self.lock:
            for index, current in enumerate(self.map):
                if match == current:
                    self.map[index] = None
                    break

            while self.map and self.map[-1] is None:
                self.map.pop()

            self.update_mp_count()

    def get(self, match_id: int) -> Match | None:
        """Resolve a match by its internal ID"""
        with self.lock:
            try:
                return self.map[match_id]
            except IndexError:
                return None

    def exists(self, match_id: int) -> bool:
        """Check if a match exists"""
        with self.lock:
            return self.get(match_id) is not None

    def update_mp_count(self) -> None:
        with self.lock:
            active_count = sum(match is not None for match in self.map)
            activity.set_mp(active_count)

    def find_available_index(self) -> int:
        for index, match in enumerate(self.map):
            if match is None:
                return index

        self.map.append(None)
        return len(self.map) - 1
