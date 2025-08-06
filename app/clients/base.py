
from chio.types import UserPresence, UserStats, UserStatus, Message, UserQuit
from chio.constants import Mode, Permissions
from typing import Iterable, List, Set
from datetime import datetime
from threading import Lock

from app.common.helpers import location, permissions, infringements as infringements_helper
from app.common.database.objects import DBUser, DBStats
from app.common.cache import leaderboards, status
from app.objects.client import ClientHash
from app.objects.multiplayer import Match
from app.objects.channel import Channel
from app.common.constants import level
from app.monitoring import RateLimiter
from app.common.database import (
    infringements,
    histories,
    groups,
    stats,
    users
)

import timeago
import logging
import config
import pytz
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
        self.port = port
        self.address = address
        self.logger = logging.getLogger(address)
        self.location: location.Geolocation | None = None

        self.stats = UserStats()
        self.status = UserStatus()
        self.presence = UserPresence()
        self.object: DBUser | None = None

        self.away_message: str | None = None
        self.away_senders: Set[int] = set()
        self.referee_matches: Set[Match] = set()
        self.channels: Set[Channel] = set()
        self.last_response = time.time()
        self.message_limiter = RateLimiter(60, 60)
        self.invite_limiter = RateLimiter(10, 20)
        self.action_lock = Lock()
        self.hidden = False
        self.rankings = {}

    @property
    def url(self) -> str:
        return f'http://osu.{config.DOMAIN_NAME}/u/{self.id}'

    @property
    def link(self) -> str:
        return f'[{self.url} {self.name}]'

    @property
    def last_response_delta(self) -> float:
        return time.time() - self.last_response

    @property
    def silenced(self) -> bool:
        if not self.object:
            return False

        if not self.object.silence_end:
            return False

        if self.remaining_silence < 0:
            # User is not silenced anymore
            self.unsilence(expired=True)
            return False

        return True

    @property
    def remaining_silence(self) -> int:
        if not self.object:
            return 0

        if not self.object.silence_end:
            return 0

        return round(
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
    def is_bot(self) -> bool:
        return (
            self.object.is_bot
            if self.object else False
        )

    @property
    def current_stats(self) -> DBStats | None:
        return (
            self.object.stats[self.status.mode.value]
            if self.object and self.object.stats else None
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
    def underscored_name(self) -> str:
        return self.name.replace(" ", "_")

    @property
    def safe_name(self) -> str:
        return self.underscored_name.lower()

    @property
    def is_irc(self) -> bool:
        return self.presence.is_irc

    @property
    def irc_formatted(self) -> str:
        return f"{self.underscored_name}!cho@{config.DOMAIN_NAME}"
    
    @property
    def irc_prefix(self) -> str:
        if self.is_staff:
            return "@"

        if self.silenced:
            return ""

        if self.is_irc:
            return "+"

        return ""

    @property
    def permissions(self) -> Permissions:
        return self.presence.permissions

    @property
    def avatar_filename(self) -> str:
        return f"{self.id}_{self.avatar_hash}.png"

    @property
    def avatar_hash(self) -> str:
        return (
            self.object.avatar_hash or "unknown"
            if self.object else "unknown"
        )

    @property
    def is_staff(self) -> bool:
        return any([self.object.is_admin, self.object.is_moderator])

    @property
    def is_verified(self) -> bool:
        return self.object.is_verified

    @property
    def has_preview_access(self) -> bool:
        return permissions.has_permission('clients.validation.bypass', self.id)

    @property
    def is_channel(self) -> bool:
        return False

    @property
    def is_tourney_client(self) -> bool:
        return False

    @property
    def friendonly_dms(self) -> bool:
        return False

    def __repr__(self) -> str:
        return f'<{self.protocol.capitalize()}Client "{self.name}" ({self.id})>'

    def __hash__(self) -> int:
        return hash((self.id, self.port))

    def __eq__(self, other) -> bool:
        if not isinstance(other, Client):
            return NotImplemented

        return (
            self.id == other.id and
            self.port == other.port
        )

    def reload(self, mode: int = 0) -> DBUser:
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
            self.update_object(mode)
            self.update_geolocation()
            self.update_status_cache()
            self.reload_rankings()
            self.reload_rank()
            bancho_permissions = groups.get_player_permissions(self.id, session)
            self.presence.permissions = Permissions(bancho_permissions)
            return self.object

    def reload_rank(self) -> None:
        """Check if redis rank desynced from database and update it, if needed"""
        cached_rank = leaderboards.global_rank(self.id, self.status.mode.value)
        self.rankings['global'] = cached_rank
        
        if not self.current_stats:
            return

        if cached_rank != self.current_stats.rank:
            self.current_stats.rank = cached_rank

            # Update rank in database
            stats.update(
                self.id,
                self.status.mode.value,
                {'rank': cached_rank}
            )

            if not config.FROZEN_RANK_UPDATES:
                # Update rank history
                histories.update_rank(
                    self.current_stats,
                    self.object.country
                )

    def reload_rankings(self) -> None:
        """Reload all non-global rankings from the cache"""
        self.rankings.update({
            'tscore': leaderboards.total_score_rank(self.id, self.status.mode.value),
            'rscore': leaderboards.score_rank(self.id, self.status.mode.value),
            'clears': leaderboards.clears_rank(self.id, self.status.mode.value),
            'ppv1': leaderboards.ppv1_rank(self.id, self.status.mode.value)
        })

    def apply_ranking(self, ranking: str = 'global') -> None:
        self.stats.rank = self.rankings.get(
            ranking,
            self.current_stats.rank
        )
        self.stats.pp = (
            round(self.current_stats.pp)
            if ranking != 'ppv1' else
            round(self.current_stats.ppv1)
        )

    def apply_default_ranking(self) -> None:
        self.stats.rank = self.current_stats.rank

    def update_object(self, mode: int = 0) -> None:
        """Apply the current database object to the client"""
        self.id = self.object.id
        self.name = self.object.name
        self.status.mode = Mode(mode)

        if not self.object.stats:
            return

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
        
    def update_geolocation(self) -> None:
        """Updates the player's geolocation"""
        self.location = location.fetch_geolocation(self.address)
        self.presence.country_index = self.location.country_index
        self.presence.longitude = self.location.longitude
        self.presence.latitude = self.location.latitude
        self.presence.timezone = int(
            datetime.now(
                pytz.timezone(self.location.timezone)
            ).utcoffset().total_seconds() / 60 / 60
        )

    def update_leaderboard_stats(self) -> None:
        """Updates the player's stats inside the redis leaderboard"""
        leaderboards.update(
            self.current_stats,
            self.object.country.lower()
        )

    def update_status_cache(self) -> None:
        """Updates the player's status inside the cache"""
        self.apply_ranking(
            ranking='global'
        )
        status.update(
            self.id,
            self.stats,
            self.status,
            hash=ClientHash.empty("b0").string,
            version=0
        )

    def update_activity(self) -> None:
        """Updates the player's latest activity inside the database"""
        users.update(
            user_id=self.id,
            updates={'latest_activity': datetime.now()}
        )

    def update_activity_later(self) -> None:
        """Schedules the player's last activity update"""
        app.session.tasks.do_later(
            self.update_activity,
            priority=5
        )
        
    def update_cache(self) -> None:
        self.update_leaderboard_stats()
        self.update_status_cache()
        self.reload_rankings()
        self.reload_rank()

    def close_connection(self, reason: str = "") -> None:
        """Closes the connection to the client"""
        if reason:
            self.logger.info(f'Closing connection -> <{self.address}> ({reason})')

    def silence(self, duration: int, reason: str | None = None) -> datetime:
        """Silences the user for a given duration"""
        if not self.object:
            return datetime.now()

        with self.action_lock:
            infringements_helper.silence_user(
                self.object,
                duration,
                reason
            )
            self.on_user_silenced()
            return self.object.silence_end
    
    def unsilence(self, expired: bool = False) -> None:
        """Unsilences the user"""
        if not self.object:
            return

        with self.action_lock:
            infringements_helper.unsilence_user(self.object, expired)
            self.on_user_unsilenced()

    def restrict(
        self,
        reason: str | None = None,
        until: datetime | None = None,
        autoban: bool = False
    ) -> None:
        """Restricts the user for a given duration"""
        if not self.object:
            return

        with self.action_lock:
            infringements_helper.restrict_user(
                self.object,
                reason=reason,
                until=until,
                autoban=autoban
            )
            self.on_user_restricted(reason, until)

    def unrestrict(self) -> None:
        """Unrestricts the user"""
        if not self.object:
            return

        with self.action_lock:
            infringements_helper.unrestrict_user(self.object)
            self.on_user_unrestricted()

    def on_user_silenced(self) -> None:
        self.reload()
        self.enqueue_infringement_length(self.remaining_silence)

    def on_user_unsilenced(self):
        self.reload()
        self.enqueue_infringement_length(-1)

    def on_user_restricted(
        self,
        reason: str | None = None,
        until: datetime | None = None,
        autoban: bool = False
    ) -> None:
        self.reload()
        until_text = ""

        if until:
            self.enqueue_infringement_length(
                round((until - datetime.now()).total_seconds())
            )
            until_text = (
                f'You will be able to play again {timeago.format(until)}.'
            )

        if reason:
            self.enqueue_announcement(
                f'You have been {"auto-" if autoban else ""}restricted for:'
                f'\n{reason}\n{until_text}'
            )

    def on_user_unrestricted(self) -> None:
        self.reload()
        self.enqueue_infringement_length(-1)

    def enqueue_player(self, player: "Client") -> None:
        ...

    def enqueue_players(self, players: Iterable["Client"]) -> None:
        ...

    def enqueue_presence(self, player: "Client") -> None:
        ...

    def enqueue_stats(self, player: "Client") -> None:
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

    def enqueue_away_message(self, target: "Client") -> None:
        ...

    def enqueue_announcement(self, message: str) -> None:
        ...

    def enqueue_infringement_length(self, duration_seconds: int) -> None:
        ...

    def enqueue_user_quit(self, quit: UserQuit) -> None:
        ...

    def enqueue_server_restart(self, retry_in_ms: int) -> None:
        ...
