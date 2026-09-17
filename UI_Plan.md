**1. Coding Practices Reminder**
*Match the existing code structure and style already established in the project's earlier planning/build phases (Flask backend, React frontend). Don't introduce a new pattern, folder structure, state-management approach, or styling convention for this pass just because it's convenient — extend what's already there.*

***

**2. README Checklist (Part 15)**
After a deep review of `README_0_START_HERE.md` through `README_8_EXERCISES.md`, here are the specific UI elements called for by the documentation. Since the current UI only really implements the broken ML training option, almost all of these are missing and have been scheduled into Phase 15 of the plan, with their exact source cited.

| UI Element / Capability | Source | Status | Planned In |
| :--- | :--- | :--- | :--- |
| **Portfolio card list** sorted by confidence (direction). | `README_0` / `README_2` | Missing | Phase 15 |
| **Interactive candlestick charts** with prediction overlays. | `README_0` | Missing | Covered by Phase 12 |
| **Sentiment timelines** and **News feed** with FinBERT scores. | `README_0` | Missing | Phase 15 |
| **Full analysis view** with tabs for Sentiment, News, Reddit, Indicators, and History. | `README_2` | Missing | Phase 15 |
| **Search bar** (e.g., "find all articles mentioning 'interest rate'"). | `README_2` | Missing | Phase 15 |
| **Ticker configuration panel** to add specific subreddits to a ticker's tracking list. | `README_2` | Missing | Phase 15 |
| **Exported reports** (PDF, CSV, JSON, XML). | `README_1` | Missing | Covered by Phase 14 |
| **Admin paradigm demo console** (`/admin/paradigms`) with 25 tabs showing live paradigm demos. | `README_4` | Missing | Phase 15 |
| **Circuit breaker panel** (shows ML sidecar health and current circuit state). | `README_4` | Missing | Phase 15 |

*(Note: There were no conflicting definitions found between the READMEs. `README_0` and `README_2` are perfectly aligned on the progressive disclosure of the dashboard.)*

***

**3. Detailed Phased Plan (Part 17)**

*(Coding Practices Reminder: Match the existing Flask/React codebase style, structure, and patterns. No new conventions.)*

### **Phase 1: Fix What's Broken**
* **Stage 1.1: Fix ML Training Save Bug**
  * **Build:** Diagnose the backend/frontend disconnect preventing ML training configs/results from saving. Patch the route or Redux thunk.
  * **Test:** Perform a full save → reload → verify cycle to ensure data persists.
  * **Done When:** A training run can be saved and remains visible upon hard refresh.
* **Stage 1.2: Fix Dark Mode Toggle**
  * **Build:** Repair the state-management logic tied to the dark mode toggle in Settings.
  * **Test:** Toggle the switch on both desktop and mobile viewports.
  * **Done When:** The UI theme updates instantly across the app without throwing errors.

### **Phase 2: Global Navigation / Account Chrome**
* **Stage 2.1: Clean Up Settings**
  * **Build:** Rip the account/profile-editing field out of the Settings page.
  * **Test:** Verify Settings page still renders properly.
* **Stage 2.2: Persistent Account Icon**
  * **Build:** Add an account icon to the top-right persistent header of every page. Clicking it opens the account-details editor (migrated from Settings).
  * **Test:** Ensure the modal/drawer opens correctly and doesn't break mobile layout.
* **Stage 2.3: Global Dark Mode Switch**
  * **Build:** Move the fixed dark mode toggle to the persistent header next to the account icon.
  * **Test:** Toggle it from non-Settings pages to verify global state updates.
* **Stage 2.4: System-Status Badge**
  * **Build:** Add a green/yellow/red status badge in the header, rolling up infrastructure health.
  * **Test:** Mock degraded service states and verify the badge turns yellow/red.
* **Stage 2.5: Environment Indicator**
  * **Build:** Add a visible badge in the header showing the active environment/node config.
  * **Test:** Ensure text stays legible on both light and dark themes on mobile.

