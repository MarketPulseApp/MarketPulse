import json
import logging
from datetime import UTC, datetime

from arq.connections import RedisSettings
from arq.cron import cron

from app.core.config import settings
from app.plugins.datasources.registry import get_enabled_datasources

logger = logging.getLogger(__name__)


# Basic ARQ tasks
async def deduplicate_and_store_news(ctx: dict, records: list[dict]) -> None:
    """
    Chained ARQ Task for ChromaDB Deduplication.
    """
    logger.info(f"Running ChromaDB deduplication for {len(records)} records...")
    # Here we would initialize chromadb client, vectorize the text, and do a similarity search
    # If not a duplicate, store in MongoDB and then enqueue FinBERT scoring!

    # For now, just simulate passing deduplication
    valid_records = records

    # After deduplication, trigger FinBERT
    for record in valid_records:
        await ctx["redis"].enqueue_job(
            "finbert_score_news",
            text=record.get("payload", {}).get("summary", ""),
            ticker=record.get("ticker_symbols", [""])[0],
        )


async def finbert_score_news(ctx: dict, text: str, ticker: str) -> None:
    """
    Chained ARQ task for heavy FinBERT scoring.
    """
    logger.info(f"Running FinBERT on news for {ticker}")
    # Forward this to the ML sidecar or process here


async def run_ingestion_for_plugin(
    ctx: dict, source_name: str, symbols: list[str], since: datetime
) -> None:
    """
    Background task to run a specific plugin's fetch method.
    """
    plugins = await get_enabled_datasources()
    plugin = next((p for p in plugins if p.source_name == source_name), None)

    if not plugin:
        logger.error(f"Plugin {source_name} not found or disabled.")
        return

    try:
        logger.info(f"Starting ingestion for {source_name} (symbols: {len(symbols)})")
        records = await plugin.fetch(symbols, since)
        logger.info(f"Ingested {len(records)} records from {source_name}")

        if not records:
            return

        for record in records:
            firehose_entry = {
                "source": source_name,
                "timestamp": datetime.now(UTC).isoformat(),
                "type": record.record_type,
                "payload": record.payload,
            }
            await ctx["redis"].lpush("raw_ingestion_feed", json.dumps(firehose_entry))
        await ctx["redis"].ltrim("raw_ingestion_feed", 0, 199)

        # VADER scoring is done inside the plugin's fetch method for News!

        # Route the records
        record_type = records[0].record_type

        if record_type == "news":
            # Convert dataclass to dict for ARQ serialization
            records_dicts = [r.__dict__ for r in records]

            from app.db.mongo.sentiment import SentimentRepository

            mongo_client = ctx.get("mongo_client")
            if mongo_client:
                repo = SentimentRepository(mongo_client)
                await repo.insert_news(records_dicts)

            await ctx["redis"].enqueue_job("deduplicate_and_store_news", records=records_dicts)

        elif record_type == "sentiment":
            from app.db.mongo.sentiment import SentimentRepository

            mongo_client = ctx.get("mongo_client")
            if mongo_client:
                repo = SentimentRepository(mongo_client)
                records_dicts = [r.__dict__ for r in records]
                await repo.insert_reddit(records_dicts)

        elif record_type == "price":
            from app.db.postgres.ohlcv import OHLCVRepository

            # Using pool from ctx if available, else mock
            pool = ctx.get("pg_pool")
            if pool:
                repo = OHLCVRepository(pool)
                await repo.insert_batch(records)

            for symbol in symbols:
                await ctx["redis"].enqueue_job("compute_technical_indicators", symbol=symbol)

        elif record_type == "macro":
            from app.db.postgres.macro import MacroRepository

            pool = ctx.get("pg_pool")
            if pool:
                repo = MacroRepository(pool)
                await repo.insert_macro(records)

        elif record_type == "insider_trading":
            # 1. MongoDB sec_filings (Raw records)
            mongo_client = ctx.get("mongo_client")
            if mongo_client:
                # repo = SECFilingsRepository(mongo_client)
                # await repo.insert_insider_trades([r.__dict__ for r in records])
                logger.info("Mock: Storing raw insider trading records in MongoDB sec_filings")

            # 2. Neo4j graph relationships (INSIDER_BOUGHT / INSIDER_SOLD)
            neo4j_driver = ctx.get("neo4j_driver")
            if neo4j_driver:
                # repo = Neo4jInsiderRepository(neo4j_driver)
                # await repo.create_relationships(records)
                logger.info("Mock: Creating INSIDER_BOUGHT/INSIDER_SOLD relationships in Neo4j")
            else:
                logger.info(
                    "Mock: (No Neo4j driver) Creating INSIDER_BOUGHT/INSIDER_SOLD relationships in Neo4j"
                )

            # 3. TimescaleDB aggregated buy/sell ratios
            pool = ctx.get("pg_pool")
            if pool:
                # repo = TimescaleInsiderRepository(pool)
                # await repo.insert_ratios(records)
                logger.info("Mock: Storing aggregated buy/sell ratios in TimescaleDB")

        elif record_type == "earnings":
            pool = ctx.get("pg_pool")
            if pool:
                # 1. PostgreSQL earnings_calendar
                # calendar_repo = EarningsCalendarRepository(pool)
                # await calendar_repo.insert_calendar(records)
                logger.info("Mock: Storing in PostgreSQL earnings_calendar")

                # 2. TimescaleDB earnings_surprise
                # surprise_repo = EarningsSurpriseRepository(pool)
                # await surprise_repo.insert_surprise(records)
                logger.info("Mock: Storing in TimescaleDB earnings_surprise")

    except Exception as e:
        logger.error(f"Ingestion failed for {source_name}: {e}")
        raise


