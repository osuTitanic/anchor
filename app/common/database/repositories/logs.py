
from app.common.database import DBLog
from app.session import database

def create(
    message: str,
    level: str,
    type: str
) -> DBLog:
    with database.session as session:
        session.add(
            log := DBLog(
                message,
                level,
                type
            )
        )
        session.commit()

    return log

# TODO: Create fetch queries
