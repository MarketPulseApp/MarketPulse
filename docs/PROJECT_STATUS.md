# MarketPulse Project Status & Master Checklist

This document is a unified checklist and status report merging findings from the code overview, test sweep, and active plans. It outlines what needs to be done and fixed for the MarketPulse application to be complete.

## 1. Core Codebase Fixes (From Code Overview)
- [ ] **Implement Neo4j Integration**: Update `app/workers/ingestion.py` so the Neo4j driver executes actual graph creation statements for Insider Trading instead of mocking them.
- [ ] **Implement ChromaDB & NLP**: Implement vector search for semantic deduplication in `deduplicate_and_store_news` and link a real NLP model for `finbert_score_news` (they are currently stubbed).
- [ ] **Implement Predictions & Sentiment Endpoints**: Connect the routers (`app/routers/predictions.py`, `app/routers/sentiment.py`) to the respective PostgreSQL/MongoDB/TimescaleDB collections. Currently, they return hardcoded dummy JSON.
- [ ] **Fix Websocket Streams**: 
  - Allow clients to subscribe to specific symbols for the market WS (`/ws/market`) instead of endlessly streaming Apple data.
  - Replace training dummy data with an actual hook into ML worker progress in `/ws/training`.
- [ ] **Implement TimescaleDB Aggregation**: Uncomment and wire up the TimescaleDB insertion routines for earnings surprise data and insider ratios in `ingestion.py`.

## 2. Testing Fixes (From Test Sweep)
- [ ] **Fix `SURREAL_URL` in Settings**: Add `SURREAL_URL` to the Pydantic `Settings` model (likely `app/core/config.py`), or handle its absence gracefully in `tests/integration/conftest.py`.
- [ ] **Install Missing Packages**: Add and install `respx` and `prometheus-fastapi-instrumentator` in the virtual environment to fix `ModuleNotFoundError` during test collection.
- [ ] **Clean Up Ghost Database Tests**: Delete orphaned test files for unimplemented databases (Astra, Elastic, Influx, Surreal, and ZODB in `tests/unit/db/*`), or write their implementations if they are still planned.

## 3. Swagger UI Exposure (From PLAN.md)
- [ ] **Backend (`app/main.py`)**: Add `root_path="/api"` to the FastAPI app initialization.
- [ ] **Frontend (`web_dashboard/src/components/layout/Sidebar.tsx`)**: Add a new standard HTML `<a>` link (with `target="_blank"`) to `/api/docs` in the sidebar using the `BookOpen` icon.
- [ ] **Deploy & Verify**: Restart the FastAPI service and build/deploy the updated React frontend, verifying the Swagger UI loads successfully at `/api/docs`.

## 4. ML Trading Config Logging (From PLAN_LOGGING.md)
- [ ] **Frontend Logging**: Add `console.log` statements in `Settings.tsx` and `apiClient.ts` to log the outgoing request method, URL, headers, and body for the ML Trading config save.
- [ ] **Backend Middleware (`app/main.py`)**: Implement logging middleware to capture incoming requests, focusing on URL paths, query parameters, headers (especially `x-forwarded-for`, `x-forwarded-proto`, `host`), and body.
- [ ] **Backend Route Logging (`app/routers/settings.py`)**: Add `logger.info` in `/api/v1/settings/trading` to log received payloads and exceptions.
- [ ] **Test via Cloudflare**: Attempt to save the config via the Cloudflare tunnel and analyze logs to diagnose the routing failure.
