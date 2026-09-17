# Account Modal & Authentication Verification - Test Plan

**Document ID:** TP-FE-ACCTMODAL-001  
**Feature:** Phase 2 Stage 2: Persistent Account Icon & Account Modal  
**Target Application:** MarketPulse Web Dashboard (`web_dashboard/src/components/layout/Topbar.tsx`, `AccountModal.tsx`)  
**Role:** Test Engineer  
**Status:** Ready for Execution  

---

## 1. Overview & Objectives

Following the Phase 2 Stage 1 cleanup of the Settings page, user account information (Name, Email, Role) is transitioned into a persistent account component accessible globally from the topbar navigation. 

Per user requirement:
> *"Y. I would like you to make sure that it's actually pulling my account data"*

The primary objectives of this test plan are to verify:
1. **Account Data Retrieval:** Ensure that the application triggers an authenticated call to `/api/api/v1/auth/me` (or configured API proxy endpoint) with the active JWT Bearer token, returning and displaying the user's live email and profile attributes rather than hardcoded mock strings.
2. **Topbar Icon & Modal Interaction:** Verify that clicking the `UserCircle` icon in the Topbar opens the Account Modal/Dropdown, toggles it closed upon re-click, dismisses on backdrop/outside clicks, and closes when pressing the `Escape` key.
3. **Sign Out & JWT Token Flush:** Confirm that executing the "Sign Out" action inside the modal completely flushes the JWT access token from `localStorage`, terminates the authenticated session, closes the modal, and safely redirects the user to the `/login` screen.
4. **Resilience & State Management:** Validate behavior when the token is missing, expired, or corrupted (401 Unauthorized), verifying proper error handling and fallback states.
5. **Theme & Responsive Layout:** Verify visual consistency and readability across Light/Dark modes, mobile, tablet, and desktop viewports.

---

## 2. Test Environment & Prerequisites

- **Frontend URL:** `http://localhost:5173` (or active Vite development server)
- **Backend API Base:** `http://192.168.1.134:8080` (FastAPI backend proxied via `/api`)
- **Authentication Endpoints Under Test:**
  - `POST /api/api/v1/auth/login` (or `/auth/login`) - OAuth2 Token Login
  - `GET /api/api/v1/auth/me` (or `/auth/me`) - Authenticated User Profile
- **Test Credentials:**
  - Standard User: `test@test.com` / `test1234`
  - Secondary User (to verify dynamic email switching): `admin@marketpulse.local` / `securePass123`
- **Required Browser DevTools:**
  - **Network Tab:** Filter by `Fetch/XHR` to inspect headers, request payload, response status, and response bodies for `/auth/me`.
  - **Application/Storage Tab:** Inspect `Local Storage` -> `token` key.
  - **Console Tab:** Monitor for runtime errors, Axios interceptor logs, or unhandled promise rejections.

---

## 3. System Architecture & Data Flow

```
+-------------------------------------------------------------------------+
| Topbar (web_dashboard)                                                  |
|  [Logo] [Overview]                     [Bell] [UserCircle Icon (Click)] |
+-------------------------------------------------------------|-----------+
                                                              |
                                                    Toggles State (isOpen)
                                                              v
+-------------------------------------------------------------------------+
| AccountModal Component                                                  |
|                                                                         |
| 1. On Mount / Open:                                                     |
|    apiClient.get('/auth/me')                                            |
|    Headers: { Authorization: "Bearer <token>" }                         |
|                                                                         |
| 2. Backend (FastAPI router: /auth/me):                                  |
|    Validates JWT -> Returns User schema { id, email, role, is_active }  |
|                                                                         |
| 3. Render:                                                              |
|    - Email: actual user email (e.g. "test@test.com")                   |
|    - Role: "user" or "admin"                                            |
|                                                                         |
| 4. Sign Out Button Clicked:                                             |
|    localStorage.removeItem('token')                                     |
|    Redirect -> /login                                                   |
+-------------------------------------------------------------------------+
```

---

## 4. Test Cases

