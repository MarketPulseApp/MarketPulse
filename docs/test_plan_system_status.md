# System-Status Badge & Infrastructure Health Polling - Test Plan

**Document ID:** TP-FE-SYSSTAT-001  
**Feature:** Phase 2 Stage 4: System-Status Badge (`useHealthCheck` Polling)  
**Target Application:** MarketPulse Web Dashboard (`web_dashboard/src/hooks/useHealthCheck.ts`, `web_dashboard/src/components/layout/Topbar.tsx`) & Backend API (`app/routers/health.py`)  
**Role:** Test Engineer  
**Status:** Ready for Execution  

---

## 1. Overview & Objectives

In Phase 2 Stage 4, MarketPulse introduces an infrastructure health indicator badge in the dashboard topbar. The frontend periodically polls the backend `/health/full` endpoint using the `useHealthCheck` React hook to monitor core infrastructure subsystems (PostgreSQL/TimescaleDB, Valkey/Redis, MongoDB, ChromaDB) and dynamically display the operational state to the user.

The system supports three primary health states:
1. **Healthy (Green):** API is online and all database and vector store subsystems report `"ok"`.
2. **Degraded (Yellow/Amber):** API is reachable, but one or more backing services (e.g., PostgreSQL, Valkey, MongoDB, ChromaDB) report an error or timeout.
3. **Offline (Red):** The API server is completely unreachable (connection refused, network disconnected, timeout, or 5xx gateway failure).

### Primary Testing Objectives:
- **Verification of `useHealthCheck` Polling:** Confirm that the hook issues periodic GET requests to `/health/full` on the designated cadence (default 10 seconds), avoids duplicate intervals, and cleans up timers on unmount.
- **Degraded State Verification:** Validate that failing a database connection (specifically PostgreSQL or Valkey/Mongo/Chroma) accurately reflects `status: "degraded"` in the backend response and transitions the UI badge from green to yellow/amber.
- **Offline State Verification:** Validate that terminating the API process or blocking network transport immediately triggers the catch block, transitioning the badge from green/yellow to red ("offline").
- **Recovery & Reconnection Verification:** Ensure that restoring failing services automatically transitions the badge back to "healthy" (green) on the subsequent polling tick without requiring a manual page refresh.
- **UI, Accessibility & Theme Compliance:** Verify badge rendering, pulsating animation, tooltip descriptions, ARIA attributes (`role="status"`, `aria-label`), and contrast in both Light and Dark themes.

---

## 2. System Architecture & Polling Data Flow

```
+---------------------------------------------------------------------------------------+
| MarketPulse Web Dashboard (Browser)                                                   |
|                                                                                       |
|   Topbar.tsx                                                                          |
|   +-------------------------------------------------------------------------------+   |
|   | [Overview] [Status Badge (🟢/🟡/🔴)]       [Theme Toggle] [Bell] [User Profile]|   |
|   +-------------------------------------------------------------------------------+   |
|                               ^                                                       |
|                               | status: 'healthy' | 'degraded' | 'offline'            |
|                               |                                                       |
|   useHealthCheck(intervalMs = 10000)                                                  |
|   - Starts setInterval on mount                                                       |
|   - Invokes apiClient.get('/health/full')                                             |
|   - Cleans up clearInterval on unmount                                                |
+---------------------------------------------------------------------------------------+
                                |
               HTTP GET /api/v1/health/full
               (Interval: 10 seconds)
                                v
+---------------------------------------------------------------------------------------+
| MarketPulse FastAPI Backend (`app/routers/health.py`)                                  |
|                                                                                       |
|   Endpoint: @router.get("/health/full")                                               |
|   Performs async ping checks with 3-second connect timeouts:                          |
|   +-------------------+-------------------+-------------------+-------------------+   |
|   | PostgreSQL        | Valkey (Redis)    | MongoDB           | ChromaDB          |   |
|   | (asyncpg.connect) | (redis.ping)      | (motor admin cmd) | (/heartbeat)      |   |
|   +-------------------+-------------------+-------------------+-------------------+   |
|                                                                                       |
|   Status Determination:                                                               |
|   - All checks == "ok"                --> {"status": "ok", "checks": {...}}           |
|   - Any check != "ok" (Exception)     --> {"status": "degraded", "checks": {...}}     |
|   - Process terminated / Unreachable  --> Network Error (Axios catch -> "offline")    |
+---------------------------------------------------------------------------------------+
```

