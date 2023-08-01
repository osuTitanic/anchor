
from app.common.database import DBScore
from app.common.helpers import location
from datetime import datetime

import hashlib
import config
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
