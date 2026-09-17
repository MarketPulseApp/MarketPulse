import asyncio

import asyncpg


async def run():
    conn = await asyncpg.connect(
        "postgresql://marketpulse:marketpulse_password_1122@192.168.1.123:5432/marketpulse"
    )
    await conn.execute(
        "INSERT INTO system_settings (id, active_strategy, confidence_threshold) VALUES (1, 'strat_1', 0.8) ON CONFLICT (id) DO NOTHING"
    )
    await conn.close()


asyncio.run(run())