---

## 3. Test Environment & Prerequisites

### 3.1 Environments Under Test
- **Frontend Client:** `http://localhost:5173` (Vite dev server) or deployed dashboard container
- **Backend API:** `http://127.0.0.1:8080` (local uvicorn) or `http://192.168.1.134:8080` (LXC API server)
- **Infrastructure Services (Docker Compose / Podman / LXC):**
  - PostgreSQL / TimescaleDB: Port `5432` (`marketpulse-postgres`)
  - Valkey: Port `6379` (`marketpulse-valkey`)
  - MongoDB: Port `27017` (`marketpulse-mongo`)
  - ChromaDB: Port `8000` (`marketpulse-chroma`)

### 3.2 Required Tools & Instrumentation
- **Browser Developer Tools:**
  - **Network Tab:** Filter by `health/full` to inspect request cadence, headers, and JSON responses.
  - **Console Tab:** Monitor for unexpected errors or uncaught promise rejections.
  - **Network Throttling:** Ability to toggle "Offline" mode.
- **Terminal Access:** Access to execute `docker`, `curl`, or command-line scripts to halt/restart backend and DB services.

---

## 4. Health Check States & Specification Matrix

| State | Backend Endpoint HTTP Status | Backend Response Body (`/health/full`) | Hook `status` Value | UI Dot Color | Badge Label / Tooltip |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Healthy** | `200 OK` | `{"status": "ok", "checks": {"postgres": "ok", "valkey": "ok", "mongodb": "ok", "chroma": "ok"}}` | `'healthy'` | Green (`bg-emerald-500` / `bg-green-500`) | "Systems Operational" |
| **Degraded** | `200 OK` | `{"status": "degraded", "checks": {"postgres": "connection refused...", "valkey": "ok", ...}}` | `'degraded'` | Yellow/Amber (`bg-amber-500` / `bg-yellow-500`) | "System Degraded (DB Issue)" |
| **Offline** | Network Error / `502 Bad Gateway` / `ECONNREFUSED` / Timeout | *(None - Request Failed / Rejected Promise)* | `'offline'` | Red (`bg-rose-500` / `bg-red-500`) | "System Offline" |

---

## 5. Fault Injection & Simulation Methodology

To systematically verify the badge and hook behavior, use the following simulation techniques for **Degraded** and **Offline** conditions.

### 5.1 Triggering the "Degraded" State (Failed DB Connection)

The system transitions to "Degraded" when the API is running, but one or more backing databases fail their connection check. Choose one of the following methods:

#### Method A: Docker Container Suspension (Live Infrastructure)
1. Ensure the full stack is running (`docker compose up -d` or active LXC containers).
2. Stop only the PostgreSQL database container:
   ```bash
   docker stop marketpulse-postgres
   ```
   *(Alternatively, stop Valkey: `docker stop marketpulse-valkey` or Mongo: `docker stop marketpulse-mongo`)*
3. Observe backend logs (`docker logs -f marketpulse-api` or uvicorn console).
4. Verify backend endpoint directly via curl:
   ```bash
   curl -s http://localhost:8080/health/full | jq .
   ```
   **Expected Response:**
   ```json
   {
     "status": "degraded",
     "checks": {
       "postgres": "Connection refused or timed out",
       "valkey": "ok",
       "mongodb": "ok",
       "chroma": "ok"
     }
   }
   ```
5. To recover:
   ```bash
   docker start marketpulse-postgres
   ```

#### Method B: Temporary Backend Code Mock (Isolated Testing)
If running without Docker or in a local mock environment, temporarily simulate a DB failure in `app/routers/health.py`:
```python
# In app/routers/health.py under health_full():
# Simulate DB error:
checks["postgres"] = "ConnectionRefusedError: [Errno 111] Connection refused"
```
Revert the change once testing is complete.

