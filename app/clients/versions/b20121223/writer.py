
from app.common.objects import bMessage

from ..b20130815 import Writer as BaseWriter

class Writer(BaseWriter):
    def write_message(self, msg: bMessage):
        self.stream.string(msg.sender)
        self.stream.string(msg.content)
        self.stream.string(msg.target)
