
from ...packets import PacketEnum
from enum import IntEnum

class RequestPacket(PacketEnum):
    CHANGE_STATUS         = 0
    SEND_MESSAGE          = 1
    EXIT                  = 2
    REQUEST_STATUS        = 3
    PONG                  = 4
    START_SPECTATING      = 17
    STOP_SPECTATING       = 18
    SEND_FRAMES           = 19
    ERROR_REPORT          = 21
    CANT_SPECTATE         = 22
    SEND_PRIVATE_MESSAGE  = 26
    PART_LOBBY            = 30
    JOIN_LOBBY            = 31
    CREATE_MATCH          = 32
    JOIN_MATCH            = 33
    LEAVE_MATCH           = 34
    MATCH_CHANGE_SLOT     = 39
    MATCH_READY           = 40
    MATCH_LOCK            = 41
    MATCH_CHANGE_SETTINGS = 42
    MATCH_START           = 45
    MATCH_SCORE_UPDATE    = 48
    MATCH_COMPLETE        = 50
    MATCH_CHANGE_BEATMAP  = 51
    MATCH_CHANGE_MODS     = 53
    MATCH_LOAD_COMPLETE   = 54
    MATCH_NO_BEATMAP      = 56
    MATCH_NOT_READY       = 57
    MATCH_FAILED          = 58

    # Not Supported:
    MATCH_HAS_BEATMAP     = 61
    MATCH_SKIP            = 62
    JOIN_CHANNEL          = 65
    BEATMAP_INFO          = 70
    MATCH_TRANSFER_HOST   = 72
    ADD_FRIEND            = 75
    REMOVE_FRIEND         = 76
    MATCH_CHANGE_TEAM     = 79
    LEAVE_CHANNEL         = 80
    RECEIVE_UPDATES       = 81
    SET_AWAY_MESSAGE      = 84
    IRC_ONLY              = 84
    STATS_REQUEST         = 85
    MATCH_INVITE          = 87
    MATCH_CHANGE_PASSWORD = 90
    TOURNAMENT_MATCH_INFO = 93
    PRESENCE_REQUEST      = 97
    PRESENCE_REQUEST_ALL  = 98
    CHANGE_FRIENDONLY_DMS = 99

class ResponsePacket(PacketEnum):
    LOGIN_REPLY                     = 5
    COMMAND_ERROR                   = 6 # Unused
    SEND_MESSAGE                    = 7
    PING                            = 8
    IRC_CHANGE_USERNAME             = 9
    IRC_QUIT                        = 10 # Unused (replaced by QuitState)
    IRC_JOIN                        = 11
    USER_STATS                      = 12
    USER_QUIT                       = 13
    SPECTATOR_JOINED                = 14
    SPECTATOR_LEFT                  = 15
    SPECTATE_FRAMES                 = 16
    VERSION_UPDATE                  = 20
    CANT_SPECTATE                   = 23
    GET_ATTENSION                   = 24
    ANNOUNCE                        = 25
    UPDATE_MATCH                    = 27
    NEW_MATCH                       = 28
    DISBAND_MATCH                   = 29
    LOBBY_JOIN                      = 35 # Only used in older clients
    LOBBY_PART                      = 36 # Only used in older clients
    MATCH_JOIN_SUCCESS              = 37
    MATCH_JOIN_FAIL                 = 38
    FELLOW_SPECTATOR_JOINED         = 43
    FELLOW_SPECTATOR_LEFT           = 44
    ALL_PLAYERS_LOADED              = 46 # Unused (Use 53 instead)
    MATCH_START                     = 47
    MATCH_SCORE_UPDATE              = 49
    MATCH_TRANSFER_HOST             = 52
    MATCH_ALL_PLAYERS_LOADED        = 55
    MATCH_PLAYER_FAILED             = 59
    MATCH_COMPLETE                  = 60

    # Not Supported:
    MATCH_SKIP                      = 63
    UNAUTHORIZED                    = 64 # Only used in older clients
    CHANNEL_JOIN_SUCCESS            = 66
    CHANNEL_AVAILABLE               = 67
    CHANNEL_REVOKED                 = 68
    CHANNEL_AVAILABLE_AUTOJOIN      = 69
    BEATMAP_INFO_REPLY              = 71
    LOGIN_PERMISSIONS               = 73
    FRIENDS_LIST                    = 74
    PROTOCOL_VERSION                = 77
    MENU_ICON                       = 78
    MONITOR                         = 82
    MATCH_PLAYER_SKIPPED            = 83
    USER_PRESENCE                   = 84
    IRC_ONLY                        = 85
    RESTART                         = 87
    INVITE                          = 89
    CHANNEL_INFO_COMPLETE           = 90
    MATCH_CHANGE_PASSWORD           = 92
    SILENCE_INFO                    = 93
    USER_SILENCED                   = 95
    USER_PRESENCE_SINGLE            = 96
    USER_PRESENCE_BUNDLE            = 97
    USER_DM_BLOCKED                 = 101
    TARGET_IS_SILENCED              = 102
    VERSION_UPDATE_FORCED           = 103
    SWITCH_SERVER                   = 104

class Completeness(IntEnum):
    StatusOnly = 0
    Statistics = 1
    Full       = 2
