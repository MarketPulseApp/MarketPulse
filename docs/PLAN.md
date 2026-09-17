# Plan: Expose Swagger API Documentation

This document outlines the necessary steps to expose the FastAPI Swagger UI to Cloudflare and add a convenient link to it in the React frontend sidebar.

## 1. Backend Changes (`app/main.py`)

FastAPI's built-in Swagger UI requires the `root_path` to be explicitly set when running behind a reverse proxy (like Nginx/Cloudflare) under a specific path (e.g., `/api`). This ensures that the generated `openapi.json` correctly maps the endpoint URLs.

**Changes required in `app/main.py`:**
Locate the FastAPI app initialization (around line 75):
```python
app = FastAPI(title="MarketPulse API", version="0.1.0", lifespan=lifespan)
```
Modify it to include `root_path="/api"`:
```python
app = FastAPI(
    title="MarketPulse API",
    version="0.1.0",
    lifespan=lifespan,
    root_path="/api"
)
```
*(FastAPI enables `/docs` and `/redoc` by default, so no other changes are strictly necessary to enable Swagger).*

## 2. Frontend Changes (`web_dashboard/src/components/layout/Sidebar.tsx`)

To make the API documentation easily accessible, we will add a new link in the sidebar. Since the Swagger UI is served directly by the backend and isn't a React route, we should use a standard HTML `<a>` tag with `target="_blank"` rather than a React Router `<NavLink>`.

**Changes required in `web_dashboard/src/components/layout/Sidebar.tsx`:**
Import an appropriate icon (e.g., `BookOpen` or `Code`) from `lucide-react`:
```tsx
import { ..., BookOpen } from 'lucide-react';
```
Add the following block within the `<nav>` section (e.g., above the Settings or Admin Console links):
```tsx
<a
  href="/api/docs"
  target="_blank"
  rel="noopener noreferrer"
  className="flex items-center space-x-3 p-2 rounded-lg transition-colors text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700"
>
  <BookOpen size={20} />
  <span>API Documentation</span>
</a>
```

## 3. Deployment Steps

Once the code changes are committed, the following deployment steps should be taken:

1. **Deploy Backend:**
   - Pull the latest changes to the server.
   - Restart the FastAPI service (e.g., using `systemctl restart marketpulse-api` or restarting the relevant Docker container/pm2 process).
   - *Verification:* Navigate to `https://<your-domain>/api/docs` and confirm the Swagger UI loads and the endpoints can be tested successfully.

2. **Deploy Frontend:**
   - Build the updated React application (`npm run build` or `yarn build`).
   - Deploy the new build artifacts to your hosting provider (e.g., Cloudflare Pages, Vercel, Nginx static dir).
   - *Verification:* Open the dashboard, locate the new "API Documentation" link in the sidebar, click it, and ensure it opens the Swagger UI in a new tab.