#### Method C: Browser DevTools Network Interception / Local Overrides
1. Open DevTools in Chrome/Edge (`F12`).
2. Go to the **Network** tab, find a request to `health/full`.
3. Right-click the request and select **Override content** (or use Request Interceptor / Mockoon).
4. Edit the response body to:
   ```json
   {
     "status": "degraded",
     "checks": {
       "postgres": "Mocked asyncpg connection timeout",
       "valkey": "ok",
       "mongodb": "ok",
       "chroma": "ok"
     }
   }
   ```
5. Save the override. The next polling tick will consume the mocked degraded response.

---

### 5.2 Triggering the "Offline" State (API Outage)

The system transitions to "Offline" when the network request to `/health/full` fails entirely. Choose one of the following methods:

#### Method A: Terminate the Backend API Process (Service Outage)
1. Stop the running FastAPI / Uvicorn server:
   - If running in terminal: Press `Ctrl + C`.
   - If running in Docker:
     ```bash
     docker stop marketpulse-api
     ```
   - If running in Linux/LXC:
     ```bash
     sudo systemctl stop marketpulse-api
     ```
2. Verify with curl:
   ```bash
   curl http://localhost:8080/health/full
   # Output: curl: (7) Failed to connect to localhost port 8080: Connection refused
   ```
3. To recover: Restart the FastAPI server (`docker start marketpulse-api` or restart uvicorn).

#### Method B: Browser DevTools Offline Mode (Client-Side Network Loss)
1. In the browser where the dashboard is running, open **DevTools** (`F12`).
2. Navigate to the **Network** tab.
3. In the throttling dropdown (labeled "No throttling" by default), select **Offline**.
4. Within 10 seconds (the next polling tick), Axios will fail with `ERR_INTERNET_DISCONNECTED` or `Network Error`.
5. To recover: Switch the throttling dropdown back to **No throttling**.

#### Method C: URL Blocking in DevTools
1. In DevTools, open the **Network Request Blocking** drawer (`Ctrl+Shift+P` -> `Show Network request blocking`).
2. Click **Add pattern** and enter `*health/full*`.
3. Check the enable box. Subsequent polling requests will return `(blocked:devtools)`.
4. To recover: Uncheck the blocking rule.

---

## 6. Detailed Test Cases

### TC-SYSSTAT-01: Nominal Polling & Healthy State Verification
**Objective:** Confirm initial load and continuous polling of the `/health/full` endpoint when all services are operational.

- **Preconditions:**
  - Backend API is running with all database containers active (Postgres, Valkey, Mongo, Chroma).
  - Web dashboard is loaded at `http://localhost:5173`.
  - Browser DevTools is open to the **Network** tab (filter: `health`).
- **Steps:**
  1. Open or refresh the dashboard page.
  2. Inspect the Network tab immediately upon page load.
  3. Observe the initial HTTP GET request to `/health/full`.
  4. Inspect the HTTP response code and payload.
  5. Inspect the Topbar status indicator in the UI.
  6. Hover over or inspect the status indicator.
- **Expected Results:**
  - An initial request to `/health/full` is fired immediately on component mount (line 29 in `useHealthCheck.ts`).
  - Response code is `200 OK`.
  - Response body contains `status: "ok"`.
  - Status indicator in the Topbar renders a solid or pulsing **Green** dot (`bg-emerald-500` or `bg-green-500`).
  - Tooltip/text displays "Healthy", "Operational", or "All systems normal".
  - Console shows no unhandled errors or warnings.

---

### TC-SYSSTAT-02: Polling Interval Cadence & Memory Cleanup
**Objective:** Verify that `useHealthCheck` polls every 10 seconds and releases interval timers upon component unmount.

- **Preconditions:**
  - User is on the dashboard.
  - Browser DevTools **Network** tab is open with timestamps enabled.
- **Steps:**
  1. Leave the dashboard open without user interaction for 45 seconds.
  2. Record the timestamps of consecutive requests to `/health/full`.
  3. Calculate the delta between successive requests.
  4. Navigate away from the view containing Topbar (or unmount Topbar in test harness).
  5. Observe the Network tab for another 30 seconds.