### TC-ACC-01: UserCircle Icon Rendering & Placement in Topbar
**Objective:** Confirm the `UserCircle` icon replaces or augments the legacy avatar and renders in the top-right navigation area.

- **Preconditions:**
  - User is authenticated and navigating any dashboard page (e.g., `/`, `/settings`, `/paper-trading`).
- **Steps:**
  1. Inspect the right side of the Topbar header.
  2. Locate the user account trigger element.
  3. Verify the presence of the `lucide-react` `UserCircle` (or designated user icon).
  4. Inspect the button attributes:
     - Must have accessible label/aria attributes (`aria-label="User Account"`, `aria-haspopup="dialog"` or `"menu"`).
     - Hover states provide visual feedback (`hover:bg-gray-100`, `dark:hover:bg-gray-700`).
  5. Check layout on viewport widths: Desktop (>=1024px), Tablet (768px - 1023px), and Mobile (<768px).
- **Expected Results:**
  - The icon is clearly visible, vertically centered in the 64px (`h-16`) Topbar.
  - Sizing is balanced with adjacent notification (`Bell`) and navigation icons.
  - Renders cleanly without clipping on mobile screens.

---

### TC-ACC-02: Modal Open/Close Toggle Interactions
**Objective:** Verify that clicking the `UserCircle` icon toggles the account modal and all dismissal mechanisms function properly.

- **Preconditions:**
  - Dashboard is loaded; modal is initially closed (`isOpen === false`).
- **Steps:**
  1. Click the `UserCircle` icon once.
     - Verify the Account Modal opens and appears anchored below the Topbar trigger or centered as a dialog.
  2. Click the `UserCircle` icon a second time.
     - Verify the modal closes immediately.
  3. Click the `UserCircle` icon to re-open the modal.
  4. Click anywhere outside the modal bounds (backdrop or dashboard background).
     - Verify the click-outside handler dismisses the modal.
  5. Click the `UserCircle` icon to open the modal again.
  6. Press the `Escape` key on the keyboard.
     - Verify the modal dismisses immediately.
  7. If an explicit close button (`X`) is provided inside the modal, click it and verify closure.
- **Expected Results:**
  - Modal toggles smoothly without UI jitter or flickering.
  - Dismissal triggers (re-click, outside click, ESC key, close button) reliably update state.
  - Focus returns to the trigger button upon closure for accessibility.

---

### TC-ACC-03: Real Account Data Fetching via `/api/api/v1/auth/me`
**Objective:** Verify that the modal actively queries `/api/api/v1/auth/me` and returns genuine account data for the logged-in user.

- **Preconditions:**
  - User logged in as `test@test.com` with a valid JWT token stored in `localStorage.getItem('token')`.
  - DevTools Network tab is open and recording network log.
- **Steps:**
  1. Click the `UserCircle` icon to trigger modal display.
  2. Inspect the Network tab:
     - Filter for `auth/me` or `/api/api/v1/auth/me`.
     - Verify an HTTP `GET` request was dispatched.
  3. Inspect the Request Headers:
     - Confirm header: `Authorization: Bearer <JWT_TOKEN_STRING>`.
  4. Inspect the Response:
     - Status code: `200 OK`.
     - Payload format:
       ```json
       {
         "id": "...",
         "email": "test@test.com",
         "role": "user",
         "is_active": true,
         "created_at": "...",
         "updated_at": "..."
       }
       ```
  5. Verify the payload email matches the active session (`test@test.com`).
  6. Log out, log in with an alternate account (e.g. `admin@marketpulse.local`), open the modal, and verify the network response returns `admin@marketpulse.local`.
- **Expected Results:**
  - Network request is dispatched with valid Bearer token credentials.
  - Response status is `200 OK`.
  - The email field dynamically reflects the authentic authenticated user rather than hardcoded mock strings (e.g. `"demo@example.com"` or `"Admin"`).

---

### TC-ACC-04: Account Modal UI Data Binding & Presentation
**Objective:** Verify that the data returned from `/auth/me` binds correctly to the modal UI elements.

