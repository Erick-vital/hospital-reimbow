from collections.abc import Iterator

from fastapi import Request
from sqlalchemy import MetaData, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from hospital.core.config import Settings


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention={
        "ix": "ix_%(table_name)s_%(column_0_name)s",
        "uq": "uq_%(table_name)s_%(column_0_name)s",
        "ck": "ck_%(table_name)s_%(constraint_name)s",
        "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
        "pk": "pk_%(table_name)s",
    })


class Database:
    def __init__(self, settings: Settings) -> None:
        self.engine = create_engine(
            settings.connection_url,
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=5,
            pool_timeout=2,
            connect_args={"connect_timeout": 2, "options": "-c statement_timeout=2000 -c timezone=UTC"},
            hide_parameters=True,
            echo=False,
        )
        self.sessions = sessionmaker(self.engine, expire_on_commit=False)

    def dispose(self) -> None:
        self.engine.dispose()


def get_session(request: Request) -> Iterator[Session]:
    # El servicio delimita begin/commit; cerrar revierte cualquier transacción pendiente.
    with request.app.state.database.sessions() as session:
        yield session
