# ML Model Training UI & WebSocket Telemetry - Test Plan

**Document ID:** TP-FE-TRAINUI-001
**Feature:** Phase 3 Stage 1: Live Progress Bar & WebSocket Telemetry (`/training`)
**Target Application:** MarketPulse Web Dashboard (`web_dashboard/src/pages/Training.tsx`, `web_dashboard/src/components/training/*`) & Backend WebSocket API (`app/routers/ws.py`, `ml_sidecar/server.py`)
**Role:** Test Engineer
**Status:** Ready for Execution

---

## 1. Overview & Objectives

In Phase 3 Stage 1 of the MarketPulse development plan, the platform transitions model retraining into a dedicated, interactive, real-time control room accessible at the `/training` route. Previously, training operations were unmonitored or triggered blindly via static API endpoints without streaming progress indicators.

The `/training` page introduces an end-to-end interactive training console featuring:
1. **Model Training Control:** A primary **"Start Training"** action button allowing operators to initiate model training runs with configurable parameters.
2. **Real-Time Progress Bar:** A dynamic progress bar that advances smoothly from 0% to 100% reflecting current training completion status.
3. **Live Telemetry HUD:** Real-time metrics streaming over WebSocket, including current execution stage (e.g., data ingestion, feature engineering, model fitting, validation), active data source, step/epoch counters, current batch loss, validation loss, and elapsed time.
4. **Auto-Scrolling Terminal Console:** An embedded ANSI/monospaced terminal viewer displaying streaming stdout/stderr training logs that automatically scrolls to the latest incoming line as new WebSocket telemetry arrives.
5. **Sticky Scrolling & User Override:** Automatic scrolling must pin to the bottom when the user is at the bottom, but allow manual scrolling inspection when the user scrolls upward, resuming auto-scroll when returned to the bottom.
6. **Error Handling & Resilience:** Graceful handling of WebSocket disconnections, backend exceptions, and network latency without freezing the user interface.

### Primary Testing Objectives:
- **Route & Layout Verification:** Confirm `/training` is properly registered in `App.tsx`, secured with authentication (`PrivateRoute`), and accessible via the application navigation `Sidebar.tsx`.
- **Start Training Trigger:** Verify that clicking the "Start Training" button issues the appropriate training initiation request, transitions the UI into the active state, disables duplicate submissions, and initializes the WebSocket stream.
- **Progress Bar Advancement:** Verify that incoming WebSocket telemetry packets update the progress bar width, percentage label, and ARIA attributes in real time.
- **Terminal Log Streaming & Auto-Scroll:** Verify that received log chunks are appended without data truncation and that the terminal container automatically scrolls (`scrollTop = scrollHeight`) to keep the latest message visible.
- **Scroll Lock / Override Behavior:** Validate that if a user manually scrolls up to inspect previous epoch outputs, the auto-scroll does not aggressively yank the viewport back down until the user scrolls back to the bottom.
- **Telemetry HUD Metric Updates:** Ensure stage indicators, epoch/step counters, and loss values update synchronously with incoming telemetry frames.
- **Completion & Error States:** Validate state transitions upon normal completion (100% progress, summary metrics) and error scenarios (failed training, disconnected socket, timeout).
- **Responsive Design & Dark Theme:** Confirm terminal contrast, progress bar styling, and layout stability across desktop, tablet, and mobile viewports in both Light and Dark modes.

---

## 2. System Architecture & Telemetry Data Flow

