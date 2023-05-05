
from sqlalchemy             import create_engine, func
from sqlalchemy.orm.session import sessionmaker

from .objects import Base

# TODO: Refactor code to allow multiple sessions and retrying transactions

class Postgres:
    def __init__(self, username: str, password: str, host: str, port: int) -> None:
        self.engine = create_engine(
            f'postgresql://{username}:{password}@{host}/{username}', 
            echo=False
        )

        Base.metadata.create_all(bind=self.engine)
        self.session = sessionmaker(bind=self.engine)()
