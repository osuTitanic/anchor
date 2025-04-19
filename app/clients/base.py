
from chio.types import UserPresence, UserStats, UserStatus, Message
from chio.constants import Mode, Permissions
from datetime import datetime, timedelta
from typing import Iterable, List

from app.common.database.objects import DBUser, DBStats
from app.common.cache import leaderboards, status
from app.objects.channel import Channel
from app.common.constants import level
from app.common import officer
from app.common.database import (
    infringements,
    histories,
    clients,
    scores,
    groups,
    stats,
    users
)

import timeago
import logging
import config
import time
import app

class Client:
    """
    This class represents a client connected to the server.
    It's meant to be a base for IRC and osu! clients, but can
    potentially be used for other protocols as well.
    """

    def __init__(self, address: str, port: int) -> None:
        self.id = 0
        self.name = ""
        self.protocol = "internal"
        self.address = address
        self.port = port
        self.presence = UserPresence()
        self.status = UserStatus()
        self.stats = UserStats()
        self.object: DBUser | None = None
        self.logger = logging.getLogger(address)
        self.last_response = time.time()
        self.last_minute_stamp = time.time()
        self.recent_message_count = 0
        self.permissions = Permissions.Regular
        self.groups = []

    @property
    def is_bot(self) -> bool:
        return (
            self.object.is_bot
            if self.object else False
        )

    @property
    def silenced(self) -> bool:
        if not self.object.silence_end:
            return False

        if self.remaining_silence < 0:
            # User is not silenced anymore
            self.unsilence()
            return False

        return True

    @property
    def remaining_silence(self) -> int:
        if not self.object.silence_end:
            return 0

        return (
            self.object.silence_end.timestamp() -
            datetime.now().timestamp()
        )

    @property
    def restricted(self) -> bool:
        if not self.object:
            return False

        if not self.object.restricted:
            return False

        if not (recent := infringements.fetch_recent_by_action(self.id, action=0)):
            self.unrestrict()
            return False

        if recent.is_permanent:
            return True
        
        if not recent.length:
            return True

        remaining = (recent.length - datetime.now()).total_seconds()

        if remaining <= 0:
            self.unrestrict()
            return False

        return True

    @property
    def link(self) -> str:
        return f'[http://osu.{config.DOMAIN_NAME}/u/{self.id} {self.name}]'

    @property
    def current_stats(self) -> DBStats | None:
        return (
            self.object.stats[self.status.mode.value]
            if self.object else None
        )

    @property
    def friends(self) -> List[int]:
        return [
            rel.target_id for rel in self.object.relationships
            if rel.status == 0
        ]

    @property
    def online_friends(self) -> Iterable["Client"]:
        for id in self.friends:
            if player := app.session.players.by_id(id):
                yield player

    @property
    def level(self) -> int:
        score = self.current_stats.tscore
        added_score = 0
        index = 0

        while added_score + level.NEXT_LEVEL[index] < score:
            added_score += level.NEXT_LEVEL[index]
            index += 1

        return round(
            (index + 1) + (score - added_score) / level.NEXT_LEVEL[index]
        )

    @property
    def avatar_filename(self) -> str:
        return f"{self.id}_000.png"

    @property
    def is_irc(self) -> bool:
        return False

    @property
    def is_supporter(self) -> bool:
        return 'Supporter' in self.groups

    @property
    def is_admin(self) -> bool:
        return 'Admins' in self.groups

    @property
    def is_dev(self) -> bool:
        return 'Developers' in self.groups

    @property
    def is_moderator(self) -> bool:
        return 'Global Moderator Team' in self.groups

    @property
    def has_preview_access(self) -> bool:
        return 'Preview' in self.groups

    @property
    def is_staff(self) -> bool:
        return any([self.is_admin, self.is_dev, self.is_moderator])

    @property
    def is_verified(self) -> bool:
        return self.object.is_verified

    def __repr__(self) -> str:
        return f'<Client "{self.name}" ({self.id})>'

    def __hash__(self) -> int:
        return self.id

    def __eq__(self, other) -> bool:
        if isinstance(other, Client):
            return (
                self.id == other.id and
                self.port == other.port
            )
        return False

    def reload(self) -> DBUser:
        """Re-fetch database information and apply it to the client"""
        with app.session.database.managed_session() as session:
            self.object = users.fetch_by_id(
                self.id,
                DBUser.target_relationships,
                DBUser.relationships,
                DBUser.groups,
                DBUser.stats,
                session=session
            )
            self.permissions = Permissions(groups.get_player_permissions(self.id, session))
            self.groups = [group.name for group in groups.fetch_user_groups(self.id, True, session)]
            self.update_object(self.object.preferred_mode)
            self.reload_rank()
            return self.object

    def reload_rank(self) -> int:
        """Check if redis rank desynced from database and update it, if needed"""
        cached_rank = leaderboards.global_rank(self.id, self.status.mode.value)

        if cached_rank != self.current_stats.rank:
            self.current_stats.rank = cached_rank

            # Update rank in database
            stats.update(
                self.id,
                self.status.mode.value,
                {'rank': cached_rank}
            )

            # Update rank history
            histories.update_rank(
                self.current_stats,
                self.object.country
            )

    def update_object(self, mode: int = 0) -> None:
        """Apply the current database object to the client"""
        self.id = self.object.id
        self.name = self.object.name
        self.status.mode = Mode(mode)

        # Ensure stats are sorted by mode
        self.object.stats.sort(key=lambda x: x.mode)

        # Use stats from current mode
        stats: DBStats = self.object.stats[mode]
        self.stats.rank = stats.rank
        self.stats.accuracy = stats.acc
        self.stats.rscore = stats.rscore
        self.stats.tscore = stats.tscore
        self.stats.playcount = stats.playcount
        self.stats.pp = round(stats.pp)

    def update_leaderboard_stats(self) -> None:
        """Updates the player's stats inside the redis leaderboard"""
        leaderboards.update(
            self.current_stats,
            self.object.country.lower()
        )

    def update_status_cache(self) -> None:
        """Updates the player's status inside the cache"""
        status.update(
            self.id,
            self.stats,
            self.status,
            self.client.hash.string,
            self.client.version.date
        )

    def update_activity(self) -> None:
        """Updates the player's latest activity inside the database"""
        users.update(
            user_id=self.id,
            updates={'latest_activity': datetime.now()}
        )

    def close_connection(self, reason: str = "") -> None:
        """Closes the connection to the client"""
        self.logger.info(
            f'Closing connection -> <{self.address}> ({reason})' if reason else
            f"<{self.address}> -> Connection done."
        )

    def silence(self, duration_sec: int, reason: str | None = None) -> None:
        if self.is_bot:
            return

        duration = timedelta(seconds=duration_sec)

        if not self.object.silence_end:
            self.object.silence_end = datetime.now() + duration
        else:
            # Append duration, if user has been silenced already
            self.object.silence_end += duration

        # Update database
        users.update(self.id, {'silence_end': self.object.silence_end})

        # Enqueue to client
        self.enqueue_infringement_length(duration_sec)

        # Add entry inside infringements table
        infringements.create(
            self.id,
            action=1,
            length=(datetime.now() + duration),
            description=reason
        )

        officer.call(
            f'{self.name} was silenced for {timeago.format(datetime.now() + duration)}. '
            f'Reason: "{reason}"'
        )

    def unsilence(self):
        self.object.silence_end = None
        self.enqueue_infringement_length(0)

        # Update database
        users.update(self.id, {'silence_end': None})

        infringement = infringements.fetch_recent_by_action(
            self.id,
            action=1
        )

        if infringement:
            infringements.delete_by_id(infringement.id)

    def restrict(
        self,
        reason: str | None = None,
        until: datetime | None = None,
        autoban: bool = False
    ) -> None:
        self.object.restricted = True

        # Update database
        users.update(self.id, {'restricted': True})

        # Remove permissions
        groups.delete_entry(self.id, 999)
        groups.delete_entry(self.id, 1000)

        # Update leaderboards
        leaderboards.remove(
            self.id,
            self.object.country
        )

        scores.hide_all(self.id)
        stats.update_all(self.id, {'rank': 0})

        if reason:
            self.enqueue_announcement(
                f'You have been restricted for:\n{reason}'
                f'\nYou will be able to play again {timeago.format(until)}.'
                if until else ''
            )

        if until:
            self.enqueue_infringement_length(
                round((until - datetime.now()).total_seconds())
            )

        # Update hardware
        clients.update_all(self.id, {'banned': True})

        # Add entry inside infringements table
        infringements.create(
            self.id,
            action=0,
            length=until,
            is_permanent=True
                    if not until
                    else False,
            description=f'{"Autoban: " if autoban else ""}{reason}'
        )

        officer.call(
            f'{self.name} was {"auto-" if autoban else ""}restricted. Reason: "{reason}"'
        )

    def unrestrict(self) -> None:
        users.update(self.id, {'restricted': False})
        self.object.restricted = False

        # Add to player & supporter group
        groups.create_entry(self.id, 999)
        groups.create_entry(self.id, 1000)

        # Update hardware
        clients.update_all(self.id, {'banned': False})

        # Update client
        self.enqueue_infringement_length(-1)

    def enqueue_player(self, player: "Client") -> None:
        ...

    def enqueue_players(self, players: Iterable["Client"]) -> None:
        ...

    def enqueue_channel(self, channel: Channel, autojoin: bool = False) -> None:
        ...

    def enqueue_channel_join_success(self, channel: str) -> None:
        ...

    def enqueue_channel_revoked(self, channel: str) -> None:
        ...

    def enqueue_message(self, message: str, sender: "Client", target: str) -> None:
        ...

    def enqueue_message_object(self, message: Message) -> None:
        ...

    def enqueue_announcement(self, message: str) -> None:
        ...

    def enqueue_infringement_length(self, duration_seconds: int) -> None:
        ...

    def enqueue_user_quit(self, player: "Client") -> None:
        ...

    def enqueue_server_restart(self, retry_in_ms: int) -> None:
        ...
