
from app.common.objects import bStatusUpdate
from app.common.constants import (
    ClientStatus,
    GameMode,
    Mods
)

from dataclasses import dataclass

@dataclass(slots=True)
class Status:
    action: ClientStatus = ClientStatus.Idle
    text: str = ""
    checksum: str = ""
    mods: Mods = Mods.NoMod
    mode: GameMode = GameMode.Osu
    beatmap: int = -1

    def __repr__(self) -> str:
        return (
            f"<[{self.action.name}] "
            f"mode='{self.mode.name}' "
            f"mods={self.mods} "
            f"text='{self.text}' "
            f"md5='{self.checksum}' "
            f"beatmap={self.beatmap}>"
        )

    @property
    def bancho_status(self) -> bStatusUpdate:
        return bStatusUpdate(
            self.action,
            self.text,
            self.mods,
            self.mode,
            self.checksum,
            self.beatmap
        )
