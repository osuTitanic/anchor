

from enum import IntFlag

class Mods(IntFlag):
    NoMod                  = 0
    NoFail                 = 1 << 0
    Easy                   = 1 << 1
    NoVideo                = 1 << 2
    Hidden                 = 1 << 3
    HardRock               = 1 << 4
    SuddenDeath            = 1 << 5
    DoubleTime             = 1 << 6
    Relax                  = 1 << 7
    HalfTime               = 1 << 8
    Nightcore              = 1 << 9
    Flashlight             = 1 << 10
    Autoplay               = 1 << 11
    SpunOut                = 1 << 12
    Autopilot              = 1 << 13
    Perfect                = 1 << 14
    Key4                   = 1 << 15
    Key5                   = 1 << 16
    Key6                   = 1 << 17
    Key7                   = 1 << 18
    Key8                   = 1 << 19
    FadeIn                 = 1 << 20
    Random                 = 1 << 21
    LastMod                = 1 << 29

    KeyMod = Key4 | Key5 | Key6 | Key7 | Key8
    SpeedMods = DoubleTime | HalfTime| Nightcore
    FreeModAllowed = NoFail | Easy | Hidden | HardRock | SuddenDeath | Flashlight | FadeIn | Relax | Autopilot | SpunOut | KeyMod
