import asyncio

import asyncpg


async def run():
    conn = await asyncpg.connect(
        "postgresql://marketpulse:marketpulse_password_1122@192.168.1.123:5432/marketpulse"
    )
    row = await conn.fetchrow("SELECT * FROM system_settings WHERE id = 1")
    print(dict(row) if row else "NO ROW FOUND")
    await conn.close()


asyncio.run(run())