```
+-----------------------------------------------------------------------------------------------+
| MarketPulse Web Dashboard (Browser Client)                                                    |
|                                                                                               |
|  /training Route                                                                              |
|  +-----------------------------------------------------------------------------------------+  |
|  | Header: ML Retraining Station               [Status: IDLE / TRAINING / COMPLETED]       |  |
|  | Configuration Options: Model [RandomForest v1] | Tickers [AAPL, NVDA] | Epochs [10]     |  |
|  | [ ▶ Start Training ] [ ⏹ Abort ]                                                        |  |
|  +-----------------------------------------------------------------------------------------+  |
|  | Telemetry HUD:                                                                          |  |
|  | [ Stage: Fitting Model ] [ Source: TimescaleDB ] [ Epoch: 4/10 ] [ Loss: 0.0341 ]       |  |
|  +-----------------------------------------------------------------------------------------+  |
|  | Progress Bar: [=============================>                  ] 40%                    |  |
|  +-----------------------------------------------------------------------------------------+  |
|  | Terminal Console (Monospace Log Stream - Auto-Scrolling):                               |  |
|  | [19:15:01] Ingesting 2,500 OHLCV bars from TimescaleDB...                               |  |
|  | [19:15:03] Generating 23 technical indicators (RSI, MACD, BB, VWAP)...                   |  |
|  | [19:15:06] Training RandomForestRegressor - Estimator 40/100...                         |  |
|  | [19:15:08] Epoch 4/10 - Batch loss: 0.0341 - Val score: 0.892 <--- Auto-scroll pinned  |  |
|  +-----------------------------------------------------------------------------------------+  |
+-----------------------------------------------------------------------------------------------+
                             |                                           ^
              1. POST /api/v1/training/start                             | 2. WebSocket Frames
                 (or WS Handshake)                                       |    (Telemetry & Logs)
                             v                                           |
+-----------------------------------------------------------------------------------------------+
| MarketPulse Backend API (`app/routers/ws.py` & `app/routers/training.py`)                      |
|                                                                                               |
|  WebSocket Endpoint: `/ws/training` or `/api/v1/training/stream`                              |
|  - Accepts client connection with JWT validation                                             |
|  - Spawns / attaches to background training runner                                            |
|  - Streams real-time telemetry packets (JSON) & stdout lines to connected client              |
+-----------------------------------------------------------------------------------------------+
                                             ^
                                             | Inter-process pipes / Redis PubSub / Celery
                                             v
+-----------------------------------------------------------------------------------------------+
| MarketPulse ML Sidecar / Worker (`ml_sidecar/train_model.py`)                                  |
|                                                                                               |
|  - Fetches data from PostgreSQL / TimescaleDB & sentiment caches                              |
|  - Runs feature engineering pipeline                                                          |
|  - Trains ensemble models & calculates step loss                                              |
|  - Emits telemetry events every batch/step                                                    |
+-----------------------------------------------------------------------------------------------+
```

---

## 3. WebSocket Telemetry Schema Specification

The frontend terminal and progress components consume JSON telemetry frames over the WebSocket connection. The protocol adheres to the following message contracts:

### 3.1 Connection Handshake / Status Frame
Sent immediately upon successful connection establishment:
```json
{
  "type": "connection_ack",
  "session_id": "trn-20260916-01a",
  "status": "connected",
  "timestamp": "2026-09-16T19:15:00.000Z"
}
```

### 3.2 Live Progress & Telemetry Frame
Broadcast periodically (e.g., every 250ms - 500ms or on each training step):
```json
{
  "type": "telemetry",
  "session_id": "trn-20260916-01a",
  "stage": "model_training",
  "stage_display": "Fitting Ensemble Model",
  "data_source": "timescaledb_ohlcv",
  "epoch": 4,
  "total_epochs": 10,
  "step": 140,
  "total_steps": 350,
  "progress_pct": 40.0,
  "loss": 0.0341,
  "val_loss": 0.0418,
  "log_line": "[TRAIN] [19:15:08] Epoch 4/10 (step 140/350) - Loss: 0.0341 - Estimators fitted: 40/100",
  "elapsed_seconds": 12.4,
  "timestamp": "2026-09-16T19:15:08.120Z"
}
```

### 3.3 Training Completed Frame
Broadcast when the pipeline finishes successfully:
```json
{
  "type": "completed",
  "session_id": "trn-20260916-01a",
  "stage": "completed",
  "stage_display": "Training Complete",
  "progress_pct": 100.0,
  "metrics": {
    "final_loss": 0.0215,
    "accuracy": 0.914,
    "duration_seconds": 28.6,
    "model_path": "/opt/marketpulse/models/rf_baseline_model.joblib"
  },
  "log_line": "[SUCCESS] [19:15:28] Retraining complete. New model artifacts deployed and hot-reloaded.",
  "timestamp": "2026-09-16T19:15:28.650Z"
}
```

