
from enum import IntEnum, IntFlag

class LoginError(IntEnum):
    Authentication = -1
    UpdateNeeded   = -2
    Banned         = -3
    NotActivated   = -4
    ServerError    = -5
    TestBuild      = -6

class ClientStatus(IntEnum):
    Idle         = 0
    Afk          = 1
    Playing      = 2
    Editing      = 3
    Modding      = 4
    Multiplayer  = 5
    Watching     = 6
    Unknown      = 7
    Testing      = 8
    Submitting   = 9
    Paused       = 10
    Lobby        = 11
    Multiplaying = 12
    OsuDirect    = 13

class ReplayAction(IntEnum):
    Standard      = 0
    NewSong       = 1
    Skip          = 2
    Completion    = 3
    Fail          = 4
    Pause         = 5
    Unpause       = 6
    SongSelect    = 7
    WatchingOther = 8

class ButtonState(IntFlag):
    NoButton = 0
    Left1    = 1
    Right1   = 2
    Left2    = 4
    Right2   = 8

class QuitState(IntEnum):
    Gone         = 0
    OsuRemaining = 1
    IrcRemaining = 2

class AvatarExtension(IntEnum):
    NONE = 0
    PNG  = 1
    JPG  = 2

class PresenceFilter(IntEnum):
    NoPlayers = 0
    All       = 1
    Friends   = 2
