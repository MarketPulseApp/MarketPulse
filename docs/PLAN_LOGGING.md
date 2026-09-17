# Logging Implementation Plan for ML Trading Config

## Overview
The goal is to trace the exact request path, headers, and payload of the ML Trading config save request from the React frontend to the FastAPI backend. This is necessary to diagnose why the request fails when routed through a Cloudflare tunnel.

## Frontend Modifications (React)

### 1. `Settings.tsx`
- Add `console.log` statements before the API call to save the ML Trading config.
- Log the exact URL being called.
- Log the payload being sent.
- Log any error responses received.

### 2. `apiClient.ts`
- Add an interceptor or `console.log` statements in the request and response flow.
- Log the outgoing request method, URL, headers, and body.
- Log the incoming response status, headers, and body.

## Backend Modifications (FastAPI)

### 1. `main.py`
- Implement a logging middleware to capture all incoming requests.
- Log the request method, URL path, and query parameters.
- Log all headers, paying special attention to `x-forwarded-for`, `x-forwarded-proto`, and `host`.
- Log the request body (if possible and safe).
- Log the response status code.

### 2. `app/routers/settings.py`
- Add `logger.info` statements in the specific route handler for saving the ML Trading config (`/api/v1/settings/trading`).
- Log the received payload.
- Log any exceptions or validation errors before returning a 4xx or 5xx response.

## Execution Steps
1. Update `Settings.tsx` and `apiClient.ts` with frontend logging.
2. Update `main.py` to add global request logging middleware.
3. Update `app/routers/settings.py` to add route-specific logging.
4. Deploy/Restart services.
5. Attempt to save the ML Trading config via the Cloudflare tunnel.
6. Analyze the frontend console and backend logs to identify the point of failure.