### 3.4 Training Error / Failure Frame
Broadcast if an unhandled exception or data ingestion error occurs:
```json
{
  "type": "error",
  "session_id": "trn-20260916-01a",
  "stage": "error",
  "stage_display": "Training Failed",
  "error_message": "TimescaleDB connection timeout while fetching OHLCV data for AAPL",
  "log_line": "[ERROR] [19:15:14] Traceback (most recent call last): ConnectionRefusedError: [Errno 111]",
  "timestamp": "2026-09-16T19:15:14.300Z"
}
```

---

## 4. Test Environment & Prerequisites

### 4.1 Environments Under Test
- **Frontend URL:** `http://localhost:5173/training` (Vite dev server)
- **Backend API Base:** `http://localhost:8080` (FastAPI backend) or `http://192.168.1.134:8080`
- **WebSocket Endpoint:** `ws://localhost:8080/ws/training` (or proxied via Vite `/api/ws`)
- **ML Sidecar Service:** `http://192.168.1.134:8085` (`ml_sidecar`)

### 4.2 Required Browser Tools & Setup
- **Browser Developer Tools:**
  - **Network Tab:** Filter by `WS` to inspect the live WebSocket frames, message cadence, and payload sizes.
  - **Console Tab:** Monitor for connection state changes, WebSocket errors, or unhandled React render warnings.
  - **Elements / Inspector:** Verify DOM scroll position (`element.scrollTop`, `element.scrollHeight`, `element.clientHeight`) and ARIA attributes.
- **Authentication:** Valid JWT session stored in `localStorage.getItem('token')`.

---

## 5. Training UI State Machine & Verification Matrix

| State | "Start Training" Button | Progress Bar | Telemetry HUD | Terminal Console | Status Indicator |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Idle** | Enabled (`bg-indigo-600`, "Start Training") | 0% (`w-0`, hidden or grey track) | Dashes (`--`), "Idle" | Shows initial prompt: `Ready. Click "Start Training" to begin.` | Grey/Neutral ("Ready") |
| **Starting / Connecting** | Disabled + Spinner ("Connecting...") | 0% (Indeterminate pulse optional) | "Initializing connection..." | `[INFO] Initializing WebSocket connection to training engine...` | Amber/Yellow ("Connecting") |
| **Running / In-Progress** | Disabled ("Training in progress...") | Dynamic (0% -> 99%), Smooth transition | Live stage, epoch, step, loss updating | Continuously appending lines, pinned to bottom (`auto-scroll: ON`) | Blue/Pulsing ("Running") |
| **User Scrolled Up** | Disabled ("Training in progress...") | Dynamic (0% -> 99%) | Live updating | Logs continue appending, scroll frozen on inspected line, "Scroll to Bottom" badge appears | Blue/Pulsing ("Running") |
| **Completed** | Enabled ("Start New Run") | 100% (`bg-emerald-500` / `bg-green-500`) | Final metrics: Stage: Completed, Final Loss, Elapsed Time | Appends completion banner, final model hash/path | Green ("Completed") |
| **Error / Failed** | Enabled ("Retry Training") | Frozen % or Red (`bg-rose-500` / `bg-red-500`) | Stage: Error, error detail card | Appends red error traceback, error summary | Red ("Failed") |
| **Disconnected** | Enabled or "Reconnect" button | Preserved last known % | Stage: Disconnected | `[WARN] WebSocket connection closed unexpectedly.` | Red/Amber ("Disconnected") |

---

## 6. Test Harness & Simulation Methodology

To execute verification without requiring a 30-minute heavy GPU/CPU retraining pipeline for every single test cycle, use the following test harness options:

### 6.1 Method A: Mock WebSocket Telemetry Server (Fast Automated Testing)
Use a lightweight Python mock script (`test_training_mock_ws.py`) that simulates the exact telemetry frames at controlled intervals (e.g. 100ms per step):

