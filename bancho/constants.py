
from typing import List

from enum import Enum

# These are the packet types, used in the latest clients
# They will be different in some older clients

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
    LOBBY_JOIN                      = 34 # Unused
    LOBBY_PART                      = 35 # Unused
    MATCH_JOIN_SUCCESS              = 36
    MATCH_JOIN_FAIL                 = 37
    FELLOW_SPECTATOR_JOINED         = 42
    FELLOW_SPECTATOR_LEFT           = 43
    ALL_PLAYERS_LOADED              = 45 # Unused (Use 53 instead)
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
    PROTOCOL_VERSION                = 75
    MENU_ICON                       = 76
    MONITOR                         = 80
    MATCH_PLAYER_SKIPPED            = 81
    USER_PRESENCE                   = 83
    IRC_ONLY                        = 84
    RESTART                         = 86
    INVITE                          = 88
    CHANNEL_INFO_COMPLETE           = 89
    MATCH_CHANGE_PASSWORD           = 91
    SILENCE_INFO                    = 92
    USER_SILENCED                   = 94
    USER_PRESENCE_SINGLE            = 95
    USER_PRESENCE_BUNDLE            = 96
    USER_DM_BLOCKED                 = 100
    TARGET_IS_SILENCED              = 101
    VERSION_UPDATE_FORCED           = 102
    SWITCH_SERVER                   = 103

