"""dummy

Revision ID: fbf81257f834
Revises: 
"""

from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "fbf81257f834"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
