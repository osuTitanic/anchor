
from app.common.constants import AvatarExtension
from app.common.objects import bUserPresence

from ..b20130329 import Writer as BaseWriter

class Writer(BaseWriter):
    def write_presence(self, presence: bUserPresence):
        self.stream.s32(presence.user_id)
        self.stream.string(presence.username)
        self.stream.u8(AvatarExtension.PNG.value) # NOTE: Client will not send avatar request when NONE
        self.stream.u8(presence.timezone + 24)
        self.stream.u8(presence.country_code)
        self.stream.string(presence.city)
        self.stream.u8(presence.permissions.value)
        self.stream.float(presence.longitude)
        self.stream.float(presence.latitude)
        self.stream.s32(presence.rank)
        self.stream.u8(presence.mode.value)