- **Expected Results:**
  - Successive `/health/full` requests occur at consistent intervals of **10,000 ms ± 500 ms** (10 seconds).
  - No duplicate or overlapping polling loops are initiated (exactly 1 request per interval).
  - When the component unmounts, the interval is cleared via `clearInterval`, and no further network calls are dispatched.

---

### TC-SYSSTAT-03: Degraded State Simulation via DB Failure
**Objective:** Verify that a database connection failure transitions the status badge to "Degraded" (Yellow/Amber).

- **Preconditions:**
  - Dashboard is open and currently displaying "Healthy" (Green dot).
  - Terminal access is available.
- **Steps:**
  1. Trigger a DB failure using Section 5.1 (e.g., `docker stop marketpulse-postgres` or apply backend mock).
  2. Watch the **Network** tab in the browser for the next scheduled polling tick (within 10 seconds).
  3. Inspect the response payload of the `/health/full` request.
  4. Observe the status badge in the Topbar.
  5. Hover over the badge to inspect the tooltip or status text.
- **Expected Results:**
  - Endpoint returns HTTP `200 OK` with payload:
    `{ "status": "degraded", "checks": { "postgres": "<error string>", ... } }`
  - Hook state updates to `'degraded'`.
  - Topbar status indicator changes from Green to **Yellow/Amber** (`bg-amber-500` or `bg-yellow-500`).
  - Status tooltip or label updates to reflect "Degraded" or "Database Warning".
  - The rest of the dashboard remains interactive without application crashes.

---

### TC-SYSSTAT-04: Degraded Recovery to Healthy
**Objective:** Verify automatic self-healing transition from "Degraded" back to "Healthy" when the DB reconnects.

- **Preconditions:**
  - System is currently in "Degraded" state (Yellow dot, PostgreSQL stopped).
- **Steps:**
  1. Restore the database service:
     ```bash
     docker start marketpulse-postgres
     ```
  2. Wait up to 10 seconds for the next polling cycle.
  3. Inspect the `/health/full` network request in DevTools.
  4. Observe the status badge in the Topbar.
- **Expected Results:**
  - Once Postgres is ready, `/health/full` returns `{"status": "ok", "checks": {"postgres": "ok", ...}}`.
  - Hook state transitions from `'degraded'` to `'healthy'`.
  - Topbar indicator seamlessly transitions from Yellow/Amber back to **Green**.
  - No manual page reload or user intervention is required.

---

### TC-SYSSTAT-05: Offline State Simulation via API Shutdown
**Objective:** Verify that stopping the backend API server transitions the status badge to "Offline" (Red).

- **Preconditions:**
  - Dashboard is open and currently displaying "Healthy" or "Degraded".
  - Terminal access is available.
- **Steps:**
  1. Stop the backend API using Section 5.2 (e.g., `docker stop marketpulse-api` or terminate the Uvicorn process).
  2. Wait up to 10 seconds for the next polling tick.
  3. Inspect the Network tab in DevTools: observe failed HTTP request (`ERR_CONNECTION_REFUSED` or timeout).
  4. Observe the status badge in the Topbar.
  5. Hover over the badge to inspect the tooltip or status text.
- **Expected Results:**
  - The request to `/health/full` fails and is caught by the `catch (error)` block in `useHealthCheck.ts`.
  - Hook state updates to `'offline'`.
  - Topbar status indicator transitions to **Red** (`bg-rose-500` or `bg-red-500`).
  - Tooltip/label indicates "System Offline" or "Backend Unreachable".
  - The application handles the error gracefully without throwing uncaught React errors or rendering a blank screen.

---

### TC-SYSSTAT-06: Offline Recovery to Healthy
**Objective:** Verify automatic recovery from "Offline" back to "Healthy" when the API server resumes.

- **Preconditions:**
  - System is in "Offline" state (Red dot, API stopped).
  - Dashboard remains open in the browser.
