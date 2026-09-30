"""push subscriptions and reminders

Browsers' Web Push subscriptions and the reminders they asked for. On Postgres the new
tables get row-level security, like the others (revision 0002), so Supabase's REST
API exposes nothing.

Revision ID: 0003
Revises: 0002
Create Date: 2026-09-30 17:44:57.891980

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0003"
down_revision: str | Sequence[str] | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "push_subscriptions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("endpoint", sa.String(length=2048), nullable=False),
        sa.Column("p256dh", sa.String(length=100), nullable=False),
        sa.Column("auth", sa.String(length=50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("endpoint"),
    )
    op.create_table(
        "push_reminders",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("subscription_id", sa.String(length=36), nullable=False),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("title", sa.String(length=120), nullable=False),
        sa.Column("body", sa.String(length=300), nullable=False),
        sa.ForeignKeyConstraint(["subscription_id"], ["push_subscriptions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("push_reminders", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_push_reminders_due_at"), ["due_at"], unique=False)
        batch_op.create_index(
            batch_op.f("ix_push_reminders_subscription_id"), ["subscription_id"], unique=False
        )
    if op.get_bind().dialect.name == "postgresql":
        for table in ("push_subscriptions", "push_reminders"):
            op.execute(f'ALTER TABLE "{table}" ENABLE ROW LEVEL SECURITY')


def downgrade() -> None:
    with op.batch_alter_table("push_reminders", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_push_reminders_subscription_id"))
        batch_op.drop_index(batch_op.f("ix_push_reminders_due_at"))
    op.drop_table("push_reminders")
    op.drop_table("push_subscriptions")
