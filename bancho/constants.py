
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
    'BD': 'Bangladesh',
    'BE': 'Belgium',
    'BF': 'Burkina Faso',
    'BG': 'Bulgaria',
    'BA': 'Bosnia and Herzegovina',
    'BB': 'Barbados',
    'WF': 'Wallis and Futuna',
    'BL': 'Saint Barthelemy',
    'BM': 'Bermuda',
    'BN': 'Brunei',
    'BO': 'Bolivia',
    'BH': 'Bahrain',
    'BI': 'Burundi',
    'BJ': 'Benin',
    'BT': 'Bhutan',
    'JM': 'Jamaica',
    'BV': 'Bouvet Island',
    'BW': 'Botswana',
    'WS': 'Samoa',
    'BQ': 'Bonaire, Saint Eustatius and Saba',
    'BR': 'Brazil',
    'BS': 'Bahamas',
    'JE': 'Jersey',
    'BY': 'Belarus',
    'BZ': 'Belize',
    'RU': 'Russia',
    'RW': 'Rwanda',
    'RS': 'Serbia',
    'TL': 'East Timor',
    'RE': 'Reunion',
    'TM': 'Turkmenistan',
    'TJ': 'Tajikistan',
    'RO': 'Romania',
    'TK': 'Tokelau',
    'GW': 'Guinea-Bissau',
    'GU': 'Guam',
    'GT': 'Guatemala',
    'GS': 'South Georgia and the South Sandwich Islands',
    'GR': 'Greece',
    'GQ': 'Equatorial Guinea',
    'GP': 'Guadeloupe',
    'JP': 'Japan',
    'GY': 'Guyana',
    'GG': 'Guernsey',
    'GF': 'French Guiana',
    'GE': 'Georgia',
    'GD': 'Grenada',
    'GB': 'United Kingdom',
    'GA': 'Gabon',
    'SV': 'El Salvador',
    'GN': 'Guinea',
    'GM': 'Gambia',
    'GL': 'Greenland',
    'GI': 'Gibraltar',
    'GH': 'Ghana',
    'OM': 'Oman',
    'TN': 'Tunisia',
    'JO': 'Jordan',
    'HR': 'Croatia',
    'HT': 'Haiti',
    'HU': 'Hungary',
    'HK': 'Hong Kong',
    'HN': 'Honduras',
    'HM': 'Heard Island and McDonald Islands',
    'VE': 'Venezuela',
    'PR': 'Puerto Rico',
    'PS': 'Palestinian Territory',
    'PW': 'Palau',
    'PT': 'Portugal',
    'SJ': 'Svalbard and Jan Mayen',
    'PY': 'Paraguay',
    'IQ': 'Iraq',
    'PA': 'Panama',
    'PF': 'French Polynesia',
    'PG': 'Papua New Guinea',
    'PE': 'Peru',
    'PK': 'Pakistan',
    'PH': 'Philippines',
    'PN': 'Pitcairn',
    'PL': 'Poland',
    'PM': 'Saint Pierre and Miquelon',
    'ZM': 'Zambia',
    'EH': 'Western Sahara',
    'EE': 'Estonia',
    'EG': 'Egypt',
    'ZA': 'South Africa',
    'EC': 'Ecuador',
    'IT': 'Italy',
    'VN': 'Vietnam',
    'SB': 'Solomon Islands',
    'ET': 'Ethiopia',
    'SO': 'Somalia',
    'ZW': 'Zimbabwe',
    'SA': 'Saudi Arabia',
    'ES': 'Spain',
    'ER': 'Eritrea',
    'ME': 'Montenegro',
    'MD': 'Moldova',
    'MG': 'Madagascar',
    'MF': 'Saint Martin',
    'MA': 'Morocco',
    'MC': 'Monaco',
    'UZ': 'Uzbekistan',
    'MM': 'Myanmar',
    'ML': 'Mali',
    'MO': 'Macao',
    'MN': 'Mongolia',
    'MH': 'Marshall Islands',
    'MK': 'Macedonia',
    'MU': 'Mauritius',
    'MT': 'Malta',
    'MW': 'Malawi',
    'MV': 'Maldives',
    'MQ': 'Martinique',
    'MP': 'Northern Mariana Islands',
    'MS': 'Montserrat',
    'MR': 'Mauritania',
    'IM': 'Isle of Man',
    'UG': 'Uganda',
    'TZ': 'Tanzania',
    'MY': 'Malaysia',
    'MX': 'Mexico',
    'IL': 'Israel',
    'FR': 'France',
    'IO': 'British Indian Ocean Territory',
    'SH': 'Saint Helena',
    'FI': 'Finland',
    'FJ': 'Fiji',
    'FK': 'Falkland Islands',
    'FM': 'Micronesia',
    'FO': 'Faroe Islands',
    'NI': 'Nicaragua',
    'NL': 'Netherlands',
    'NO': 'Norway',
    'NA': 'Namibia',
    'VU': 'Vanuatu',
    'NC': 'New Caledonia',
    'NE': 'Niger',
    'NF': 'Norfolk Island',
    'NG': 'Nigeria',
    'NZ': 'New Zealand',
    'NP': 'Nepal',
    'NR': 'Nauru',
    'NU': 'Niue',
    'CK': 'Cook Islands',
    'XK': 'Kosovo',
    'CI': 'Ivory Coast',
    'CH': 'Switzerland',
    'CO': 'Colombia',
    'CN': 'China',
    'CM': 'Cameroon',
    'CL': 'Chile',
    'CC': 'Cocos Islands',
    'CA': 'Canada',
    'CG': 'Republic of the Congo',
    'CF': 'Central African Republic',
    'CD': 'Democratic Republic of the Congo',
    'CZ': 'Czech Republic',
    'CY': 'Cyprus',
    'CX': 'Christmas Island',
    'CR': 'Costa Rica',
    'CW': 'Curacao',
    'CV': 'Cape Verde',
    'CU': 'Cuba',
    'SZ': 'Swaziland',
    'SY': 'Syria',
    'SX': 'Sint Maarten',
    'KG': 'Kyrgyzstan',
    'KE': 'Kenya',
    'SS': 'South Sudan',
    'SR': 'Suriname',
    'KI': 'Kiribati',
    'KH': 'Cambodia',
    'KN': 'Saint Kitts and Nevis',
    'KM': 'Comoros',
    'ST': 'Sao Tome and Principe',
    'SK': 'Slovakia',
    'KR': 'South Korea',
    'SI': 'Slovenia',
    'KP': 'North Korea',
    'KW': 'Kuwait',
    'SN': 'Senegal',
    'SM': 'San Marino',
    'SL': 'Sierra Leone',
    'SC': 'Seychelles',
    'KZ': 'Kazakhstan',
    'KY': 'Cayman Islands',
    'SG': 'Singapore',
    'SE': 'Sweden',
    'SD': 'Sudan',
    'DO': 'Dominican Republic',
    'DM': 'Dominica',
    'DJ': 'Djibouti',
    'DK': 'Denmark',
    'VG': 'British Virgin Islands',
    'DE': 'Germany',
    'YE': 'Yemen',
    'DZ': 'Algeria',
    'US': 'United States',
    'UY': 'Uruguay',
    'YT': 'Mayotte',
    'UM': 'United States Minor Outlying Islands',
    'LB': 'Lebanon',
    'LC': 'Saint Lucia',
    'LA': 'Laos',
    'TV': 'Tuvalu',
    'TW': 'Taiwan',
    'TT': 'Trinidad and Tobago',
    'TR': 'Turkey',
    'LK': 'Sri Lanka',
    'LI': 'Liechtenstein',
    'LV': 'Latvia',
    'TO': 'Tonga',
    'LT': 'Lithuania',
    'LU': 'Luxembourg',
    'LR': 'Liberia',
    'LS': 'Lesotho',
    'TH': 'Thailand',
    'TF': 'French Southern Territories',
    'TG': 'Togo',
    'TD': 'Chad',
    'TC': 'Turks and Caicos Islands',
    'LY': 'Libya',
    'VA': 'Vatican',
    'VC': 'Saint Vincent and the Grenadines',
    'AE': 'United Arab Emirates',
    'AD': 'Andorra',
    'AG': 'Antigua and Barbuda',
    'AF': 'Afghanistan',
    'AI': 'Anguilla',
    'VI': 'U.S. Virgin Islands',
    'IS': 'Iceland',
    'IR': 'Iran',
    'AM': 'Armenia',
    'AL': 'Albania',
    'AO': 'Angola',
    'AQ': 'Antarctica',
    'AS': 'American Samoa',
    'AR': 'Argentina',
    'AU': 'Australia',
    'AT': 'Austria',
    'AW': 'Aruba',
    'IN': 'India',
    'AX': 'Aland Islands',
    'AZ': 'Azerbaijan',
    'IE': 'Ireland',
    'ID': 'Indonesia',
    'UA': 'Ukraine',
    'QA': 'Qatar',
    'MZ': 'Mozambique',
    'XX': 'Unknown country'
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
    LastMod        = 2097152
    FreeModAllowed = 1049659

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

class Rankings(Enum):
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
