
from app.common.database import DBChannel
from app.session import database

from typing import List

def create(
    name: str,
    topic: str,
    read_permissions: int,
    write_permissions: int
    # TODO: Channel Owner
) -> DBChannel:
    with database.session as session:
        session.add(
            chan := DBChannel(
                name,
                topic,
                read_permissions,
                write_permissions
            )
        )
        session.commit()

    return chan

def fetch_all() -> List[DBChannel]:
    return database.temp_session.query(DBChannel) \
                                .all()
