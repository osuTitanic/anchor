
from app.common.constants import (
    ClientStatus,
    GameMode,
    Mods
)

from dataclasses import dataclass, field
from typing import List

@dataclass
class Status:
    action: ClientStatus = ClientStatus.Idle
    text: str = ""
    checksum: str = ""
    mods: Mods = Mods.NoMod
    mode: GameMode = GameMode.Osu
    beatmap: int = -1

    def __repr__(self) -> str:
        return f"<[{self.action.name}] mode='{self.mode.name}' mods={self.mods} text='{self.text}' md5='{self.checksum}' beatmap={self.beatmap}>"
