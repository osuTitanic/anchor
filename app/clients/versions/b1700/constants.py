
from .. import PacketEnum
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
  # MATCH_CHANGE_BEATMAP  = 51
    MATCH_CHANGE_MODS     = 52
    MATCH_LOAD_COMPLETE   = 53
    MATCH_NO_BEATMAP      = 55
    MATCH_NOT_READY       = 56
    MATCH_FAILED          = 57
    MATCH_HAS_BEATMAP     = 60
    MATCH_SKIP            = 61
    JOIN_CHANNEL          = 64
    BEATMAP_INFO          = 69
    MATCH_TRANSFER_HOST   = 71
    ADD_FRIEND            = 74
    REMOVE_FRIEND         = 75
    MATCH_CHANGE_TEAM     = 78
    LEAVE_CHANNEL         = 79
    RECEIVE_UPDATES       = 80
    SET_AWAY_MESSAGE      = 83

    # Not Supported:
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
    ALL_PLAYERS_LOADED              = 46 # Unused (Use 54 instead)
    MATCH_START                     = 47
    MATCH_SCORE_UPDATE              = 49
    MATCH_TRANSFER_HOST             = 51
    MATCH_ALL_PLAYERS_LOADED        = 54
    MATCH_PLAYER_FAILED             = 58
    MATCH_COMPLETE                  = 59
    MATCH_SKIP                      = 62
    UNAUTHORIZED                    = 63 # Only used in older clients
    CHANNEL_JOIN_SUCCESS            = 65
    CHANNEL_AVAILABLE               = 66
    CHANNEL_REVOKED                 = 67
    CHANNEL_AVAILABLE_AUTOJOIN      = 68
    BEATMAP_INFO_REPLY              = 70
    LOGIN_PERMISSIONS               = 72
    FRIENDS_LIST                    = 73
    PROTOCOL_VERSION                = 76
    MENU_ICON                       = 77
    MONITOR                         = 81
    MATCH_PLAYER_SKIPPED            = 82

    # Not Supported:
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
