import asyncio
import os

import functions
from arq import run_worker
from arq.connections import RedisSettings

VALKEY_URL = os.getenv("VALKEY_URL", "redis://localhost:6379")


def parse_redis_settings(url: str) -> RedisSettings:
    host_port = url.replace("redis://", "")
    host, port = host_port.split(":") if ":" in host_port else (host_port, "6379")
    return RedisSettings(host=host, port=int(port))


class WorkerSettings:
    redis_settings = parse_redis_settings(VALKEY_URL)
    functions = functions.all_functions
    queue_name = "marketpulse"
    max_jobs = 10
    job_timeout = 300


if __name__ == "__main__":
    asyncio.run(run_worker(WorkerSettings))
