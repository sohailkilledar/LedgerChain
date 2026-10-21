from pathlib import Path
from uuid import uuid4

from alembic import command
from alembic.config import Config
import sqlalchemy as sa
from sqlalchemy import MetaData, create_engine, select, text


def test_payment_migration_backfills_existing_organizations() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    try:
        with engine.connect() as connection:
            config = Config(str(Path(__file__).parents[1] / "alembic.ini"))
            config.attributes["connection"] = connection
            command.upgrade(config, "0003")
            organizations = sa.table(
                "organizations",
                sa.column("id", sa.Uuid()),
                sa.column("name", sa.String()),
            )
            organization_id = uuid4()
            connection.execute(
                organizations.insert().values(id=organization_id, name="Legacy organization")
            )
            connection.commit()
            command.upgrade(config, "head")
            organizations_after = sa.Table("organizations", MetaData(), autoload_with=connection)
            row = connection.execute(
                select(organizations_after.c.account_number, organizations_after.c.balance).where(
                    organizations_after.c.id == organization_id
                )
            ).first()
            assert row is not None
            assert row.account_number.startswith("0")
            assert len(row.account_number) == 18
            assert row.balance == 0
            assert connection.execute(text("SELECT COUNT(*) FROM payments")).scalar_one() == 0
    finally:
        engine.dispose()