Countries = {
    "XX": "Unknown",
    "OC": "Oceania",
    "EU": "Europe",
    "AD": "Andorra",
    "AE": "UAE",
    "AF": "Afghanistan",
    "AG": "Antigua",
    "AI": "Anguilla",
    "AL": "Albania",
    "AM": "Armenia",
    "AN": "Netherlands Antilles",
    "AO": "Angola",
    "AQ": "Antarctica",
    "AR": "Argentina",
    "AS": "American Samoa",
    "AT": "Austria",
    "AU": "Australia",
    "AW": "Aruba",
    "AZ": "Azerbaijan",
    "BA": "Bosnia",
    "BB": "Barbados",
    "BD": "Bangladesh",
    "BE": "Belgium",
    "BF": "Burkina Faso",
    "BG": "Bulgaria",
    "BH": "Bahrain",
    "BI": "Burundi",
    "BJ": "Benin",
    "BM": "Bermuda",
    "BN": "Brunei Darussalam",
    "BO": "Bolivia",
    "BR": "Brazil",
    "BS": "Bahamas",
    "BT": "Bhutan",
    "BV": "Bouvet Island",
    "BW": "Botswana",
    "BY": "Belarus",
    "BZ": "Belize",
    "CA": "Canada",
    "CC": "Cocos Islands",
    "CD": "Congo",
    "CF": "Central African Republic",
    "CG": "Congo",
    "CH": "Switzerland",
    "CI": "Cote D'Ivoire",
    "CK": "Cook Islands",
    "CL": "Chile",
    "CM": "Cameroon",
    "CN": "China",
    "CO": "Colombia",
    "CR": "Costa Rica",
    "CU": "Cuba",
    "CV": "Cape Verde",
    "CX": "Christmas Island",
    "CY": "Cyprus",
    "CZ": "Czech Republic",
    "DE": "Germany",
    "DJ": "Djibouti",
    "DK": "Denmark",
    "DM": "Dominica",
    "DO": "Dominican Republic",
    "DZ": "Algeria",
    "EC": "Ecuador",
    "EE": "Estonia",
    "EG": "Egypt",
    "EH": "Western Sahara",
    "ER": "Eritrea",
    "ES": "Spain",
    "ET": "Ethiopia",
    "FI": "Finland",
    "FJ": "Fiji",
    "FK": "Falkland Islands",
    "FM": "Micronesia, Federated States of",
    "FO": "Faroe Islands",
    "FR": "France",
    "FX": "France, Metropolitan",
    "GA": "Gabon",
    "GB": "United Kingdom",
    "GD": "Grenada",
    "GE": "Georgia",
    "GF": "French Guiana",
    "GH": "Ghana",
    "GI": "Gibraltar",
    "GL": "Greenland",
    "GM": "Gambia",
    "GN": "Guinea",
    "GP": "Guadeloupe",
    "GP": "Guadeloupe",
    "GT": "Guatemala",
    "GU": "Guam",
    "GW": "Guinea-Bissau",
    "GY": "Guyana",
    "HK": "Hong Kong",
    "HM": "Heard Island",
    "HN": "Honduras",
    "HR": "Croatia",
    "HT": "Haiti",
    "HU": "Hungary",
    "ID": "Indonesia",
    "IE": "Ireland",
    "IL": "Israel",
    "IN": "India",
    "IO": "British Indian Ocean Territory",
    "IQ": "Iraq",
    "IR": "Iran, Islamic Republic of",
    "IS": "Iceland",
    "IT": "Italy",
    "JM": "Jamaica",
    "JO": "Jordan",
    "JP": "Japan",
    "KE": "Kenya",
    "KG": "Kyrgyzstan",
    "KH": "Cambodia",
    "KI": "Kiribati",
    "KM": "Comoros",
    "KN": "St. Kitts and Nevis",
    "KP": "Korea, Democratic People's Republic of",
    "KR": "Korea",
    "KW": "Kuwait",
    "KY": "Cayman Islands",
    "KZ": "Kazakhstan",
    "LA": "Lao",
    "LB": "Lebanon",
    "LC": "St. Lucia",
    "LI": "Liechtenstein",
    "LK": "Sri Lanka",
    "LR": "Liberia",
    "LS": "Lesotho",
    "LT": "Lithuania",
    "LU": "Luxembourg",
    "LV": "Latvia",
    "LY": "Libyan Arab Jamahiriya",
    "MA": "Morocco",
    "MC": "Monaco",
    "MD": "Moldova, Republic of",
    "MG": "Madagascar",
    "MH": "Marshall Islands",
    "MK": "Macedonia, the Former Yugoslav Republic of",
    "ML": "Mali",
    "MM": "Myanmar",
    "MN": "Mongolia",
    "MO": "Macau",
    "MP": "Northern Mariana Islands",
    "MQ": "Martinique",
    "MR": "Mauritania",
    "MS": "Montserrat",
    "MT": "Malta",
    "MU": "Mauritius",
    "MV": "Maldives",
    "MW": "Malawi",
    "MX": "Mexico",
    "MY": "Malaysia",
    "MZ": "Mozambique",
    "NA": "Namibia",
    "NC": "New Caledonia",
    "NE": "Niger",
    "NF": "Norfolk Island",
    "NG": "Nigeria",
    "NI": "Nicaragua",
    "NL": "Netherlands",
    "NO": "Norway",
    "NP": "Nepal",
    "NR": "Nauru",
    "NU": "Niue",
    "NZ": "New Zealand",
    "OM": "Oman",
    "PA": "Panama",
    "PE": "Peru",
    "PF": "French Polynesia",
    "PG": "Papua New Guinea",
    "PH": "Philippines",
    "PK": "Pakistan",
    "PL": "Poland",
    "PM": "St. Pierre",
    "PN": "Pitcairn",
    "PR": "Puerto Rico",
    "PS": "Palestinian Territory",
    "PT": "Portugal",
    "PW": "Palau",
    "PY": "Paraguay",
    "QA": "Qatar",
    "RE": "Reunion",
    "RO": "Romania",
    "RU": "Russian Federation",
    "RW": "Rwanda",
    "SA": "Saudi Arabia",
    "SB": "Solomon Islands",
    "SC": "Seychelles",
    "SD": "Sudan",
    "SE": "Sweden",
    "SG": "Singapore",
    "SH": "St. Helena",
    "SI": "Slovenia",
    "SJ": "Svalbard and Jan Mayen",
    "SK": "Slovakia",
    "SL": "Sierra Leone",
    "SM": "San Marino",
    "SN": "Senegal",
    "SO": "Somalia",
    "SR": "Suriname",
    "SS": "South Sudan",
    "ST": "Sao Tome and Principe",
    "SV": "El Salvador",
    "SX": "Sint Maarten (Dutch part)",
    "SY": "Syrian Arab Republic",
    "SZ": "Eswatini",
    "TC": "Turks and Caicos Islands",
    "TD": "Chad",
    "TF": "French Southern Territories",
    "TG": "Togo",
    "TH": "Thailand",
    "TJ": "Tajikistan",
    "TK": "Tokelau",
    "TL": "Timor-Leste",
    "TM": "Turkmenistan",
    "TN": "Tunisia",
    "TO": "Tonga",
    "TR": "Turkey",
    "TT": "Trinidad and Tobago",
    "TV": "Tuvalu",
    "TW": "Taiwan, Province of China",
    "TZ": "Tanzania, United Republic of",
    "UA": "Ukraine",
    "UG": "Uganda",
    "UM": "United States Minor Outlying Islands",
    "US": "United States",
    "UY": "Uruguay",
    "UZ": "Uzbekistan",
    "VA": "Holy See (Vatican City State)",
    "VC": "Saint Vincent and the Grenadines",
    "VE": "Venezuela, Bolivarian Republic of",
    "VG": "Virgin Islands, British",
    "VI": "Virgin Islands, U.S.",
    "VN": "Vietnam",
    "VU": "Vanuatu",
    "WF": "Wallis and Futuna",
    "WS": "Samoa",
    "YE": "Yemen",
    "YT": "Mayotte",
    "ZA": "South Africa",
    "ZM": "Zambia",
    "ZW": "Zimbabwe",
}