- **Steps:**
  1. Restart the backend API server:
     ```bash
     docker start marketpulse-api
     ```
     *(Or start uvicorn: `uvicorn app.main:app --port 8080`)*
  2. Wait for the server to finish initialization.
  3. Allow `useHealthCheck` to execute its subsequent polling tick.
  4. Inspect the Network tab and Topbar badge.
- **Expected Results:**
  - The polling request succeeds with HTTP `200 OK`.
  - Hook state transitions from `'offline'` to `'healthy'`.
  - Topbar status badge switches from Red back to **Green**.
  - System logs confirm successful connection restoration.

---

### TC-SYSSTAT-07: Rapid State Flapping / Transition Sequences
**Objective:** Verify state stability across rapid transitions (Healthy -> Degraded -> Offline -> Degraded -> Healthy).

- **Preconditions:**
  - Stack is running.
- **Steps:**
  1. Start at Healthy (Green).
  2. Stop PostgreSQL container -> Verify badge turns Yellow within 10s.
  3. Stop API container -> Verify badge turns Red within 10s.
  4. Restart API container (with Postgres still stopped) -> Verify badge turns Yellow within 10s.
  5. Restart PostgreSQL container -> Verify badge returns to Green within 10s.
- **Expected Results:**
  - Badge reliably reflects each state in sequence without getting stuck in an outdated state.
  - React state updates correctly without race conditions or memory leaks.

---

### TC-SYSSTAT-08: UI Presentation, Accessibility & Theme Contrast
**Objective:** Verify visual appearance, theme switching (Light/Dark), and accessibility compliance.

- **Preconditions:**
  - User is on the dashboard.
- **Steps:**
  1. Inspect the status badge element in the Topbar DOM:
     - Verify presence of `role="status"` or `aria-live="polite"`.
     - Verify accessible `aria-label` (e.g. `aria-label="System status: healthy"`).
  2. Switch the dashboard to **Dark Mode** via the Topbar theme toggle:
     - Verify Green dot (`bg-emerald-500`), Yellow dot (`bg-amber-500`), and Red dot (`bg-rose-500`) remain vibrant and clearly distinguishable against dark header background (`dark:bg-gray-800`).
  3. Switch back to **Light Mode**:
     - Verify all three colors maintain sufficient contrast against light header background (`bg-white`).
  4. Test on a mobile viewport (width: 375px):
     - Ensure the badge does not cause layout overflow or displace adjacent icons (Theme, Bell, User profile).
- **Expected Results:**
  - Color contrast meets WCAG AA criteria (minimum 3:1 for graphical UI indicators).
  - Badge is fully responsive and readable across all viewport sizes.
  - Screen readers announce the system status change cleanly.

---

## 7. Automated Test Suites & Code Snippets

### 7.1 Frontend Hook Unit Test (Vitest / React Testing Library)

Create or execute unit tests for `useHealthCheck` using mock timers:

```typescript
import { renderHook, act } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { useHealthCheck } from './useHealthCheck';
import apiClient from '../api/client';

vi.mock('../api/client');

describe('useHealthCheck Hook', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('initializes with healthy and maintains healthy when status is ok', async () => {
    (apiClient.get as any).mockResolvedValue({
      data: { status: 'ok', checks: { postgres: 'ok', valkey: 'ok' } }
    });

    const { result } = renderHook(() => useHealthCheck(5000));

    await act(async () => {
      vi.advanceTimersByTime(100);
    });

    expect(result.current.status).toBe('healthy');
    expect(apiClient.get).toHaveBeenCalledWith('/health/full');
  });

  it('transitions to degraded when response indicates degraded', async () => {
    (apiClient.get as any).mockResolvedValue({
      data: { status: 'degraded', checks: { postgres: 'connection timeout' } }
    });

    const { result } = renderHook(() => useHealthCheck(5000));

    await act(async () => {
      vi.advanceTimersByTime(100);
    });

    expect(result.current.status).toBe('degraded');
  });

  it('transitions to offline when API request fails (network error)', async () => {
    (apiClient.get as any).mockRejectedValue(new Error('Network Error'));

    const { result } = renderHook(() => useHealthCheck(5000));

    await act(async () => {
      vi.advanceTimersByTime(100);
    });

    expect(result.current.status).toBe('offline');
  });

  it('polls at designated interval and cleans up on unmount', async () => {
    (apiClient.get as any).mockResolvedValue({ data: { status: 'ok' } });

    const { unmount } = renderHook(() => useHealthCheck(10000));

    expect(apiClient.get).toHaveBeenCalledTimes(1);

    await act(async () => {
      vi.advanceTimersByTime(10000);
    });
    expect(apiClient.get).toHaveBeenCalledTimes(2);

    await act(async () => {
      vi.advanceTimersByTime(10000);
    });
    expect(apiClient.get).toHaveBeenCalledTimes(3);

    unmount();

    await act(async () => {
      vi.advanceTimersByTime(20000);
    });
    expect(apiClient.get).toHaveBeenCalledTimes(3); // No additional calls after unmount
  });
});
```