async def cron_poll_all_sources(ctx: dict) -> None:
    """
    Cron job to trigger all enabled plugins.
    """
    logger.info("Cron: polling all data sources.")
    plugins = await get_enabled_datasources()

    active_symbols = ["AAPL", "MSFT", "TSLA"]
    from datetime import timedelta; since = datetime.now(UTC) - timedelta(days=7)

    for plugin in plugins:
        await ctx["redis"].enqueue_job(
            "run_ingestion_for_plugin",
            source_name=plugin.source_name,
            symbols=active_symbols,
            since=since,
        )


class WorkerSettings:
    """
    ARQ worker configuration.
    """

    functions = [run_ingestion_for_plugin, deduplicate_and_store_news, finbert_score_news]
    cron_jobs = [cron(cron_poll_all_sources, minute={0, 15, 30, 45})]
    redis_settings = RedisSettings(
        host=settings.VALKEY_HOST, port=settings.VALKEY_PORT, password=settings.VALKEY_PASSWORD
    )
    max_jobs = 10
    job_timeout = 300

    async def on_startup(ctx: dict) -> None:
        logger.info("ARQ Ingestion Worker starting...")
        try:
            from app.db.postgres.ohlcv import create_pool

            ctx["pg_pool"] = await create_pool()
            logger.info("Connected to Postgres")

            import motor.motor_asyncio

            ctx["mongo_client"] = motor.motor_asyncio.AsyncIOMotorClient(settings.MONGO_URL)
            logger.info("Connected to Mongo")

            try:
                from neo4j import AsyncGraphDatabase

                uri = getattr(settings, "NEO4J_URI", "bolt://localhost:7687")
                user = getattr(settings, "NEO4J_USER", "neo4j")
                pwd = getattr(settings, "NEO4J_PASSWORD", "password")
                ctx["neo4j_driver"] = AsyncGraphDatabase.driver(uri, auth=(user, pwd))
                logger.info("Connected to Neo4j")
            except ImportError:
                logger.warning("neo4j library not installed, mocking Neo4j driver.")
                ctx["neo4j_driver"] = None
            except Exception as e:
                logger.error(f"Failed to connect to Neo4j: {e}")
                ctx["neo4j_driver"] = None

        except Exception as e:
            logger.error(f"Failed to connect to databases: {e}")

    async def on_shutdown(ctx: dict) -> None:
        logger.info("ARQ Ingestion Worker shutting down...")
        pool = ctx.get("pg_pool")
        if pool:
            await pool.close()
            logger.info("Postgres connection closed")

        mongo_client = ctx.get("mongo_client")
        if mongo_client:
            mongo_client.close()
            logger.info("Mongo connection closed")

        neo4j_driver = ctx.get("neo4j_driver")
        if neo4j_driver:
            await neo4j_driver.close()
            logger.info("Neo4j connection closed")

