import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from prometheus_fastapi_instrumentator import Instrumentator

from app.db.embedded.accuracy_analytics import AccuracyAnalyticsRepository
from app.db.embedded.audit_ledger import AuditLedgerRepository
from app.db.embedded.company_geo import CompanyGeoRepository
from app.infrastructure.valkey import lifespan_valkey
from app.plugins import load_all_plugins
from app.routers import (
    auth,
    data_stream,
    datasources,
    health,
    market_data,
    paper_trading,
    predictions,
    quotas,
    sentiment,
    settings,
    watchlist,
    ws,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("c:\\marketpulse\\MarketPulse\\backend_debug.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

# Global instances
audit_ledger = None
accuracy_db = None
geo_db = None


@asynccontextmanager
async def lifespan(app):
    global audit_ledger, accuracy_db, geo_db

    logger.info("Initializing embedded databases...")

    # Initialize SQLite Audit Ledger
    audit_ledger = AuditLedgerRepository("/data/audit_ledger.sqlite")
    await audit_ledger.initialize()
    await audit_ledger.append(
        action="SYSTEM_STARTUP",
        actor_id="system",
        new_value={"status": "started"},
    )

    # Initialize DuckDB Persistent
    accuracy_db = AccuracyAnalyticsRepository("/data/accuracy.duckdb")

    # Initialize SpatiaLite
    geo_db = CompanyGeoRepository("/data/company_geo.sqlite")
    await geo_db.initialize()

    load_all_plugins()
    async with lifespan_valkey():
        yield

    logger.info("Shutdown complete.")


from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="MarketPulse API", version="0.1.0", lifespan=lifespan, root_path="/api")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://dashboard.brodiepasker.xyz", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info(f"Incoming Request - Method: {request.method} Path: {request.url.path}")
    logger.info(f"Headers: {request.headers}")
    response = await call_next(request)
    return response


Instrumentator().instrument(app).expose(app)

app.include_router(health.router)
app.include_router(market_data.router, prefix="/market", tags=["market"])
app.include_router(sentiment.router, prefix="/sentiment", tags=["sentiment"])
app.include_router(predictions.router, prefix="/predictions", tags=["predictions"])
app.include_router(watchlist.router, prefix="/watchlist", tags=["watchlist"])
app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(paper_trading.router, prefix="/paper-trading", tags=["paper-trading"])
app.include_router(ws.router, prefix="/ws", tags=["websocket"])
app.include_router(settings.router, prefix="/api/v1/settings", tags=["settings"])
app.include_router(quotas.router, prefix="/api/v1/quotas", tags=["quotas"])
app.include_router(data_stream.router, prefix="/api/v1/data-stream", tags=["data-stream"])
app.include_router(datasources.router, prefix="/api/v1/datasources", tags=["datasources"])