### **Phase 3: Training UI Features**
* **Stage 3.1: Live Progress Bar & Telemetry**
  * **Build:** Add a live progress bar. Add detailed, real-time telemetry (stage, current data source, step/epoch counters, current loss) streaming via WebSocket.
  * **Test:** Run a dummy training session and verify logs stream in real-time.
* **Stage 3.2: Simulate Trading Button & Backtest Viewer**
  * **Build:** Add a button to simulate trading over a specified time. Build a backtest results viewer showing equity curve, drawdown, and win rate.
  * **Test:** Ensure charts render correctly and fit mobile screens.
* **Stage 3.3: Data Source Selection**
  * **Build:** Let users select from previously saved data sources (RSS, Reddit) when building a run.
  * **Test:** Verify the payload correctly passes the selected sources to the backend.
* **Stage 3.4: Training History & Scheduler**
  * **Build:** Add a history/comparison view to compare metrics and rollback models. Add a cron-style recurring training scheduler.
  * **Test:** Schedule a run, and successfully trigger a rollback.
* **Stage 3.5: Paper-Trading P&L Tracker**
  * **Build:** Build a running profit/loss view across simulated trades over time.
  * **Test:** Validate the P&L math and graph rendering.

### **Phase 4: Data Ingestion Command Center**
* **Stage 4.1: Live Ingestion View**
  * **Build:** Add a sidebar item for a live view of all ingestion sources (RSS, insider, Reddit), showing recent activity.
  * **Test:** Ensure lists paginate or scroll cleanly on desktop/mobile.
* **Stage 4.2: Filtering & Error States**
  * **Build:** Add a filter/search box. Surface per-source error states (e.g., 403s, rate limits) with a visible "Retry" button.
  * **Test:** Mock a rate-limited API and click retry.

### **Phase 5: Ticker Tracking**
* **Stage 5.1: Ticker Selection & "Track All"**
  * **Build:** Add UI to pick specific tickers or "track all". If "track all" is clicked, show a severe resource-warning dialog.
  * **Test:** Verify the warning explicitly blocks the action until confirmed.
* **Stage 5.2: Watchlist**
  * **Build:** Add a lightweight watchlist for price/signal alerts without full ingestion overhead.
  * **Test:** Add and remove tickers from the watchlist on mobile.

### **Phase 6: Infrastructure Monitoring**
* **Stage 6.1: Metrics Tracking & History**
  * **Build:** Track node/service CPU temp, CPU usage, RAM, power, and storage. Provide historical trend charts.
  * **Test:** Simulate usage spikes and check chart updates.
* **Stage 6.2: Anomaly Annotation & Status Page**
  * **Build:** Annotate spikes with the likely responsible service. Build a dedicated `/status` page listing all services, their up/down state, and last check timestamp.
  * **Test:** Bring down a local service and ensure the status page reflects it.

### **Phase 7: Database Explorer**
* **Stage 7.1: Global DB Explorer**
  * **Build:** Build an explorer covering PostgreSQL, TimescaleDB, Valkey, ChromaDB, etc.
  * **Test:** Execute basic read queries on different DB types.
* **Stage 7.2: Neo4j & SQLite Specialist Views**
  * **Build:** Add a dedicated graph visualizer for Neo4j AuraDB. Add a dedicated viewer for local SQLite files.
  * **Test:** Ensure nodes/edges render in the Neo4j visualizer on desktop.

### **Phase 8: Storage Lifecycle**
* **Stage 8.1: Archival System & Forecast**
  * **Build:** Write backend logic to automatically compress older data when space is low. Add a "days until full" forecast metric to the UI.
  * **Test:** Force a low-storage state and verify compression triggers.
* **Stage 8.2: Transparent Decompression**
  * **Build:** Ensure long-window training requests automatically decompress archived data on demand without error.
  * **Test:** Train a model spanning archived date ranges.

### **Phase 9: Google Drive Offload + Retrieval**
* **Stage 9.1: Google Drive Integration**
  * **Build:** Build the auth flow, credentials storage, and upload/download client for Google Drive API.
  * **Test:** Successfully authenticate and upload a dummy file.
