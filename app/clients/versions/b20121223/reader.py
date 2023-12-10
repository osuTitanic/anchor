
from ..b20130815 import Reader as BaseReader

from app.common.objects import bMessage

class Reader(BaseReader):
    def read_message(self) -> bMessage:
        return bMessage(
            sender=self.stream.string(),
            content=self.stream.string(),
            target=self.stream.string()
        )