- **Preconditions:**
  - Modal opened following successful `200 OK` response from `/auth/me`.
- **Steps:**
  1. Inspect the modal content:
     - Verify the Email field displays the exact string returned by the API (`test@test.com`).
     - Verify user Role/Status badge (e.g., "Active", "Role: User" or "Admin").
  2. Test loading state:
     - Simulate a throttled network connection (DevTools "Slow 3G").
     - Click the `UserCircle` icon.
     - Verify a loading skeleton or spinner appears while the `/auth/me` request is in-flight.
  3. Test error state:
     - Block request URL or simulate network failure.
     - Verify graceful error message (e.g., "Unable to load account details") with retry button or sign-out option.
- **Expected Results:**
  - Account information is rendered clearly with proper typography and alignment.
  - No undefined values (e.g., `undefined`, `NaN`, `[object Object]`) appear in the DOM.
  - Loading and error states provide clear, non-blocking user feedback.

---

### TC-ACC-05: Sign Out Execution & JWT Token Flush
**Objective:** Confirm that clicking the "Sign Out" button flushes the JWT token and terminates the session.

- **Preconditions:**
  - User is authenticated with `token` present in `localStorage`.
  - Account Modal is open.
- **Steps:**
  1. Inspect `localStorage` via DevTools Application tab:
     - Confirm `localStorage.getItem('token')` has a valid non-empty JWT string.
  2. Click the **Sign Out** (or **Log Out**) button inside the modal.
  3. Verify storage cleanup:
     - Inspect `localStorage`: Confirm `token` key is completely removed (`null`) or emptied.
  4. Verify application routing:
     - Confirm user is immediately redirected to `/login`.
  5. Verify modal state:
     - Ensure the modal is closed and removed from DOM.
  6. Attempt to navigate back via browser "Back" button:
     - Verify protected routes redirect immediately back to `/login`.
  7. Verify subsequent API calls:
     - Confirm no background requests are sent using the discarded token.
- **Expected Results:**
  - `localStorage.removeItem('token')` is successfully executed.
  - Stored token is completely eliminated.
  - Session is fully terminated and user is redirected to the `/login` route.

---

### TC-ACC-06: Session Expiry & 401 Unauthorized Resilience
**Objective:** Verify application behavior when opening the modal with an invalid, manipulated, or expired token.

- **Preconditions:**
  - User is on the dashboard.
- **Steps:**
  1. In DevTools Application tab, edit `localStorage.getItem('token')` to an invalid string: `"invalid_token_12345"`.
  2. Click the `UserCircle` icon to open the modal.
  3. Observe Network tab:
     - `GET /api/api/v1/auth/me` returns `401 Unauthorized` or `403 Forbidden`.
  4. Verify frontend handling:
     - Interceptor or modal catches the 401 response.
     - Clears the invalid token from `localStorage`.
     - Redirects user to `/login` with an informational message ("Session expired. Please log in again.").
- **Expected Results:**
  - Application does not crash or display an infinite loading state.
  - Expired/invalid tokens are automatically purged and user is prompted to re-authenticate.

---

### TC-ACC-07: Light & Dark Theme Continuity
**Objective:** Ensure the modal and its contents maintain WCAG AA contrast and match the application's design system in both themes.

- **Preconditions:**
  - Navigate to dashboard.
- **Steps:**
  1. Open Account Modal in Light Mode:
     - Inspect background (`bg-white`), borders (`border-gray-200`), primary text (`text-gray-900`), and secondary text (`text-gray-500`).
  2. Toggle Dark Mode ON via Settings or theme context.
  3. Open Account Modal in Dark Mode:
     - Inspect background (`dark:bg-gray-800`), borders (`dark:border-gray-700`), text (`dark:text-white`, `dark:text-gray-300`), and buttons (`hover:bg-gray-700`).
     - Check Sign Out button contrast (e.g., `text-red-500 hover:bg-red-50 dark:hover:bg-red-900/30`).
