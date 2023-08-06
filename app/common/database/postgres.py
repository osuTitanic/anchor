
from sqlalchemy.exc  import ResourceClosedError
from sqlalchemy      import create_engine
from sqlalchemy.orm  import Session

from typing import Generator, List
from threading import Timer

from .objects import Base

import logging
import random

class Postgres:
    def __init__(self, username: str, password: str, host: str, port: int) -> None:
        self.engine = create_engine(
            f'postgresql://{username}:{password}@{host}:{port}/{username}',
            max_overflow=30,
            pool_size=15,
            echo=False
        )

        self.pool: List[Session] = []
        self.pool.extend(
            [self.session] * 10
        )

        self.logger = logging.getLogger('postgres')
        Base.metadata.create_all(bind=self.engine)

    @property
    def session(self) -> Session:
        self.pool.append(
            session := Session(
                bind=self.engine,
                expire_on_commit=True
            )
        )
        return session

    @property
    def pool_session(self) -> Session:
        session = self.pool[random.randrange(0, 10)]

        if session.is_active:
            return session
        else:
            # Create new session
            self.pool.remove(session)
            self.session

        # I don't like this method...

        return session
