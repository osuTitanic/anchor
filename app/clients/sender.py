
from typing import Optional
from abc import ABC

from app.objects.player import Player

from app.common.constants import (
    Permissions
)

from app.common.objects import (
    UserPresence,
    UserStats
)

class BaseSender(ABC):
    def __init__(self, player: Player) -> None:
        self.player = player

    def send_login_reply(self, reply: int):
        ...

    def send_protocol_version(self, version: int):
        ...

    def send_ping(self):
        ...

    def send_announcement(self, message: str):
        ...

    def send_menu_icon(self, image: Optional[str], url: Optional[str]):
        ...

    def send_presence(self, presence: UserPresence):
        ...

    def send_stats(self, presence: UserStats):
        ...

    def send_permissions(self, permissions: Permissions):
        ...
