
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

        # TODO: Add config for poolsize
        self.poolsize = 10

        self.pool: List[Session] = [
            self.session for _ in range(self.poolsize)
        ]

        self.logger = logging.getLogger('postgres')
        Base.metadata.create_all(bind=self.engine)

    @property
    def session(self) -> Session:
        return Session(
            bind=self.engine,
            expire_on_commit=True
        )

    @property
    def pool_session(self) -> Session:
        session = self.pool[random.randrange(0, len(self.pool))]

        if session.is_active:
            return session
        else:
            # Create new session
            self.pool.remove(session)
            self.pool.append(session := self.session)

        # TODO: Is there a built-in connection pool?

        return session
