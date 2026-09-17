"""Add api_key to api_quotas

Revision ID: fafdca71d2a7
Revises: 7cc53cf49763
Create Date: 2026-09-17 14:54:40.659164

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fafdca71d2a7'
down_revision: Union[str, Sequence[str], None] = '7cc53cf49763'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('api_quotas', sa.Column('api_key', sa.Text(), nullable=True))
    op.execute('''
    DROP FUNCTION IF EXISTS fn_get_all_quotas();
    CREATE OR REPLACE FUNCTION fn_get_all_quotas()
    RETURNS TABLE (
        source              TEXT,
        daily_limit         INT,
        monthly_limit       INT,
        daily_used          INT,
        monthly_used        INT,
        is_unlimited        BOOLEAN,
        low_threshold       INT,
        last_reset_daily    TIMESTAMPTZ,
        last_reset_monthly  TIMESTAMPTZ,
        updated_at          TIMESTAMPTZ,
        notes               TEXT,
        api_key             TEXT
    ) AS
    BEGIN
        RETURN QUERY
        SELECT q.source, q.daily_limit, q.monthly_limit,
               q.daily_used, q.monthly_used, q.is_unlimited,
               q.low_threshold, q.last_reset_daily, q.last_reset_monthly,
               q.updated_at, q.notes, q.api_key
        FROM api_quotas q
        ORDER BY q.source;
    END;
     LANGUAGE plpgsql;
    ''')


def downgrade() -> None:
    """Downgrade schema."""
    op.execute('''
    DROP FUNCTION IF EXISTS fn_get_all_quotas();
    CREATE OR REPLACE FUNCTION fn_get_all_quotas()
    RETURNS TABLE (
        source              TEXT,
        daily_limit         INT,
        monthly_limit       INT,
        daily_used          INT,
        monthly_used        INT,
        is_unlimited        BOOLEAN,
        low_threshold       INT,
        last_reset_daily    TIMESTAMPTZ,
        last_reset_monthly  TIMESTAMPTZ,
        updated_at          TIMESTAMPTZ,
        notes               TEXT
    ) AS
    BEGIN
        RETURN QUERY
        SELECT q.source, q.daily_limit, q.monthly_limit,
               q.daily_used, q.monthly_used, q.is_unlimited,
               q.low_threshold, q.last_reset_daily, q.last_reset_monthly,
               q.updated_at, q.notes
        FROM api_quotas q
        ORDER BY q.source;
    END;
     LANGUAGE plpgsql;
    ''')
    op.drop_column('api_quotas', 'api_key')

