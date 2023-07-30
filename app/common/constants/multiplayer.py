
from enum import IntEnum, IntFlag

class MatchType(IntEnum):
    Standard  = 0
    Powerplay = 1

class MatchScoringTypes(IntEnum):
    Score    = 0
    Accuracy = 1
    Combo    = 2

class MatchTeamTypes(IntEnum):
    HeadToHead = 0
    TagCoop    = 1
    TeamVs     = 2
    TagTeamVs  = 3

class SlotStatus(IntFlag):
    Open      = 1
    Locked    = 2
    NotReady  = 4
    Ready     = 8
    NoMap     = 16
    Playing   = 32
    Complete  = 64
    Quit      = 128

    HasPlayer = NotReady | Ready | NoMap | Playing | Complete

class SlotTeam(IntEnum):
    Neutral = 0
    Blue    = 1
    Red     = 2