---

### 7.2 Backend Health Endpoint Test (Pytest + FastAPI TestClient)

```python
import pytest
from unittest.mock import patch, AsyncMock
from httpx import AsyncClient
from app.main import app

@pytest.mark.asyncio
async def test_health_full_all_ok():
    with patch("asyncpg.connect", new_callable=AsyncMock), \
         patch("redis.asyncio.Redis.ping", new_callable=AsyncMock), \
         patch("motor.motor_asyncio.AsyncIOMotorClient.admin", new_callable=AsyncMock), \
         patch("httpx.AsyncClient.get", return_value=AsyncMock(status_code=200)):
        
        async with AsyncClient(app=app, base_url="http://test") as ac:
            response = await ac.get("/health/full")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ok"
            assert data["checks"]["postgres"] == "ok"

@pytest.mark.asyncio
async def test_health_full_degraded_when_postgres_fails():
    with patch("asyncpg.connect", side_effect=Exception("connection refused")), \
         patch("redis.asyncio.Redis.ping", new_callable=AsyncMock), \
         patch("motor.motor_asyncio.AsyncIOMotorClient.admin", new_callable=AsyncMock), \
         patch("httpx.AsyncClient.get", return_value=AsyncMock(status_code=200)):
        
        async with AsyncClient(app=app, base_url="http://test") as ac:
            response = await ac.get("/health/full")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "degraded"
            assert "connection refused" in data["checks"]["postgres"]
```

---

## 8. Verification Execution Checklist

| ID | Test Case | Target State | Execution Method | Result (Pass/Fail) | Sign-off Date |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **TC-SYSSTAT-01** | Nominal Polling | Healthy (🟢) | Live API & DBs | Pending | |
| **TC-SYSSTAT-02** | Cadence (10s) & Cleanup | Lifecycle | DevTools Network & Timers | Pending | |
| **TC-SYSSTAT-03** | Failed DB Connection | Degraded (🟡) | Stop Postgres container | Pending | |
| **TC-SYSSTAT-04** | Recovery from Degraded | Healthy (🟢) | Start Postgres container | Pending | |
| **TC-SYSSTAT-05** | Total API Shutdown | Offline (🔴) | Stop API process / DevTools Offline | Pending | |
| **TC-SYSSTAT-06** | Recovery from Offline | Healthy (🟢) | Restart API process | Pending | |
| **TC-SYSSTAT-07** | Transition Sequence | Multi-State | Rapid Stop/Start sequence | Pending | |
| **TC-SYSSTAT-08** | Accessibility & Themes | UI Compliance | Light/Dark inspection & ARIA | Pending | |

---

## 9. Rollback & Emergency Procedures

- If polling creates excessive server load:
  - Adjust default `intervalMs` from `10000` (10s) to `30000` (30s) or `60000` (60s) in `useHealthCheck.ts`.
- If the `/health/full` endpoint hangs on dead connections:
  - Ensure timeouts in `app/routers/health.py` (currently 3 seconds for asyncpg, valkey, motor, and httpx) are strictly enforced and do not block the worker thread.
- If CORS or Axios interceptor issues arise:
  - Confirm proxy configuration in `web_dashboard/src/api/client.ts` strips `/api/` prefix appropriately.
