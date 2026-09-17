# Data Ingestion: Phase 5 - Firehose Wiring

## Overview
Wire all the newly created ingestion pipelines directly into the "Raw Ingestion Feed" in the UI. Instead of exclusively polling fragmented databases, we will create a unified real-time firehose in Valkey.

## Tasks

### 1. ARQ Worker Firehose Injection
- **File:** `c:\marketpulse\MarketPulse\app\workers\ingestion.py`
- **Details:**
  - Update `run_ingestion_for_plugin`. Immediately after a plugin returns its `records` array, serialize each record into a unified firehose payload (`source`, `type`, `timestamp`, `payload`).
  - Use the Valkey client (`ctx["redis"]`) to `lpush` the JSON payloads onto a `raw_ingestion_feed` list.
  - Apply an `ltrim` to keep the list capped at the last 200 items for memory efficiency.

### 2. FastAPI Stream Endpoint
- **File:** `c:\marketpulse\MarketPulse\app\routers\data_stream.py`
- **Details:**
  - Rewrite `get_raw_data_stream` (the `GET /raw` endpoint) to connect to Valkey instead of MongoDB.
  - Perform an `lrange raw_ingestion_feed 0 100` and return the deserialized JSON directly to the frontend.

### 3. UI Alignment & Unit Testing
- **File:** `c:\marketpulse\MarketPulse\app\tests\routers\test_data_stream.py`
- **Details:**
  - Write Pytest fixtures to mock the Valkey `lrange` response.
  - Verify the endpoint returns the exact schema expected by the `RawData.tsx` React component (`source`, `type`, `timestamp`, `payload`).
