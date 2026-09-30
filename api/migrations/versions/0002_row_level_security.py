"""row-level security on Postgres

Supabase serves the tables of the public schema through its REST API to anyone
holding the project's anon key. With row-level security on and no policies, those
roles see nothing, while the API, which connects as the tables' owner, is unaffected.
SQLite has no such API, so nothing changes there.

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-30 18:00:00

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0002"
down_revision: str | Sequence[str] | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLES = ("users", "people", "life_events", "alembic_version")


def _set(state: str) -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    for table in TABLES:
        op.execute(f'ALTER TABLE "{table}" {state} ROW LEVEL SECURITY')


def upgrade() -> None:
    _set("ENABLE")


def downgrade() -> None:
    _set("DISABLE")