```python
import asyncio
import json
import websockets

async def handler(websocket):
    print("Client connected to mock training WS")
    await websocket.send(json.dumps({
        "type": "connection_ack",
        "session_id": "test-mock-001",
        "status": "connected"
    }))

    stages = [
        ("data_ingestion", "TimescaleDB Ingestion", 10, "Fetching 10,000 bars..."),
        ("feature_engineering", "Feature Calculation", 30, "Calculating RSI, MACD, Bollinger Bands..."),
        ("model_training", "RandomForest Fitting", 75, "Fitting trees in forest..."),
        ("validation", "Evaluating Metrics", 95, "Calculating RMSE and direction accuracy...")
    ]

    for stage_key, stage_name, target_pct, desc in stages:
        current_pct = target_pct - 15
        while current_pct <= target_pct:
            await asyncio.sleep(0.3)
            await websocket.send(json.dumps({
                "type": "telemetry",
                "session_id": "test-mock-001",
                "stage": stage_key,
                "stage_display": stage_name,
                "data_source": "timescale_aapl",
                "epoch": 2,
                "total_epochs": 5,
                "step": int(current_pct * 4),
                "total_steps": 400,
                "progress_pct": float(current_pct),
                "loss": round(0.08 - (current_pct * 0.0006), 4),
                "log_line": f"[{stage_name}] Step {int(current_pct * 4)}: {desc} (Loss: {round(0.08 - (current_pct * 0.0006), 4)})"
            }))
            current_pct += 5

    await asyncio.sleep(0.5)
    await websocket.send(json.dumps({
        "type": "completed",
        "session_id": "test-mock-001",
        "stage": "completed",
        "stage_display": "Training Complete",
        "progress_pct": 100.0,
        "metrics": {"final_loss": 0.0182, "duration_seconds": 12.5},
        "log_line": "[SUCCESS] Training pipeline completed successfully."
    }))

async def main():
    async with websockets.serve(handler, "127.0.0.1", 8089):
        print("Mock training WebSocket running on ws://127.0.0.1:8089")
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())
```

### 6.2 Method B: Live Backend Integration
1. Ensure the FastAPI backend is running on `http://localhost:8080`.
2. Connect to the actual training router (`/ws/training` or `/retrain` pipeline).
3. Observe live output streaming directly from `ml_sidecar/train_model.py`.

---

## 7. Detailed Test Cases

### TC-TRN-01: Navigation & Route Registration Verification
**Objective:** Confirm that `/training` is registered in client routes, protected by `PrivateRoute`, and accessible from the Sidebar.

- **Preconditions:**
  - Web dashboard is running (`http://localhost:5173`).
  - User is authenticated with a valid JWT.
- **Steps:**
  1. Navigate to `http://localhost:5173/`.
  2. Inspect the left navigation sidebar.
  3. Verify the existence of a navigation item labeled **"Model Training"** or **"Training"** with an appropriate icon (e.g. `Brain`, `Cpu`, or `Activity` from `lucide-react`).
  4. Click the sidebar item.
  5. Inspect the address bar and page title.
  6. Open an incognito browser window (without authentication) and attempt to directly navigate to `http://localhost:5173/training`.
- **Expected Results:**
  - Sidebar contains the "Training" navigation link.
  - Clicking the link navigates seamlessly to `/training` without full page reload.
  - Active navigation state highlights the Training link in the sidebar (`bg-indigo-50 text-indigo-700` or dark mode equivalent).
  - Unauthenticated access redirects immediately to `/login`.

---

### TC-TRN-02: Initial Page Layout & Idle State Verification
**Objective:** Confirm all UI elements render in their default idle state prior to launching training.

- **Preconditions:**
  - User is navigated to `/training`.
  - No active training session is running.
- **Steps:**
  1. Inspect the main header and description.
  2. Locate the **"Start Training"** button:
     - Verify it is visible, clickable, and styled with primary action colors (e.g., `bg-indigo-600 hover:bg-indigo-700 text-white`).
     - Verify it does not display a loading spinner.
  3. Inspect the **Progress Bar** component:
     - Verify the bar width is 0% (`w-0` or `width: 0%`).
     - Verify percentage indicator text reads `"0%"` or `"Ready"`.
     - Inspect ARIA attributes: `role="progressbar"`, `aria-valuenow="0"`, `aria-valuemin="0"`, `aria-valuemax="100"`.
  4. Inspect the **Telemetry HUD / Metrics Cards**:
     - Status badge displays `"IDLE"` or `"READY"`.
     - Stage card displays `"--"` or `"Standby"`.
     - Data source card displays `"--"`.
     - Epoch counter displays `0 / 0` or `"--"`.
     - Current Loss card displays `"--"`.
  5. Inspect the **Terminal Console**:
     - Verify dark monospaced container styling (`bg-gray-900`, `text-green-400` or `text-gray-200`, `font-mono`).
     - Displays initial placeholder message (e.g. `Ready to train. Click "Start Training" to begin streaming logs.`).
     - No unhandled exceptions or NaN values appear in the DOM.
