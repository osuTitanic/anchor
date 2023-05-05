
from dataclasses import dataclass, field
from typing      import List

from ..protocol import BanchoProtocol

from ..constants import (
    ClientStatus,
    Mode,
    Mod
)

@dataclass
class Status:
    action: ClientStatus = ClientStatus.Idle
    text: str = ""
    checksum: str = ""
    mods: List[Mod] = field(default_factory=list) # = []
    mode: Mode = Mode.Osu

    def __repr__(self) -> str:
        return f'<Status ({self.action})>'

class Player(BanchoProtocol):
    pass
