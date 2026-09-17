"""Add system_settings table

Revision ID: 7cc53cf49763
Revises:
Create Date: 2026-09-16 09:23:36.761920

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "7cc53cf49763"
down_revision: str | Sequence[str] | None = "fbf81257f834"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "system_settings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("active_strategy", sa.String(), nullable=False, server_default="default"),
        sa.Column("confidence_threshold", sa.Float(), nullable=False, server_default="0.999"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.execute(
        "INSERT INTO system_settings (id, active_strategy, confidence_threshold) VALUES (1, 'default', 0.999)"
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("system_settings")