- **Expected Results:**
  - Full aesthetic parity with the dashboard design system.
  - Contrast ratios pass WCAG AA standards in both themes.

---

## 5. Automated / API Diagnostic Scripts

For rapid regression testing, the following automated scripts verify the backend `/auth/me` contract and token lifecycle.

### Python Backend Verification Script (`test_auth_me.py`)

```python
import asyncio
import httpx

API_BASE = "http://192.168.1.134:8080"

async def test_auth_me_pipeline():
    async with httpx.AsyncClient(base_url=API_BASE) as client:
        # Step 1: Authenticate
        login_res = await client.post(
            "/auth/login",
            data={"username": "test@test.com", "password": "test1234"}
        )
        assert login_res.status_code == 200, f"Login failed: {login_res.text}"
        token = login_res.json()["access_token"]
        print(f"[PASS] Token acquired: {token[:15]}...")

        # Step 2: Fetch Account Data via /auth/me
        headers = {"Authorization": f"Bearer {token}"}
        me_res = await client.get("/auth/me", headers=headers)
        assert me_res.status_code == 200, f"/auth/me failed: {me_res.text}"
        user_data = me_res.json()
        print(f"[PASS] /auth/me returned data: {user_data}")
        
        # Step 3: Validate Specific User Email
        assert user_data.get("email") == "test@test.com", "Email mismatch!"
        assert "id" in user_data, "Missing user ID"
        print(f"[PASS] Verified user email matches: {user_data['email']}")

        # Step 4: Validate Unauthorized Request Without Token
        unauth_res = await client.get("/auth/me")
        assert unauth_res.status_code == 401, f"Expected 401, got {unauth_res.status_code}"
        print("[PASS] Unauthenticated access properly rejected (401)")

if __name__ == "__main__":
    asyncio.run(test_auth_me_pipeline())
```

---

## 6. Verification Checklist

| Check ID | Verification Item | Target Standard | Status | Notes |
| :--- | :--- | :--- | :---: | :--- |
| **CHK-ACC-01** | `UserCircle` Topbar Icon | Rendered in top-right with accessible attributes | [ ] | Replaces/supplements static Admin text |
| **CHK-ACC-02** | Modal Toggle Open/Close | Opens on click, closes on re-click | [ ] | Smooth transition, no layout shift |
| **CHK-ACC-03** | Modal Dismissal Triggers | Closes on outside click, close button, and `Escape` key | [ ] | Focus restored to trigger |
| **CHK-ACC-04** | `/auth/me` API Invocation | Dispatches GET with `Authorization: Bearer <token>` | [ ] | Verify via DevTools Network tab |
| **CHK-ACC-05** | Real Email Binding | Displays live authenticated email (e.g. `test@test.com`) | [ ] | Zero mock/hardcoded email strings |
| **CHK-ACC-06** | Sign Out Token Flush | `localStorage.removeItem('token')` called | [ ] | `token` key is cleared immediately |
| **CHK-ACC-07** | Post-Signout Navigation | User redirected to `/login`; back button protected | [ ] | Session terminated completely |
| **CHK-ACC-08** | 401 Session Expiry | Invalid/expired token purges storage and redirects | [ ] | Graceful degradation, no crashes |
| **CHK-ACC-09** | Dark/Light Mode Styling | Theme classes applied, contrast WCAG AA compliant | [ ] | Tested on both light and dark |
| **CHK-ACC-10** | Mobile Responsiveness | Dropdown/modal adapts to viewports < 768px | [ ] | No horizontal overflow or clipping |

---

## 7. Sign-Off Criteria

Phase 2 Stage 2 Account Modal implementation is certified for production release when:
1. All checklist items (**CHK-ACC-01** through **CHK-ACC-10**) are marked as **PASSED**.
2. DevTools Network inspection confirms `/auth/me` returns `200 OK` with the exact email of the signed-in user.
3. Clicking **Sign Out** reliably clears the JWT token from `localStorage` and routes to `/login`.
4. Zero unhandled console exceptions or visual regressions are present across Chrome, Firefox, Edge, and mobile viewports.