ToNextLevel = [
    30000,
    100000,
    210000,
    360000,
    550000,
    780000,
    1050000,
    1360000,
    1710000,
    2100000,
    2530000,
    3000000,
    3510000,
    4060000,
    4650000,
    5280000,
    5950000,
    6660000,
    7410000,
    8200000,
    9030000,
    9900000,
    10810000,
    11760000,
    12750000,
    13780000,
    14850000,
    15960000,
    17110000,
    18300000,
    19530000,
    20800000,
    22110000,
    23460000,
    24850000,
    26280000,
    27750000,
    29260000,
    30810000,
    32400000,
    34030000,
    35700000,
    37410000,
    39160000,
    40950000,
    42780000,
    44650000,
    46560000,
    48510000,
    50500000,
    52530000,
    54600000,
    56710000,
    58860000,
    61050000,
    63280000,
    65550000,
    67860000,
    70210001,
    72600001,
    75030002,
    77500003,
    80010006,
    82560010,
    85150019,
    87780034,
    90450061,
    93160110,
    95910198,
    98700357,
    101530643,
    104401157,
    107312082,
    110263748,
    113256747,
    116292144,
    119371859,
    122499346,
    125680824,
    128927482,
    132259468,
    135713043,
    139353477,
    143298259,
    147758866,
    153115959,
    160054726,
    169808506,
    184597311,
    208417160,
    248460887,
    317675597,
    439366075,
    655480935,
    1041527682,
    1733419828,
    2975801691,
    5209033044,
    9225761479,
    99999999999,
    99999999999,
    99999999999,
    99999999999,
    99999999999,
    99999999999,
    99999999999,
    99999999999,
    99999999999,
    99999999999
]

class ClientStatus(Enum):
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

class ClientMode(Enum):
    Menu                = 0
    Edit                = 1
    Play                = 2
    Quit                = 3
    SelectEdit          = 4
    SelectPlay          = 5
    Options             = 6
    OptionsSkin         = 7
    Rank                = 8
    Update              = 9
    Busy                = 10
    Unknown             = 11
    Lobby               = 12
    MatchSetup          = 13
    SelectMulti         = 14
    RankingVs           = 15
    UpdateSkin          = 16
    OnlineSelection     = 17
    OptionsOffsetWizard = 18
    Special             = 19
    RankingTagCoop      = 20
    RankingTeam         = 21
    BeatmapImport       = 22
    PackageUpdater      = 23
    Benchmark           = 24