* **Stage 9.2: Cloud Archival & Hydration**
  * **Build:** Push compressed archives to Drive if the node remains full. Pull data back in batches on demand during full historical retraining without clogging local storage.
  * **Test:** Mock a full local drive, trigger Drive upload, then request a full retrain and monitor local disk IO.

### **Phase 10: Alerting and Notifications**
* **Stage 10.1: In-App Notifications & Preferences**
  * **Build:** Build toast/in-app notifications for node capacity, service downs, failed training, and ingestion errors. Build a preferences page to route alerts (in-app, muted, etc.).
  * **Test:** Trigger all four alert types and verify they respect preferences.
* **Stage 10.2: Discord Bot Hook & Guardrails**
  * **Build:** Flag the ingestion error notification logic to act as the hook point for the future Discord Bot phase. Add confirmation dialogs to all destructive actions.
  * **Test:** Attempt to delete a data source and confirm the dialog appears.

### **Phase 11: Command Palette**
* **Stage 11.1: Global Search & Shortcuts**
  * **Build:** Implement a Cmd+K command palette to jump to any section. Add keyboard shortcuts throughout the app and a `?` help overlay.
  * **Test:** Use shortcuts to navigate the app completely without a mouse.

### **Phase 12: Analytics and Model Insight**
* **Stage 12.1: Matrix, Sentiment & Calendar**
  * **Build:** Add a ticker correlation matrix, an aggregated sentiment score dashboard, and an earnings/economic calendar view.
  * **Test:** Verify visualizations scale cleanly to mobile.
* **Stage 12.2: Explainability & Lineage**
  * **Build:** Add feature-importance visualization for predictions. Add a data lineage viewer to trace predictions back to specific raw records.
  * **Test:** Trace a sample prediction down to a dummy Reddit post.
* **Stage 12.3: Chart Overhaul**
  * **Build:** Update the main ticker chart with an "all tickers" vs "single ticker" toggle. Let users overlay sentiment and insider trading on single tickers, toggling between scaled lines and event markers.
  * **Test:** Ensure rendering of multiple overlaid axes doesn't break mobile aspect ratios.

### **Phase 13: Admin and Operations**
* **Stage 13.1: Logs & Secrets Management**
  * **Build:** Add an application error log viewer. Add a UI to manage API keys/secrets securely.
  * **Test:** Add a fake API key and verify it persists and masks correctly.
* **Stage 13.2: Quotas, Costs & Audits**
  * **Build:** Add an API rate-limit dashboard, a cloud cost tracker for metered DBs, config backup/restore functionality, and a user action audit log.
  * **Test:** Run a config backup and verify the downloaded file payload.

### **Phase 14: Export and Onboarding**
* **Stage 14.1: Export/Reporting**
  * **Build:** Add CSV/PDF export functionality to all tables and charts.
  * **Test:** Export the backtest results and open the resulting PDF.
* **Stage 14.2: First-Run Tour**
  * **Build:** Implement an onboarding checklist / guided tour to show where everything lives.
  * **Test:** Run through the tour on a fresh browser session.

### **Phase 15: README Missing/Partial Items Completion**
* **Stage 15.1: Portfolio & Full Analysis View**
  * **Build:** Implement the portfolio card list sorted by confidence. Implement the full analysis view tabs (Sentiment, News, Reddit, Indicators, History).
  * **Test:** Ensure tab switching is fluid and non-blocking on mobile.
* **Stage 15.2: Ticker Configuration & Search**
  * **Build:** Add functionality to attach specific subreddits to a ticker via the config panel. Build the global text search bar for news/articles.
  * **Test:** Search for a known string and verify it returns correct raw records.
* **Stage 15.3: Admin Paradigm Console & Circuit Breaker**
  * **Build:** Build `/admin/paradigms` with 25 tabs. Build the Circuit breaker panel showing ML sidecar health.
  * **Test:** Verify admin routes are strictly protected.

***

**4. Final Coverage Matrix**

