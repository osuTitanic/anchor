
from app.common.database import DBScore

import time
import app

def replays():
    """Job for automatically removing score replays if they have been beaten"""

    last_id = app.session.database.session.query(DBScore.id) \
                .order_by(DBScore.id.desc()) \
                .first()

    last_id = last_id[0] if last_id else 1

    while True:
        with app.session.database.managed_session() as session:
            results = session.query(DBScore) \
                        .filter(DBScore.id > last_id) \
                        .filter(DBScore.status == 2) \
                        .order_by(DBScore.id.asc()) \
                        .all()

            for score in results:
                app.session.storage.remove_replay(score.id)
                last_id = score.id

        for _ in range(30):
            if app.session.jobs._shutdown:
                exit()

            time.sleep(1)

