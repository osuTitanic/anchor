
from enum import IntFlag

class Permissions(IntFlag):
    NoPermissions = 0
    Normal        = 1
    BAT           = 2
    Supporter     = 4
    Friend        = 8
    Admin         = 16
