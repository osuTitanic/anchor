
from app.common.database import DBScore
import app

def replays():
    """Job for automatically removing score replays if they have been beaten"""
    # TODO: Move this somewhere else?

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

        app.session.jobs.sleep(30)
