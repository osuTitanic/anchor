
from app.common.objects import bMessage

from ..b323 import Reader as BaseReader

class Reader(BaseReader):
    def read_message(self) -> bMessage:
        sender = self.stream.string()
        content = self.stream.string()
        is_private = self.stream.bool()

        # Sender is the target username if is_private is True
        return bMessage(
            sender=sender if not is_private else '',
            target='#osu' if not is_private else sender,
            content=content
        )