- **Expected Results:**
  - Clean, professional idle state rendered with zero UI glitches or console warnings.

---

### TC-TRN-03: "Start Training" Click & WebSocket Handshake
**Objective:** Verify that clicking "Start Training" triggers the training process and establishes the WebSocket stream.

- **Preconditions:**
  - User is on `/training`.
  - Browser DevTools open to **Network** (filter: `WS`) and **Console**.
- **Steps:**
  1. Click the **"Start Training"** button.
  2. Observe button state immediately upon click:
     - Verify button text changes to `"Initializing..."` or `"Training in progress..."`.
     - Verify a spinner icon appears.
     - Verify button is `disabled` (`cursor-not-allowed` / `opacity-50`) to prevent duplicate submissions.
  3. Inspect the **Network** tab:
     - Look for WebSocket upgrade request (e.g., `GET /ws/training` with `101 Switching Protocols`).
     - Verify headers include JWT token authorization (via subprotocol, query param, or initial auth frame).
  4. Inspect initial messages exchanged:
     - Look for incoming `connection_ack` or initial telemetry frame.
  5. Inspect Terminal Console:
     - Verify an initial connection log appears (e.g., `[INFO] Connected to telemetry stream. Training job initialized...`).
- **Expected Results:**
  - WebSocket connection opens with HTTP status `101 Switching Protocols`.
  - Single connection established (no duplicate or rapid socket reconnections).
  - Button transitions cleanly to disabled loading state.

---

### TC-TRN-04: Real-Time Progress Bar Advancement
**Objective:** Verify that incoming telemetry packets advance the progress bar smoothly and accurately from 0% towards 100%.

- **Preconditions:**
  - Training has started and WebSocket telemetry packets are arriving.
- **Steps:**
  1. Observe the progress bar fill element as telemetry arrives.
  2. Inspect the DOM element style / class:
     - Verify `width: X%` corresponds to the incoming `progress_pct` value.
     - Verify CSS transition class is applied (e.g., `transition-all duration-300 ease-out`) so the bar moves smoothly rather than jumping abruptly.
  3. Observe the numerical percentage label:
     - Confirm it updates monotonically: `10%` -> `25%` -> `50%` -> `75%` -> `100%`.
  4. Inspect accessibility attributes in the DOM:
     - `aria-valuenow` updates dynamically to match the current percentage.
  5. Verify stage color transitions (optional design enhancement):
     - Normal progress renders in brand/indigo/emerald colors.
- **Expected Results:**
  - Progress bar advances smoothly in direct synchrony with incoming WebSocket frames.
  - Percentage text does not flicker or wrap awkwardly.
  - The bar reaches exactly 100% upon completion.

---

### TC-TRN-05: Real-Time Telemetry HUD & Metrics Synchronization
**Objective:** Verify that stage, data source, epoch/step counters, and loss values update synchronously with telemetry packets.

- **Preconditions:**
  - WebSocket telemetry stream is actively receiving frames.
- **Steps:**
  1. Compare incoming WebSocket frame data in DevTools with the rendered cards on screen:
  2. **Stage Card:** Verify it reflects current phase (e.g., "Data Ingestion" -> "Feature Engineering" -> "Fitting RandomForest" -> "Validation").
  3. **Data Source Card:** Verify active source is displayed (e.g., `TimescaleDB (OHLCV)`, `Reddit Sentiment Cache`).
  4. **Epoch / Step Card:** Verify step and epoch counters update dynamically (e.g. `Epoch: 3 / 10 | Step: 120 / 400`).
  5. **Current Loss Card:** Verify loss values update dynamically and format cleanly to 4 decimal places (e.g. `0.0412`).
  6. **Elapsed Time Counter:** Verify counter increments every second during active training.
- **Expected Results:**
  - Every telemetry packet immediately updates the respective HUD metric card without lag.
  - Numbers format cleanly (no unhandled `NaN`, `undefined`, or overflow strings).

---

