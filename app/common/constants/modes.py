
from enum import IntEnum

class GameMode(IntEnum):
    Osu          = 0
    Taiko        = 1
    CatchTheBeat = 2
    OsuMania     = 3

    @property
    def formatted(self) -> str:
        return {
            GameMode.Osu: 'osu!',
            GameMode.Taiko: 'Taiko',
            GameMode.CatchTheBeat: 'CatchTheBeat',
            GameMode.OsuMania: 'osu!mania'
        }[self]
