import asyncio
import sys

sys.path.append("/opt/marketpulse")

from app.core.security import get_password_hash
from app.db.postgres.ohlcv import create_pool
from app.db.postgres.user import UserRepository


async def run():
    pool = await create_pool()
    repo = UserRepository(pool)
    await pool.execute("INSERT INTO users (id, email, password_hash, role) VALUES ('11111111-1111-1111-1111-111111111111', 'test@test.com', '%s', 'admin') ON CONFLICT (email) DO NOTHING" % get_password_hash('test1234'))
    print('Done')

if __name__ == "__main__":
    asyncio.run(run())
