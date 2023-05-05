
from abc import ABC

class BaseHandler(ABC):

    """
    This class will be used as a base for different client handlers.
    """

    def __init__(self, player) -> None:
        from bancho.objects.player import Player

        self.player: Player = player
        self.client = self.player.client

    def login_success(self):
        ...
