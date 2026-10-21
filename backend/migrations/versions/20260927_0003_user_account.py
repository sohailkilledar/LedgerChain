"""user profiles, organization accounts and preferences

Revision ID: 0003
Revises: 0002
Create Date: 2026-09-27
"""

from collections.abc import Sequence
from uuid import uuid4

import sqlalchemy as sa
from alembic import context, op

revision: str = "0003"
down_revision: str | Sequence[str] | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("display_name", sa.String(length=120), nullable=True))
    op.add_column("users", sa.Column("phone", sa.String(length=32), nullable=True))

    op.create_table(
        "organizations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("account_type", sa.String(length=32), server_default="business", nullable=False),
        sa.Column("status", sa.String(length=24), server_default="active", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "account_type IN ('business', 'sole_proprietorship', 'partnership', 'corporation', 'nonprofit')",
            name="account_type",
        ),
        sa.CheckConstraint("status IN ('active', 'suspended')", name="status"),
        sa.PrimaryKeyConstraint("id", name="pk_organizations"),
    )
    op.create_index("ix_organizations_created_at", "organizations", ["created_at"], unique=False)

    op.create_table(
        "organization_memberships",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("role", sa.String(length=16), server_default="member", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("role IN ('owner', 'member')", name="role"),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.id"], name="fk_organization_memberships_organization_id_organizations", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_organization_memberships_user_id_users", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_organization_memberships"),
        sa.UniqueConstraint("organization_id", "user_id", name="uq_organization_memberships_organization_id"),
    )
    op.create_index("ix_organization_memberships_user_id", "organization_memberships", ["user_id"], unique=False)

    op.create_table(
        "user_settings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("time_zone", sa.String(length=64), server_default="UTC", nullable=False),
        sa.Column("locale", sa.String(length=16), server_default="en", nullable=False),
        sa.Column("date_format", sa.String(length=8), server_default="dmy", nullable=False),
        sa.Column("show_technical_by_default", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("share_usage_data", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("date_format IN ('dmy', 'mdy', 'iso')", name="date_format"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_user_settings_user_id_users", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_user_settings"),
    )

    op.create_table(
        "notification_preferences",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("security_notifications", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("transaction_notifications", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("account_notifications", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("marketing_notifications", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_notification_preferences_user_id_users", ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_notification_preferences"),
    )

    op.create_index("ix_user_settings_user_id", "user_settings", ["user_id"], unique=True)
    op.create_index("ix_notification_preferences_user_id", "notification_preferences", ["user_id"], unique=True)

    if not context.is_offline_mode():
        _create_defaults_for_existing_users()


def _create_defaults_for_existing_users() -> None:
    bind = op.get_bind()
    users = sa.table("users", sa.column("id", sa.Uuid()))
    organizations = sa.table(
        "organizations",
        sa.column("id", sa.Uuid()),
        sa.column("name", sa.String()),
    )
    memberships = sa.table(
        "organization_memberships",
        sa.column("id", sa.Uuid()),
        sa.column("organization_id", sa.Uuid()),
        sa.column("user_id", sa.Uuid()),
        sa.column("role", sa.String()),
    )
    settings = sa.table("user_settings", sa.column("id", sa.Uuid()), sa.column("user_id", sa.Uuid()))
    preferences = sa.table(
        "notification_preferences", sa.column("id", sa.Uuid()), sa.column("user_id", sa.Uuid())
    )

    for user_id in bind.execute(sa.select(users.c.id)).scalars():
        organization_id = uuid4()
        bind.execute(organizations.insert().values(id=organization_id, name="My organization"))
        bind.execute(
            memberships.insert().values(
                id=uuid4(), organization_id=organization_id, user_id=user_id, role="owner"
            )
        )
        bind.execute(settings.insert().values(id=uuid4(), user_id=user_id))
        bind.execute(preferences.insert().values(id=uuid4(), user_id=user_id))


def downgrade() -> None:
    op.drop_index("ix_notification_preferences_user_id", table_name="notification_preferences")
    op.drop_table("notification_preferences")
    op.drop_index("ix_user_settings_user_id", table_name="user_settings")
    op.drop_table("user_settings")
    op.drop_index("ix_organization_memberships_user_id", table_name="organization_memberships")
    op.drop_table("organization_memberships")
    op.drop_index("ix_organizations_created_at", table_name="organizations")
    op.drop_table("organizations")
    op.drop_column("users", "phone")
    op.drop_column("users", "display_name")
