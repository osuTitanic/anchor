
from app.session import database
from app.common.database import (
    DBReplayHistory,
    DBPlayHistory,
    DBRankHistory,
    DBStats
)

from datetime import datetime

def update_plays(
    user_id: int,
    mode: int
) -> None:
    time = datetime.now()

    with database.session as session:
        updated = session.query(DBPlayHistory) \
                .filter(DBPlayHistory.user_id == user_id) \
                .filter(DBPlayHistory.mode == mode) \
                .filter(DBPlayHistory.year == time.year) \
                .filter(DBPlayHistory.month == time.month) \
                .update({
                    'plays': DBPlayHistory.plays + 1
                })

        if not updated:
            session.add(
                DBPlayHistory(
                    user_id,
                    mode,
                    plays=1,
                    time=time
                )
            )

        session.commit()

def update_replay_views(
    user_id: int,
    mode: int
) -> None:
    time = datetime.now()

    with database.session as session:
        updated = session.query(DBReplayHistory) \
                    .filter(DBReplayHistory.user_id == user_id) \
                    .filter(DBReplayHistory.mode == mode) \
                    .filter(DBReplayHistory.year == time.year) \
                    .filter(DBReplayHistory.month == time.month) \
                    .update({
                        'replay_views': DBReplayHistory.replay_views + 1
                    })

        if not updated:
            session.add(
                DBReplayHistory(
                    user_id,
                    mode,
                    replay_views=1,
                    time=time
                )
            )

        session.commit()

def update_rank(
    stats: DBStats,
    country: str
) -> None:
    # TODO
    pass
