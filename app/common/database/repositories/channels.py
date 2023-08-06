
from app.common.database.objects import DBChannel
from typing import List

import app

def create(
    name: str,
    topic: str,
    read_permissions: int,
    write_permissions: int
    # TODO: Channel Owner
) -> DBChannel:
    with app.session.database.session as session:
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
    return app.session.database.pool_session \
                      .query(DBChannel) \
                      .all()
