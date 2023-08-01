
from sqlalchemy.orm import sessionmaker, scoped_session, Session
from sqlalchemy.exc import ResourceClosedError
from sqlalchemy     import create_engine

from typing import Generator
from threading import Timer

from .objects import Base

import traceback
import logging
import config

class Postgres:
    def __init__(self, username: str, password: str, host: str, port: int) -> None:
        self.engine = create_engine(
            f'postgresql://{username}:{password}@{host}:{port}/{username}',
            max_overflow=30,
            pool_size=15,
            echo=False
        )

        self.logger = logging.getLogger('postgres')
        Base.metadata.create_all(bind=self.engine)

    @property
    def session(self) -> Session:
        return Session(self.engine, expire_on_commit=True)

    @property
    def temp_session(self) -> Session:
        session = Session(self.engine)

        Timer(
            interval=15,
            function=self.close_session,
            args=[session]
        ).start()

        return session

    def close_session(self, session: Session) -> None:
        try:
            session.close()
        except AttributeError:
            pass
        except ResourceClosedError:
            pass
        except Exception as exc:
            if config.DEBUG: traceback.print_exc()
            self.logger.error(
                f'Failed to close session: {exc}'
            )