### TC-TRN-06: Terminal Console Auto-Scrolling Verification
**Objective:** Verify that the terminal window automatically scrolls to the bottom as new lines of telemetry log text arrive.

- **Preconditions:**
  - Telemetry is actively streaming log lines.
  - Number of log lines exceeds the vertical height of the terminal container (scrollbar is present).
- **Steps:**
  1. Do not touch mouse, trackpad, or keyboard.
  2. Observe the terminal console window as 20+ log lines arrive in succession.
  3. Verify that the most recently received log line is always completely visible at the bottom of the viewport.
  4. Open DevTools Console and execute the scroll verification check:
     ```javascript
     const term = document.querySelector('[data-testid="terminal-container"]') || document.querySelector('.terminal-window');
     console.log({
       scrollHeight: term.scrollHeight,
       scrollTop: term.scrollTop,
       clientHeight: term.clientHeight,
       isAtBottom: Math.abs(term.scrollHeight - term.clientHeight - term.scrollTop) < 5
     });
     ```
  5. Repeat the check across 5 consecutive log updates.
- **Expected Results:**
  - `isAtBottom` returns `true` (within a tolerance of 2–5 pixels) on every incoming log line.
  - Terminal scrolls downward automatically with zero jitter.
  - Log lines maintain monospaced font formatting, preserving timestamp, tag, and message indentation.

---

### TC-TRN-07: Auto-Scroll User Override (Sticky vs Free Scrolling)
**Objective:** Verify that manual upward scrolling pauses auto-scrolling, and scrolling back to bottom resumes it.

- **Preconditions:**
  - Training is running and terminal has accumulated over 50 lines of logs with continuous incoming messages.
- **Steps:**
  1. While logs are actively streaming, use the mouse wheel or trackpad to scroll upward by 20 lines to inspect an earlier log message.
  2. Stop scrolling and observe the viewport for 5 seconds while new messages continue to arrive.
  3. **Verify:** The viewport does **not** forcefully yank back to the bottom. The inspected text remains stable and readable.
  4. Look for an optional user helper badge (e.g. `"New logs below ↓"` or `"Scroll to bottom"` button).
  5. Now scroll the container all the way back to the bottom (or click the "Scroll to bottom" helper button).
  6. Observe subsequent incoming messages.
- **Expected Results:**
  - When the user scrolls away from the bottom (`scrollTop < scrollHeight - clientHeight - 20px`), auto-scroll is temporarily suspended.
  - When the user returns to the bottom (`scrollTop >= scrollHeight - clientHeight - 10px`), auto-scroll automatically re-engages and keeps new messages pinned.

---

### TC-TRN-08: Training Pipeline Normal Completion
**Objective:** Verify system behavior and UI transitions when the training pipeline reaches 100% completion.

- **Preconditions:**
  - Training session in progress, reaching its final epoch.
- **Steps:**
  1. Allow the mock or live training run to complete.
  2. Observe the WebSocket frame with `type: "completed"`.
  3. Inspect the UI elements post-completion:
     - Progress bar reaches `100%` and turns green (`bg-emerald-500`).
     - Telemetry HUD status badge switches to `"COMPLETED"`.
     - Final metrics banner surfaces summary statistics (Total Duration, Final Loss, Validation Score).
     - Terminal displays a clear success banner (e.g. `[SUCCESS] Retraining complete. Model hot-reloaded.`).
     - "Start Training" button re-enables or changes to `"Start New Run"` allowing subsequent sessions.
  4. Click "Start New Run":
     - Verify state resets properly (progress bar returns to 0%, terminal clears or adds divider, ready for next run).
- **Expected Results:**
  - Clean transition to completed state without hanging spinners or deadlocks.
  - Operators can immediately start a fresh run if desired.

---

### TC-TRN-09: Error Handling & Pipeline Failure Simulation
**Objective:** Verify UI error state handling when the backend training process fails or reports an exception.

- **Preconditions:**
  - User is on `/training`.
