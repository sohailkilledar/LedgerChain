from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Integer, String, create_engine, select, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.pool import StaticPool

from app.core.config import Settings
from app.db.base import Base
from app.db.readiness import DatabaseStatus, check_database
from app.db.session import Database, DbSession, create_db_engine, create_session_factory
from app.main import create_app
from app.repositories.base import Repository


class DatabaseRecord(Base):
    __tablename__ = "database_test_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(80), nullable=False)


class DatabaseRecordRepository(Repository[DatabaseRecord]):
    model = DatabaseRecord


@pytest.fixture
def sqlite_engine() -> Iterator[Engine]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    try:
        yield engine
    finally:
        engine.dispose()


@pytest.fixture
def database(sqlite_engine: Engine) -> Database:
    return Database(
        engine=sqlite_engine,
        session_factory=create_session_factory(sqlite_engine),
    )


def test_postgres_urls_use_psycopg_3_driver() -> None:
    settings = Settings(_env_file=None, database_url="postgresql://user:password@localhost/ledgerchain")

    assert settings.sqlalchemy_database_url == "postgresql+psycopg://user:password@localhost/ledgerchain"


def test_database_engine_creation_does_not_open_connections() -> None:
    engine = create_db_engine(Settings(_env_file=None))
    try:
        assert engine.url.drivername == "postgresql+psycopg"
    finally:
        engine.dispose()


def test_repository_performs_crud_and_leaves_commit_to_service(database: Database) -> None:
    with database.session_factory() as session:
        repository = DatabaseRecordRepository(session)
        record = repository.add(DatabaseRecord(name="first"))
        repository.add(DatabaseRecord(name="second"))
        session.commit()

        assert repository.get(record.id) is record
        assert len(repository.list_page(limit=1)) == 1
        assert len(repository.list_page(limit=0)) == 1

        repository.delete(record)
        session.commit()
        assert repository.get(record.id) is None


def test_uncommitted_changes_are_rolled_back_when_session_closes(database: Database) -> None:
    with database.session_factory() as session:
        DatabaseRecordRepository(session).add(DatabaseRecord(name="uncommitted"))

    with database.session_factory() as session:
        records = session.scalars(select(DatabaseRecord)).all()

    assert records == []


def test_request_scoped_database_dependency_yields_and_closes_session(database: Database) -> None:
    from unittest.mock import MagicMock

    from app.db.session import get_db_session

    session = MagicMock()
    factory = MagicMock(return_value=session)
    database_with_spy = Database(engine=database.engine, session_factory=factory)  # type: ignore[arg-type]
    dependency = get_db_session(database_with_spy)

    assert next(dependency) is session
    with pytest.raises(StopIteration):
        next(dependency)
    session.close.assert_called_once_with()


def test_route_receives_request_scoped_database_session(database: Database) -> None:
    app = create_app(Settings(_env_file=None, environment="test"), database=database)

    @app.get("/_test/database-session")
    def database_session_probe(session: DbSession) -> dict[str, bool]:
        return {"connected": session.execute(text("SELECT 1")).scalar_one() == 1}

    with TestClient(app) as client:
        response = client.get("/_test/database-session")

    assert response.status_code == 200
    assert response.json() == {"connected": True}


def test_readiness_checks_database_and_is_versioned(database: Database) -> None:
    app = create_app(Settings(_env_file=None, environment="test"), database=database)

    with TestClient(app) as client:
        response = client.get("/ready")
        versioned_response = client.get("/api/v1/ready")

    assert response.status_code == 200
    assert response.json()["status"] == "ready"
    assert response.json()["checks"]["database"]["status"] == "ok"
    assert versioned_response.status_code == 200


def test_readiness_failure_returns_standard_service_unavailable(
    database: Database, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("app.api.health.check_database", lambda _engine: DatabaseStatus(reachable=False))
    app = create_app(Settings(_env_file=None, environment="test"), database=database)

    with TestClient(app) as client:
        response = client.get("/ready", headers={"X-Request-ID": "db-check-123"})

    assert response.status_code == 503
    error = response.json()["error"]
    assert error["code"] == "DATABASE_UNAVAILABLE"
    assert error["retryable"] is True
    assert error["request_id"] == "db-check-123"
    assert response.headers["X-Request-ID"] == "db-check-123"
    assert "password" not in response.text.lower()


def test_liveness_does_not_query_database(database: Database, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.api.health.check_database",
        lambda _engine: pytest.fail("liveness must not check PostgreSQL"),
    )
    app = create_app(Settings(_env_file=None, environment="test"), database=database)

    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200


def test_readiness_probe_returns_success_and_latency(sqlite_engine: Engine) -> None:
    status = check_database(sqlite_engine)

    assert status.reachable is True
    assert status.latency_ms is not None
    assert status.latency_ms >= 0


def test_readiness_probe_handles_database_connection_failure() -> None:
    class UnavailableEngine:
        def connect(self) -> None:
            raise OperationalError("SELECT 1", {}, OSError("offline"))

    assert check_database(UnavailableEngine()).reachable is False  # type: ignore[arg-type]


def test_session_factory_disables_autoflush_and_expiration(sqlite_engine: Engine) -> None:
    with create_session_factory(sqlite_engine)() as session:
        assert session.autoflush is False
        assert session.expire_on_commit is False
