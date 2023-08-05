
from app.common.database.objects import DBMessage

import app

def create(
    sender: str,
    target: str,
    message: str
) -> DBMessage:
    with app.session.database.session as session:
        session.add(
            msg := DBMessage(
                sender,
                target,
                message
            )
        )
        session.commit()

    return msg

# TODO: Create fetch queries
