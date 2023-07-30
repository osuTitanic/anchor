
from dataclasses import dataclass

from ..constants import (
    ClientStatus,
    Permissions,
    QuitState,
    GameMode,
    Mods
)

@dataclass
class StatusUpdate:
    status: ClientStatus
    text: str
    mods: Mods
    mode: GameMode
    beatmap_checksum: str
    beatmap_id: int

@dataclass
class UserQuit:
    user_id: int
    quit_state: QuitState

@dataclass
class UserPresence:
    user_id: int
    is_irc: bool
    username: str
    timezone: int
    country_code: int
    permissions: Permissions
    mode: GameMode
    longitude: float
    latitude: float
    rank: int

@dataclass
class UserStats:
    user_id: int
    status: StatusUpdate
    rscore: int
    tscore: int
    accuracy: float
    playcount: int
    rank: int
    pp: int