class Mode(Enum):
    Osu      = 0
    Taiko    = 1
    Fruits   = 2
    OsuMania = 3

class Permissions(Enum):
    NoPermissions = 0
    Normal        = 1
    BAT           = 2
    Subscriber    = 4
    Friend        = 8
    Admin         = 16

    @classmethod
    def pack(cls, values) -> int:
        return sum([p.value for p in values])

    @classmethod
    def check_active(cls, values: int, permission: int) -> bool:
        return (values & permission) > Permissions.NoPermissions.value

    @classmethod
    def list(cls, values: int) -> List[Enum]:
        return [pm for pm in Permissions if cls.check_active(values, pm.value)]

class Mod(Enum):
    NoMod          = 0
    NoFail         = 1
    Easy           = 2
    Hidden         = 8
    HardRock       = 16
    SuddenDeath    = 32
    DoubleTime     = 64
    Relax          = 128
    HalfTime       = 256
    Nightcore      = 512
    Flashlight     = 1024
    Autoplay       = 2048
    SpunOut        = 4096
    Relax2         = 8192
    Perfect        = 16384
    Key4           = 32768
    Key5           = 65536
    Key6           = 131072
    Key7           = 262144
    Key8           = 524288
    keyMod         = 1015808
    FadeIn         = 1048576
    Random         = 2097152
    LastMod        = 4194304
    FreeModAllowed = 2077883

    @classmethod
    def pack(cls, values: List[Enum]):
        return sum([mod.value for mod in values])

    @classmethod
    def check_active(cls, values: int, mod: int):
        return (values & mod) > Mod.NoMod.value

    @classmethod
    def list(cls, values: int):
        return [mod for mod in Mod if cls.check_active(values, mod.value)]

class SubmissionStatus(Enum):
    Unknown = 0
    NotSubmitted = 1
    Pending = 2
    EditableCutoff = 3
    Ranked = 4
    Approved = 5

    @property
    def beatmap_info(self) -> int:
        return self.value - 3

    @classmethod
    def from_status(cls, value: int) -> Enum:
        return {
            -2: SubmissionStatus.Pending,         # Graveyard
            -1: SubmissionStatus.EditableCutoff,  # WIP
            0:  SubmissionStatus.Pending,         # Pending
            1:  SubmissionStatus.Ranked,          # Ranked
            2:  SubmissionStatus.Approved,        # Approved
            3:  SubmissionStatus.Ranked,          # Qualified
            4:  SubmissionStatus.Approved         # Loved
        }[value]
    
class Ranked(Enum):
    NotSubmitted = -1
    Pending  	 = 0
    Ranked	 	 = 1
    Approved 	 = 2

    @classmethod
    def from_status(cls, status: int):
        if status ==  1: return Ranked.NotSubmitted
        if status ==  2: return Ranked.Pending
        if status ==  4: return Ranked.Ranked
        if status ==  5: return Ranked.Approved
        return Ranked.Pending

class Grade(Enum):
    XH = 0
    SH = 1
    X = 2
    S = 3
    A = 4
    B = 5
    C = 6
    D = 7
    F = 8
    N = 9

class PresenceFilter(Enum):
    NoPlayers = 0
    All       = 1
    Friends   = 2

class MatchType(Enum):
    Standard  = 0
    Powerplay = 1

class MatchScoringTypes(Enum):
    Score    = 0
    Accuracy = 1
    Combo    = 2

class MatchTeamTypes(Enum):
    HeadToHead = 0
    TagCoop    = 1
    TeamVs     = 2
    TagTeamVs  = 3

class SlotStatus(Enum):
    Open      = 1
    Locked    = 2
    NotReady  = 4
    Ready     = 8
    NoMap     = 16
    Playing   = 32
    Complete  = 64
    Quit      = 128

    HasPlayer = NotReady | Ready | NoMap | Playing | Complete

class SlotTeam(Enum):
    Neutral = 0
    Blue    = 1
    Red     = 2

SPEED_MODS = [Mod.DoubleTime, Mod.HalfTime, Mod.Nightcore]

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
