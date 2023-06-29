
from ..objects.player import Player
from .objects import DBStats
from ..constants import Mod

from typing import Tuple, List
from redis import Redis

import config
import bancho

class UserCache:
    """
    This class will store user stats inside the cache, so that data can be shared between applications.
    It will also manage leaderboards for score, country and performance.
    """

    def __init__(self) -> None:
        self.redis = Redis(
            config.REDIS_HOST,
            config.REDIS_PORT
        )

    def user_exists(self, id: int) -> bool:
        return bool(self.redis.exists(f'users:{id}'))

    def remove_user(self, id: int) -> bool:
        return bool(self.redis.delete(f'users:{id}'))

    def get_user(self, id: int) -> dict:
        return self.redis.hgetall(f'users:{id}')

    def update_user(self, player: Player) -> str:
        return self.redis.hmset(
            name=f'users:{player.id}',
            mapping={
                'id': player.id,
                'name': player.name,
                'login_time': player.login_time.timestamp(),
                'match': player.match.id if player.match else -1,
                'version': player.client.version.string,
                'version_hash': player.client.hash.md5,
                'client_hash': player.client.hash.string,
                'country': player.object.country,
                'action': player.status.action.value,
                'text': player.status.text,
                'checksum': player.status.checksum,
                'mode': player.status.mode.value,
                'mods': Mod.pack(player.status.mods),
                'beatmap': player.status.beatmap
            }
        )

    def update_leaderboards(self, stats: DBStats):
        if stats.pp > 0:
            self.redis.zadd(
                f'bancho:performance:{stats.mode}',
                {stats.user_id: stats.pp}
            )

            self.redis.zadd(
                f'bancho:performance:{stats.mode}:{stats.user.country}',
                {stats.user_id: stats.pp}
            )

            self.redis.zadd(
                f'bancho:rscore:{stats.mode}',
                {stats.user_id: stats.rscore}
            )

    def remove_from_leaderboards(self, user_id: int, country: str):
        for mode in range(4):
            self.redis.zrem(
                f'bancho:performance:{mode}',
                user_id
            )

            self.redis.zrem(
                f'bancho:performance:{mode}:{country}',
                user_id
            )

            self.redis.zrem(
                f'bancho:rscore:{mode}',
                user_id
            )

    def get_global_rank(self, user_id: int, mode: int) -> int:
        rank = self.redis.zrevrank(
            f'bancho:performance:{mode}',
            user_id
        )
        return (rank + 1 if rank is not None else 0)

    def get_country_rank(self, user_id: int, mode: int, country: str) -> int:
        rank = self.redis.zrevrank(
            f'bancho:performance:{mode}:{country}',
            user_id
        )
        return (rank + 1 if rank is not None else 0)

    def get_score_rank(self, user_id: int, mode: int) -> int:
        rank = self.redis.zrevrank(
            f'bancho:rscore:{mode}',
            user_id
        )
        return (rank + 1 if rank is not None else 0)

    def get_performance(self, user_id: int, mode: int) -> int:
        pp = self.redis.zscore(
            f'bancho:performace:{mode}',
            user_id
        )
        return pp if pp is not None else 0

    def get_score(self, user_id: int, mode: int) -> int:
        pp = self.redis.zscore(
            f'bancho:rscore:{mode}',
            user_id
        )
        return pp if pp is not None else 0

    def get_leaderboard(self, mode, offset, range=50, type='performance', country=None) -> List[Tuple[int, float]]:
        players = self.redis.zrevrange(
            f'bancho:{type}:{mode}{f":{country}" if country else ""}',
            offset,
            range,
            withscores=True
        )

        return [(int(id), score) for id, score in players]
