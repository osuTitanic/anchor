
from .base import Client

# NOTE: This is a placeholder for now
class IrcClient(Client):
    @property
    def is_irc(self) -> bool:
        return True
