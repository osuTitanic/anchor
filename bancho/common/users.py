
from ..objects.player import Player
from .objects import DBStats
from ..constants import Mod

from redis import Redis

import config

class UserCache:
    """This class will store user stats inside the cache, so that data can be shared between applications."""

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
                'country': player.object.country,
                'action': player.status.action.value,
                'text': player.status.text,
                'checksum': player.status.checksum,
                'mode': player.status.mode.value,
                'mods': Mod.pack(player.status.mods),
                'beatmap': player.status.beatmap
            }
        )
