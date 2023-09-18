
from app.common.constants import (
    ClientStatus,
    GameMode,
    Mods
)

from app.common.objects import (
    bStatusUpdate
)

from ..b399 import Reader as BaseReader

class Reader(BaseReader):
    def read_status(self) -> bStatusUpdate:
        action = ClientStatus(self.stream.u8())

        if action.value > 9:
            # Workaround because of different enum values
            action = ClientStatus(action - 1)

        if action == ClientStatus.Unknown:
            return bStatusUpdate(action)

        s = bStatusUpdate(
            action,
            text=self.stream.string(),
            beatmap_checksum=self.stream.string(),
            mods=Mods(self.stream.u16())
        )

        if action == ClientStatus.Idle and s.beatmap_checksum:
            # Client is playing, but status didn't update???
            s.action = ClientStatus.Playing

        return s
