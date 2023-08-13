
from app.common.database import DBScore
from app.common.helpers import location
from datetime import datetime

import hashlib
import config
import struct
import socket
import app
import os

def setup():
    os.makedirs(config.DATA_PATH, exist_ok=True)

    if config.SKIP_IP_DATABASE:
        return

    if not os.path.isfile(f'{config.DATA_PATH}/geolite.mmdb'):
        location.download_database()

def get_ticks(dt) -> int:
    dt = dt.replace(tzinfo=None)
    return int((dt - datetime(1, 1, 1)).total_seconds() * 10000000)

def compute_score_checksum(score: DBScore) -> str:
    return hashlib.md5(
        '{}p{}o{}o{}t{}a{}r{}e{}y{}o{}u{}{}{}'.format(
            (score.n100 + score.n300),
            score.n50,
            score.nGeki,
            score.nKatu,
            score.nMiss,
            score.beatmap.md5,
            score.max_combo,
            score.perfect,
            score.user.name,
            score.total_score,
            score.grade,
            score.mods,
            (not score.failtime) # (passed)
        ).encode()
    ).hexdigest()

def is_local_ip(ip: str) -> bool:
    private = (
        [ 2130706432, 4278190080 ], # 127.0.0.0
        [ 3232235520, 4294901760 ], # 192.168.0.0
        [ 2886729728, 4293918720 ], # 172.16.0.0
        [ 167772160,  4278190080 ], # 10.0.0.0
    )

    f = struct.unpack(
        '!I',
        socket.inet_pton(
            socket.AF_INET,
            ip
        )
    )[0]

    for net in private:
        if (f & net[1]) == net[0]:
            return True

    return False

def load_geolocation_web(address: str) -> None:
    """Fetch geolocation data from web and store it to cache"""
    if not (result := location.fetch_web(address, is_local_ip(address))):
        return

    app.session.geolocation_cache[address] = result