| Item # | Requirement Description | Phase.Stage |
| :--- | :--- | :--- |
| 1 | Diagnose/fix ML training save bug | 1.1 |
| 2 | Confirm fix with save → reload → verify | 1.1 |
| 3 | Fix dark mode toggle in Settings | 1.2 |
| 4 | Remove account editing from Settings | 2.1 |
| 5 | Add clickable account icon to persistent header | 2.2 |
| 6 | Move dark mode switch to persistent header | 2.3 |
| 7 | Add global system-status badge | 2.4 |
| 8 | Add environment indicator badge | 2.5 |
| 9 | Live progress bar for training | 3.1 |
| 10 | Button to simulate trading | 3.2 |
| 11 | Select saved data sources for training | 3.3 |
| 12 | Detailed, real-time training telemetry | 3.1 |
| 13 | Training run history/comparison & rollback | 3.4 |
| 14 | Training run scheduler | 3.4 |
| 15 | Backtest results viewer (equity curve, etc) | 3.2 |
| 16 | Paper-trading P&L tracker | 3.5 |
| 17 | Sidebar item for live data ingestion view | 4.1 |
| 18 | Filter and search box in data viewer | 4.2 |
| 19 | Per-source error states with retry action | 4.2 |
| 20 | UI to choose specific tickers or track all | 5.1 |
| 21 | "Track all" resource warning | 5.1 |
| 22 | Lighter-weight watchlist feature | 5.2 |
| 23 | Track per node/service metrics (CPU, RAM, etc) | 6.1 |
| 24 | Historical trend views/charts | 6.1 |
| 25 | Record usage spikes annotated with service | 6.2 |
| 26 | Monitor service reachability (up/down/degraded) | 6.2 |
| 27 | Dedicated /status-style health-check page | 6.2 |
| 28 | Database explorer covering every db | 7.1 |
| 29 | Dedicated Neo4j graph explorer | 7.2 |
| 30 | Dedicated SQLite viewer | 7.2 |
| 31 | Auto compress/archive older data on full storage | 8.1 |
| 32 | Decompress archived data on demand for training | 8.2 |
| 33 | Push compressed archives to Google Drive | 9.2 |
| 34 | Google Drive API access (auth, client, etc) | 9.1 |
| 35 | Hydrate GDrive data on demand w/o clogging disk | 9.2 |
| 36 | Storage forecast per node (days until full) | 8.1 |
| 37 | In-app notifications (downs, capacity, failures) | 10.1 |
| 38 | Discord bot dependency hook point flagged | 10.2 |
| 39 | Notification preferences page | 10.1 |
| 40 | Confirmation dialogs on destructive actions | 10.2 |
| 41 | Global command palette (Cmd+K) | 11.1 |
| 42 | Keyboard shortcuts + help overlay | 11.1 |
| 43 | Correlation matrix view between tickers | 12.1 |
| 44 | Sentiment score dashboard | 12.1 |
| 45 | Earnings/economic calendar view | 12.1 |
| 46 | Model explainability/feature-importance viewer | 12.2 |
| 47 | Data lineage viewer | 12.2 |
| 48 | Overhaul main dashboard's ticker chart | 12.3 |
| 49 | Toggle between all tickers and single ticker mode | 12.3 |
| 50 | Single-ticker overlay: sentiment & insider trading | 12.3 |
| 51 | Toggle overlay render (scaled line vs markers) | 12.3 |
| 52 | Application logs viewer | 13.1 |
| 53 | API key / secrets management UI | 13.1 |
| 54 | External API rate-limit/quota dashboard | 13.2 |
| 55 | Cloud cost tracker | 13.2 |
| 56 | Backup/restore for app config and settings | 13.2 |
| 57 | Audit log of user actions | 13.2 |
| 58 | Export/reporting (CSV/PDF) | 14.1 |
| 59 | Onboarding checklist / first-run tour | 14.2 |
| 60 | Cross-check plan against 8 READMEs | Part 2 / 15.1 - 15.3 |
