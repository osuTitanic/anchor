
from app.common.database import DBPlay
from app.session import database

def create(
    beatmap_file: str,
    beatmap_id: int,
    user_id: int,
    set_id: int,
    count: int = 1
) -> DBPlay:
    with database.session as session:
        session.add(
            p := DBPlay(
                user_id,
                beatmap_id,
                set_id,
                beatmap_file,
                count
            )
        )
        session.commit()

    return p

def update(
    beatmap_file: str,
    beatmap_id: int,
    user_id: int,
    set_id: int,
    count: int = 1
) -> None:
    with database.session as session:
        updated = session.query(DBPlay) \
            .filter(DBPlay.beatmap_id == beatmap_id) \
            .filter(DBPlay.user_id == user_id) \
            .update({
                'count': DBPlay.count + count
            })

        if not updated:
            create(
                beatmap_file,
                beatmap_id,
                user_id,
                set_id,
                count
            )

        session.commit()

# TODO: Create fetch queries
