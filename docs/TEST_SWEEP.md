# Test Sweep Report

**Date:** 2026-09-17
**Directory:** `c:\marketpulse\MarketPulse\app`

## Overview
A full test sweep was attempted using `pytest`. Unfortunately, **zero tests passed** because the entire test suite failed at the collection phase. Pytest threw 12 distinct collection errors, preventing any individual test from actually executing.

## Failed Tests & Issues

### 1. Missing `SURREAL_URL` in Settings
- **Location:** `tests/integration/conftest.py`
- **Error:** `AttributeError: 'Settings' object has no attribute 'SURREAL_URL'`
- **Reason:** The integration test configuration attempts to parse `settings.SURREAL_URL`, but the `Settings` schema (likely in `app/core/config.py` or similar) does not define this attribute.
- **Estimated Fix:** Add `SURREAL_URL` to the Pydantic `Settings` model, or handle its absence gracefully in `conftest.py` if SurrealDB is optional.

### 2. Missing Python Packages
- **Locations:**
  - `tests/plugins/datasources/test_fred_plugin.py`
  - `tests/plugins/datasources/test_polygon_plugin.py`
  - `tests/plugins/datasources/test_reddit_plugin.py`
  - `tests/routers/test_data_stream.py`
- **Errors:**
  - `ModuleNotFoundError: No module named 'respx'`
  - `ModuleNotFoundError: No module named 'prometheus_fastapi_instrumentator'`
- **Reason:** The virtual environment (`.venv`) lacks these dependencies, which are required for mocking HTTP calls (`respx`) and instrumenting the FastAPI app.
- **Estimated Fix:** Add `respx` and `prometheus-fastapi-instrumentator` to the project's `requirements.txt` or `pyproject.toml` (likely under a `[dev]` or `[test]` group) and run `pip install`.

### 3. Missing / Ghost Database Modules
- **Locations:**
  - `tests/unit/db/astra/test_api_call_log.py`
  - `tests/unit/db/elastic/test_news_search.py`
  - `tests/unit/db/embedded/test_company_geo.py` (also attempts to import `db.elastic`)
  - `tests/unit/db/embedded/test_zodb_registry.py`
  - `tests/unit/db/influx/test_mention_count.py`
  - `tests/unit/db/surreal/test_cross_domain.py`
  - `tests/unit/db/surreal/test_sector.py`
- **Errors:** `ModuleNotFoundError` for `db.astra`, `db.elastic`, `db.embedded.zodb_registry`, `db.influx`, and `db.surreal`.
- **Reason:** The test files are trying to import database implementations that **do not exist** in the `app/db` directory. A check of `app/db` shows only `chroma`, `embedded`, `minio`, `mongo`, `neo4j`, `postgres`, and `valkey`. There are no folders for Astra, Elastic, Influx, or Surreal, and no `zodb_registry.py` in `embedded`.
- **Estimated Fix:** These appear to be orphaned tests, likely copied from another project or left over from architectural changes. If these databases are no longer part of the stack, these test files should be **deleted**. If they are planned for the future, the missing implementations must be written.

## Conclusion
To get the test suite running again:
1. Clean up or delete the ghost database tests.
2. Install the missing mock and observability packages.
3. Fix the `conftest.py` setting attribute. 

Once these collection errors are resolved, `pytest` will be able to discover and run the actual tests.
