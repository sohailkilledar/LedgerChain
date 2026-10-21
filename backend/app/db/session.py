from collections.abc import Iterator
from dataclasses import dataclass
from typing import Annotated, Any

from fastapi import Depends, Request
from sqlalchemy import Engine, create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings


def create_db_engine(settings: Settings) -> Engine:
    """Create the SQLAlchemy engine. No connection is opened until first use."""
    url = make_url(settings.sqlalchemy_database_url)
    options: dict[str, Any] = {"echo": settings.database_echo, "pool_pre_ping": True}
    if url.get_backend_name() == "postgresql":
        options.update(
            pool_size=settings.database_pool_size,
            max_overflow=settings.database_max_overflow,
            pool_timeout=settings.database_pool_timeout,
            pool_recycle=settings.database_pool_recycle,
            connect_args={
                "connect_timeout": settings.database_connect_timeout,
                "application_name": settings.app_name,
            },
        )
    return create_engine(url, **options)


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


@dataclass(frozen=True)
class Database:
    engine: Engine
    session_factory: sessionmaker[Session]

    @classmethod
    def from_settings(cls, settings: Settings) -> "Database":
        engine = create_db_engine(settings)
        return cls(engine=engine, session_factory=create_session_factory(engine))

    @property
    def safe_url(self) -> str:
        return self.engine.url.render_as_string(hide_password=True)

    def dispose(self) -> None:
        self.engine.dispose()


def get_database(request: Request) -> Database:
    return request.app.state.database


def get_db_session(database: Annotated[Database, Depends(get_database)]) -> Iterator[Session]:
    """One session per request. Services own commits; anything uncommitted is rolled back."""
    session = database.session_factory()
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


DbSession = Annotated[Session, Depends(get_db_session)]
