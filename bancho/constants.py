
from enum import Enum

# These are the packet types, used in the latest clients.
# They will probably be different in some older clients.

class RequestPacket(Enum):
    CHANGE_STATUS         = 0
    SEND_MESSAGE          = 1
    EXIT                  = 2
    REQUEST_STATUS        = 3
    PONG                  = 4
    START_SPECTATING      = 16
    STOP_SPECTATING       = 17
    SEND_FRAMES           = 18
    ERROR_REPORT          = 20
    CANT_SPECTATE         = 21
    SEND_PRIVATE_MESSAGE  = 25
    PART_LOBBY            = 29
    JOIN_LOBBY            = 30
    CREATE_MATCH          = 31
    JOIN_MATCH            = 32
    LEAVE_MATCH           = 33
    MATCH_CHANGE_SLOT     = 38
    MATCH_READY           = 39
    MATCH_LOCK            = 40
    MATCH_CHANGE_SETTINGS = 41
    MATCH_START           = 44
    MATCH_SCORE_UPDATE    = 47
    MATCH_COMPLETE        = 49
    MATCH_CHANGE_MODS     = 51
    MATCH_LOAD_COMPLETE   = 52
    MATCH_NO_BEATMAP      = 54
    MATCH_NOT_READY       = 55
    MATCH_FAILED          = 56
    MATCH_HAS_BEATMAP     = 59
    MATCH_SKIP            = 60
    JOIN_CHANNEL          = 63
    BEATMAP_INFO          = 68
    MATCH_TRANSFER_HOST   = 70
    ADD_FRIEND            = 73
    REMOVE_FRIEND         = 74
    MATCH_CHANGE_TEAM     = 77
    LEAVE_CHANNEL         = 78
    RECEIVE_UPDATES       = 79
    SET_AWAY_MESSAGE      = 82
    IRC_ONLY              = 84
    STATS_REQUEST         = 85
    MATCH_INVITE          = 87
    MATCH_CHANGE_PASSWORD = 90
    TOURNAMENT_MATCH_INFO = 93
    PRESENCE_REQUEST      = 97
    PRESENCE_REQUEST_ALL  = 98
    CHANGE_FRIENDONLY_DMS = 99

class ResponsePacket(Enum):
	LOGIN_REPLY                     = 5
	COMMAND_ERROR                   = 6 # Unused
	SEND_MESSAGE                    = 7
	PING                            = 8
	IRC_CHANGE_USERNAME             = 9
	IRC_QUIT                        = 10
	USER_STATS                      = 11
	USER_QUIT                       = 12
	SPECTATOR_JOINED                = 13
	SPECTATOR_LEFT                  = 14
	SPECTATE_FRAMES                 = 15
	VERSION_UPDATE                  = 19
	CANT_SPECTATE                   = 22
	GET_ATTENSION                   = 23
	ANNOUNCE                        = 24
	UPDATE_MATCH                    = 26
	NEW_MATCH                       = 27
	DISBAND_MATCH                   = 28
	LOBBY_JOIN         				= 34 # Unused
	LOBBY_PART         				= 35 # Unused
	MATCH_JOIN_SUCCESS              = 36
	MATCH_JOIN_FAIL                 = 37
	FELLOW_SPECTATOR_JOINED         = 42
	FELLOW_SPECTATOR_LEFT           = 43
	ALL_PLAYERS_LOADED				= 45 # Unused (Use 53 instead)
	MATCH_START                     = 46
	MATCH_SCORE_UPDATE              = 48
	MATCH_TRANSFER_HOST             = 50
	MATCH_ALL_PLAYERS_LOADED        = 53
	MATCH_PLAYER_FAILED             = 57
	MATCH_COMPLETE                  = 58
	MATCH_SKIP                      = 61
	UNAUTHORIZED                    = 62
	CHANNEL_JOIN_SUCCESS            = 64
	CHANNEL_AVAILABLE               = 65
	CHANNEL_REVOKED                 = 66
	CHANNEL_AVAILABLE_AUTOJOIN      = 67
	BEATMAP_INFO_REPLY              = 69
	LOGIN_PERMISSIONS               = 71
	FRIENDS_LIST                    = 72
	PROTOCOL_VERSION		        = 75
	MENU_ICON		                = 76
	MONITOR                         = 80
	MATCH_PLAYER_SKIPPED            = 81
	USER_PRESENCE                   = 83
	IRC_ONLY              			= 84
	RESTART                  	    = 86
	INVITE                          = 88
	CHANNEL_INFO_COMPLETE           = 89
	MATCH_CHANGE_PASSWORD           = 91
	SILENCE_INFO                    = 92
	USER_SILENCED                   = 94
	USER_PRESENCE_SINGLE	        = 95
	USER_PRESENCE_BUNDLE            = 96
	USER_DM_BLOCKED                 = 100
	TARGET_IS_SILENCED              = 101
	VERSION_UPDATE_FORCED			= 102
	SWITCH_SERVER					= 103

WEB_RESPONSE = '''
<pre>
        _-_
       |(_)|
        |||
        |||
        |||

        |||
        |||
  ^     |^|     ^
< ^ >   <a href="https://pbs.twimg.com/media/Dqnn54dVYAAVuki.jpg"><+></a>   < ^ >
 | |    |||    | |
  \ \__/ | \__/ /
    \,__.|.__,/
        (_)

anchor: <a href="https://github.com/Lekuruu/titanic">https://github.com/Lekuruu/titanic</a>
</pre>
'''
