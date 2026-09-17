import glob
import re

sql_files = sorted(glob.glob("init/postgres/*.sql"))
combined_sql = ""
for f in sql_files:
    with open(f, encoding="utf-8") as file:
        combined_sql += file.read() + "\n\n"

# Fix the syntax error in 002_functions.sql
combined_sql = re.sub(r"\btime\s+TIMESTAMPTZ,", '"time" TIMESTAMPTZ,', combined_sql)
combined_sql = re.sub(r"time\s+TIMESTAMPTZ,\s*symbol", '"time" TIMESTAMPTZ, symbol', combined_sql)

# Fix the columnstore missing error for compression policy
combined_sql = combined_sql.replace(
    "SELECT add_compression_policy('ohlcv',",
    "ALTER TABLE ohlcv SET (timescaledb.compress, timescaledb.compress_segmentby = 'symbol');\nSELECT add_compression_policy('ohlcv',",
)

# Fix missing IF NOT EXISTS for sentiment_scores
combined_sql = combined_sql.replace(
    "CREATE TABLE sentiment_scores (", "CREATE TABLE IF NOT EXISTS sentiment_scores ("
)

# Fix fn_get_sentiment_trend which is redefined with different return types
combined_sql = combined_sql.replace(
    "CREATE OR REPLACE FUNCTION fn_get_sentiment_trend(",
    "DROP FUNCTION IF EXISTS fn_get_sentiment_trend(text, integer) CASCADE;\nCREATE OR REPLACE FUNCTION fn_get_sentiment_trend(",
)

# Avoid breaking the triple quote string in Python
combined_sql = combined_sql.replace('"""', '\\"\\"\\"')

migration_code = f'''"""Initial schema

Revision ID: fbf81257f834
Revises: 
Create Date: 2026-09-15 14:57:32.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'fbf81257f834'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    connection = op.get_bind()
    sql_statements = """{combined_sql}"""
    # Use exec_driver_sql to avoid SQLAlchemy parsing colons as bind parameters
    connection.exec_driver_sql(sql_statements)

def downgrade() -> None:
    pass
'''

with open("migration.py", "w", encoding="utf-8") as f:
    f.write(migration_code)
print("Migration file created")