- **Steps:**
  1. Trigger a failing training run (e.g. via mock sending `type: "error"` or stopping backend database during ingestion).
  2. Click **"Start Training"**.
  3. Observe incoming WebSocket error message.
  4. Inspect the UI:
     - Progress bar stops advancing and switches to error styling (e.g., red `bg-rose-500`).
     - Telemetry HUD status badge switches to `"ERROR"` or `"FAILED"`.
     - An error alert card displays the failure reason (e.g., `"TimescaleDB connection timeout"`).
     - Terminal highlights the error in red text with timestamp and traceback.
     - "Start Training" button re-enables with label `"Retry Training"`.
  5. Click `"Retry Training"`.
- **Expected Results:**
  - Application does not crash, freeze, or throw unhandled white-screen errors.
  - Clear, human-readable error messages are surfaced to the operator.
  - Retry mechanism functions properly.

---

### TC-TRN-10: WebSocket Connection Drop & Reconnection Resilience
**Objective:** Verify application resilience if the network drops or the WebSocket disconnects mid-stream.

- **Preconditions:**
  - Training is running at ~50% progress.
- **Steps:**
  1. In DevTools Network tab, toggle throttling to **Offline**, or terminate the mock WebSocket server.
  2. Observe the terminal and status header:
     - Terminal appends `[WARN] Telemetry stream disconnected. Attempting reconnection...`.
     - Status indicator displays `"DISCONNECTED"` or `"RECONNECTING"`.
     - UI does not reset progress to 0% prematurely.
  3. In DevTools, toggle throttling back to **No throttling** (or restart the WebSocket server).
  4. Observe the socket behavior:
     - Client attempts automatic exponential backoff reconnection.
     - Once reconnected, terminal logs `[INFO] Telemetry stream re-established.`.
- **Expected Results:**
  - Network interruption is surfaced transparently without losing existing terminal history.
  - Automatic reconnection or a manual "Reconnect" action restores connectivity.

---

### TC-TRN-11: Theme Compatibility (Dark Mode vs Light Mode)
**Objective:** Ensure all training UI elements, especially terminal and progress bar, meet contrast standards in both themes.

- **Preconditions:**
  - Global theme toggle is available in topbar.
- **Steps:**
  1. Switch application to **Dark Mode** (`<html class="dark">`).
  2. Inspect `/training`:
     - Terminal background remains deep black/slate (`bg-gray-950` or `bg-gray-900`).
     - Terminal log text has high contrast (bright green `text-emerald-400`, cyan `text-cyan-300`, white `text-gray-100`, red `text-rose-400`).
     - Progress bar track (`bg-gray-800`) and fill (`bg-indigo-500` / `bg-emerald-500`) are distinct.
     - Metric cards use dark surface backgrounds (`dark:bg-gray-800 dark:border-gray-700`).
  3. Switch application to **Light Mode**.
  4. Inspect `/training`:
     - Terminal container maintains a dark code-editor theme or cleanly styled light-slate terminal with legible dark/colored monospaced text.
     - Progress bar track (`bg-gray-200`) and labels are crisp and readable.
- **Expected Results:**
  - All text meets WCAG AA 4.5:1 contrast standards across both themes.
  - No low-contrast grey-on-dark or dark-on-dark text artifacts.

---

### TC-TRN-12: Responsive Viewports & Layout Stability
**Objective:** Validate layout integrity on Desktop, Tablet, and Mobile screen sizes.

- **Preconditions:**
  - Browser responsive design mode open.
- **Steps:**
  1. Test at **Desktop** (1920x1080 and 1280x720):
     - Metric cards arrange in a 4-column or 2x2 grid.
     - Terminal window has comfortable vertical height (min `400px` - `500px`).
  2. Test at **Tablet** (768x1024):
     - Metric cards wrap into 2 columns.
     - Progress bar and terminal scale without clipping horizontal margins.
  3. Test at **Mobile** (375x667 and 412x915):
     - Metric cards stack vertically (1 column).
     - Terminal window maintains `max-h-[300px]` with internal scroll.
     - Log lines wrap or allow smooth horizontal scroll without breaking page width.
     - "Start Training" button spans full width (`w-full`) for easy touch accessibility.
- **Expected Results:**
  - Zero horizontal page overflow or layout breakage on mobile viewports.

---

## 8. Automated E2E Test Specification (Playwright Example)

For CI/CD and regression automation, the following Playwright test outlines the exact automated verification of the "Start Training" click, progress bar advance, and terminal auto-scroll:

```typescript
import { test, expect } from '@playwright/test';

test.describe('Phase 3 Stage 1: Training UI & Telemetry E2E', () => {
  test.beforeEach(async ({ page }) => {
    // Authenticate and navigate
    await page.goto('/login');
    await page.fill('input[type="email"]', 'test@test.com');
    await page.fill('input[type="password"]', 'test1234');
    await page.click('button[type="submit"]');
    await page.waitForURL('/');

    // Navigate to /training
    await page.goto('/training');
    await expect(page).toHaveURL('/training');
  });

  test('Start Training clicks, progress bar advances, and terminal auto-scrolls', async ({ page }) => {
    // 1. Verify initial Idle state
    const startButton = page.locator('button:has-text("Start Training")');
    const progressBar = page.locator('[role="progressbar"]');
    const terminal = page.locator('[data-testid="terminal-container"]');

    await expect(startButton).toBeVisible();
    await expect(startButton).toBeEnabled();
    await expect(progressBar).toHaveAttribute('aria-valuenow', '0');

    // 2. Click Start Training
    await startButton.click();

    // 3. Verify button transitions to disabled/loading
    await expect(startButton).toBeDisabled();

    // 4. Verify Progress Bar advances beyond 0%
    await expect(async () => {
      const val = await progressBar.getAttribute('aria-valuenow');
      expect(Number(val)).toBeGreaterThan(0);
    }).toPass({ timeout: 5000 });

    // 5. Verify Terminal receives logs and auto-scrolls to bottom
    await expect(async () => {
      const logLines = await terminal.locator('.terminal-line').count();
      expect(logLines).toBeGreaterThan(5);

      // Evaluate scroll position
      const scrollInfo = await terminal.evaluate((el) => ({
        scrollHeight: el.scrollHeight,
        clientHeight: el.clientHeight,
        scrollTop: el.scrollTop,
      }));

      // Verify scrollTop is pinned at or near the bottom
      const distanceToBottom = scrollInfo.scrollHeight - scrollInfo.clientHeight - scrollInfo.scrollTop;
      expect(distanceToBottom).toBeLessThanOrEqual(10);
    }).toPass({ timeout: 10000 });

    // 6. Verify Completion
    await expect(page.locator('text=Completed')).toBeVisible({ timeout: 30000 });
    await expect(progressBar).toHaveAttribute('aria-valuenow', '100');
  });
});
```

---

## 9. QA Sign-Off & Execution Checklist

| ID | Test Case Title | Target Area | Pass / Fail | Notes / Defects |
| :--- | :--- | :--- | :--- | :--- |
| **TC-TRN-01** | Navigation & Route Registration | Routing / Sidebar | [ ] | Verified `/training` route & auth |
| **TC-TRN-02** | Initial Page Layout & Idle State | UI Layout | [ ] | Button, 0% bar, idle HUD rendered |
| **TC-TRN-03** | "Start Training" Click & WS Handshake | WebSocket | [ ] | 101 status, disabled button spinner |
| **TC-TRN-04** | Real-Time Progress Bar Advancement | UI Animation | [ ] | Smooth width %, ARIA values |
| **TC-TRN-05** | Telemetry HUD & Metrics Sync | State Management | [ ] | Stage, source, epoch, loss sync |
| **TC-TRN-06** | Terminal Console Auto-Scrolling | DOM Scroll | [ ] | `scrollTop = scrollHeight` pinned |
| **TC-TRN-07** | Auto-Scroll User Override | UX Scroll Lock | [ ] | Pauses on scroll up, resumes at base |
| **TC-TRN-08** | Training Pipeline Normal Completion | Lifecycle | [ ] | 100% state, summary card, reset |
| **TC-TRN-09** | Error Handling & Failure Simulation | Error Boundary | [ ] | Red bar, traceback log, retry button |
| **TC-TRN-10** | WebSocket Disconnect & Reconnect | Network Resilience | [ ] | Graceful reconnect without state wipe|
| **TC-TRN-11** | Theme Compatibility (Dark & Light) | Accessibility / CSS | [ ] | WCAG AA contrast in terminal/cards |
| **TC-TRN-12** | Responsive Viewports & Layout | Mobile / Tablet | [ ] | No overflow, clean stacked layout |

---
*End of Test Plan: TP-FE-TRAINUI-001*
