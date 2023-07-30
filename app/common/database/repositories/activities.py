
from app.common.database import DBActivity
from app.session import database

def create(
    user_id: int,
    mode: int,
    text: str,
    args: str,
    links: str
) -> DBActivity:
    with database.session as session:
        session.add(
            ac := DBActivity(
                user_id,
                mode,
                text,
                args,
                links
            )
        )
        session.commit()

    return ac

# TODO: fetch_many
