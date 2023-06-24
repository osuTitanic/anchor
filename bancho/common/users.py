
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
        self.cache = Redis(
            config.REDIS_HOST,
            config.REDIS_PORT
        )

    def user_exists(self, id: int) -> bool:
        return bool(self.cache.exists(f'users:{id}'))

    def remove_user(self, id: int) -> bool:
        return bool(self.cache.delete(f'users:{id}'))

    def get_user(self, id: int) -> dict:
        return self.cache.hgetall(f'users:{id}')

    def update_user(self, player: Player) -> str:
        return self.cache.hmset(
            name=f'users:{player.id}',
            mapping={
                'id': player.id,
                'name': player.name,
                'login_time': player.login_time.timestamp(),
                'match': player.match.id if player.match else -1,
                'version': player.client.version.string,
                'version_hash': player.client.hash,
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
            self.cache.zadd(
                f'bancho:performance:{stats.mode}',
                {stats.user_id: stats.pp}
            )

            self.cache.zadd(
                f'bancho:performance:{stats.mode}:{stats.user.country}',
                {stats.user_id: stats.pp}
            )

            self.cache.zadd(
                f'bancho:rscore:{stats.mode}',
                {stats.user_id: stats.rscore}
            )

    def remove_from_leaderboards(self, user_id: int, country: str):
        for mode in range(4):
            self.cache.zrem(
                f'bancho:performance:{mode}',
                user_id
            )

            self.cache.zrem(
                f'bancho:performance:{mode}:{country}',
                user_id
            )

            self.cache.zrem(
                f'bancho:rscore:{mode}',
                user_id
            )

    def get_global_rank(self, user_id: int, mode: int) -> int:
        rank = self.cache.zrevrank(
            f'bancho:performance:{mode}',
            user_id
        )
        return (rank + 1 if rank is not None else 0)

    def get_country_rank(self, user_id: int, mode: int, country: str) -> int:
        rank = self.cache.zrevrank(
            f'bancho:performance:{mode}:{country}',
            user_id
        )
        return (rank + 1 if rank is not None else 0)

    def get_score_rank(self, user_id: int, mode: int) -> int:
        rank = self.cache.zrevrank(
            f'bancho:rscore:{mode}',
            user_id
        )
        return (rank + 1 if rank is not None else 0)

    def get_performance(self, user_id: int, mode: int) -> int:
        pp = self.cache.zscore(
            f'bancho:performace:{mode}',
            user_id
        )
        return pp if pp is not None else 0

    def get_score(self, user_id: int, mode: int) -> int:
        pp = self.cache.zscore(
            f'bancho:rscore:{mode}',
            user_id
        )
        return pp if pp is not None else 0

    def get_leaderboard(self, mode, offset, range=50, type='performance', country=None) -> List[Tuple[int, float]]:
        players = self.cache.zrevrange(
            f'bancho:{type}:{mode}{f":{country}" if country else ""}',
            offset,
            range,
            withscores=True
        )

        return [(int(id), score) for id, score in players]

    def get_above(self, user_id, mode, type='performance'):
        """Get information about player ranked above another player"""

        position = self.cache.zrevrank(
            f'bancho:{type}:{mode}', 
            user_id
        )
        
        score = self.cache.zscore(
            f'bancho:{type}:{mode}',
            user_id
        )

        if position is None or position <= 0:
            return {
                'difference': 0,
                'next_user': ''
            }

        above = self.cache.zrevrange(
            f'bancho:{type}:{mode}',
            position-1,
            position,
            withscores=True
        )[0]
        
        return {
            'difference': int(above[1]) - int(score),
            'next_user': bancho.services.database.user_by_id(int(above[0].decode())).name
        }
