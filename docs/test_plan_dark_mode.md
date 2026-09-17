# Dark Mode Toggle - Manual Verification Test Plan

**Document ID:** TP-FE-DARKMODE-001
**Feature:** Phase 1 Stage 2: Dark Mode Toggle
**Target Application:** MarketPulse Web Dashboard (`web_dashboard`)
**Role:** Test Engineer
**Status:** Ready for Execution

---

## 1. Overview & Objectives

This test plan outlines manual verification procedures for the dark mode toggle feature in the MarketPulse Web Dashboard. The primary objectives are to verify:
1. **Toggle Switch UI State & Accessibility:** Correct visual indicators, knob translation, and ARIA state transitions.
2. **Theme Application & Text Color Contrast:** Accurate application of Tailwind `dark` class to the document root, ensuring proper contrast and readability across text, headings, backgrounds, cards, and navigation elements.
3. **`localStorage` Persistence:** Reliable persistence of the theme setting across hard page reloads, cross-route navigation, and new browser tabs/sessions.
4. **Responsive / Viewport Compatibility:** Consistent behavior and visual integrity on desktop, tablet, and mobile viewports.

---

## 2. Test Environment & Prerequisites

- **URL:** `http://localhost:5173` (or configured dev/staging server)
- **Browsers Tested:** Chromium-based (Chrome/Edge), Firefox, Safari (or mobile emulation)
- **DevTools Open:** Console (to monitor errors) and Application/Storage tab (to inspect `localStorage` and DOM `<html>` element).
- **Authentication:** User logged in and able to access `/settings`.

---

## 3. Test Cases

### TC-DM-01: Toggle Switch Visual & ARIA State Verification
**Objective:** Confirm that the switch component in Settings reflects its toggled state visually and accessibly.

- **Preconditions:**
  - Navigate to `/settings`.
  - Initial theme is Light Mode.
- **Steps:**
  1. Inspect the toggle switch element located in the **Preferences > Dark Theme** section.
  2. Verify initial attributes:
     - Outer button background color is light gray (e.g. `bg-gray-200`).
     - Inner knob slider is positioned at origin (`translate-x-0`).
     - Accessibility attribute is `aria-checked="false"`.
  3. Click or tap the toggle switch.
  4. Observe the toggle switch animation and state change.
  5. Inspect attributes post-click:
     - Outer button background changes to active theme accent (e.g. `bg-blue-600` or `bg-indigo-600`).
     - Inner knob slider translates to the right (e.g. `translate-x-5`).
     - Accessibility attribute updates to `aria-checked="true"`.
  6. Click the toggle switch a second time to revert back to Light Mode.
- **Expected Results:**
  - Switch smoothly toggles between states without visual artifacts or delay.
  - `aria-checked` accurately reflects `"true"` when enabled and `"false"` when disabled.
  - Knob slides left/right smoothly with appropriate CSS transition timing.

---

### TC-DM-02: Text Colors, Backgrounds, and Visual Hierarchy
**Objective:** Verify that text, card surfaces, and UI elements adapt with proper contrast and readability in dark mode.

- **Preconditions:**
  - User is on `/settings`.
- **Steps:**
  1. Toggle Dark Mode to **ON**.
  2. Verify root element:
     - Ensure `<html class="dark">` has the `dark` class applied.
  3. Check text elements on the Settings page:
     - Primary page title ("Settings") switches from dark text (`text-gray-900` / `text-gray-800`) to light text (e.g. `text-white` / `text-gray-100`).
     - Section headings ("ML Trading Configuration", "User Profile", "Preferences") are clearly legible with light text.
     - Secondary/subtext descriptions (e.g. "Toggle dark mode for the dashboard.") change from `text-gray-500` to a legible subdued shade (e.g. `text-gray-400`).
  4. Check card containers and surfaces:
     - White card panels (`bg-white`) switch to dark theme background surfaces (e.g. `dark:bg-gray-800` or `dark:bg-slate-900`).
     - Card borders and divider lines switch to appropriate dark contrast tones (e.g. `dark:border-gray-700`).
  5. Check input fields and sliders:
     - Text inputs, sliders, and strategy selection cards remain distinct, legible, and usable.
     - Input text inside form fields remains clearly readable against input backgrounds.
  6. Navigate to other pages (e.g. `/`, `/paper-trading`, `/sentiment`, `/admin`):
     - Ensure topbar, sidebar, charts, and metrics cards correctly render light-on-dark styles.
     - Verify no unstyled "flash of white" or illegible dark-on-dark text occurs.
- **Expected Results:**
  - All text meets WCAG AA contrast ratios (minimum 4.5:1 for normal text).
  - No black text on dark background or white text on white background.
  - Theme changes apply immediately across all visible components without requiring a refresh.

---

### TC-DM-03: `localStorage` Persistence & Page Reload
**Objective:** Ensure that the user's theme selection persists across reloads and navigation.

- **Preconditions:**
  - User is on `/settings`.
  - Browser DevTools is open to **Application > Local Storage** (or **Storage > Local Storage**).
- **Steps:**
  1. Clear any existing `theme` key in `localStorage` or verify default state.
  2. Toggle Dark Mode to **ON**.
  3. Inspect `localStorage`:
     - Verify a key (e.g., `theme`) is stored with value `"dark"`.
  4. Perform a standard browser reload (`F5` or `Ctrl+R` / `Cmd+R`).
  5. Observe the initial page render:
     - Confirm the page reloads directly in Dark Mode without a flash of Light Mode (FOUC).
     - Confirm `<html class="dark">` retains the `dark` class.
     - Confirm the toggle button in `/settings` remains in the active ("true") state.
  6. Perform a hard refresh (`Ctrl+F5` or `Ctrl+Shift+R` / `Cmd+Shift+R`).
  7. Confirm dark mode remains active and all states hold.
  8. Navigate to a different route (e.g., `/`, `/paper-trading`) and back to `/settings`.
  9. Confirm the theme persists across client-side router transitions.
  10. Toggle Dark Mode to **OFF**.
  11. Check `localStorage`:
      - Verify key value updates to `"light"` (or is removed, per implementation).
  12. Reload the page and verify Light Mode persists.
- **Expected Results:**
  - Theme preference is immediately synchronized with `localStorage`.
  - Reloading the page respects the stored preference with zero theme flicker.
  - Router transitions preserve the active theme across the entire session.

---

### TC-DM-04: Multi-Tab & Session Continuity
**Objective:** Verify theme synchronization across browser tabs and fresh sessions.

- **Preconditions:**
  - Browser session active in Tab 1.
- **Steps:**
  1. In Tab 1, set theme to **Dark Mode**.
  2. Open a new browser tab (Tab 2) and navigate to `http://localhost:5173/settings`.
  3. Check the theme in Tab 2 upon initial load.
  4. In Tab 2, toggle Dark Mode to **OFF**.
  5. Switch back to Tab 1 and reload (or observe if cross-tab `storage` event listener is implemented).
- **Expected Results:**
  - New tabs open directly in the user's saved theme.
  - `localStorage` value is consistently read upon startup.

---

### TC-DM-05: Responsive & Mobile Viewport Verification
**Objective:** Confirm that the dark mode toggle and dark theme work seamlessly on mobile and small viewport screens.

- **Preconditions:**
  - DevTools device toolbar active (e.g., iPhone 12/14, Pixel 7, or custom 375px width).
- **Steps:**
  1. Open `/settings` on mobile viewport.
  2. Locate the Dark Theme toggle under Preferences.
  3. Ensure the toggle switch is fully visible, not cut off or overlapping surrounding elements.
  4. Tap the toggle switch to activate Dark Mode.
  5. Verify touch responsiveness (touch targets ≥ 44x44px or easily tappable).
  6. Open the mobile navigation drawer / hamburger menu.
  7. Check drawer background, icons, text, and active state styles in Dark Mode.
  8. Close drawer and scroll through Settings page to check for clipping, horizontal scrollbars, or styling glitches.
- **Expected Results:**
  - Mobile layout remains fully responsive and aligned.
  - Toggle switch responds promptly to touch/click interactions.
  - Mobile drawer and overlays respect the dark theme palette.

---

### TC-DM-06: Edge Cases & Error Resilience
**Objective:** Validate graceful degradation and fallback behavior.

- **Preconditions:**
  - Application loaded.
- **Steps:**
  1. **Corrupted/Invalid Storage:** Open DevTools console and set `localStorage.setItem('theme', 'invalid_value')`. Reload the page. Verify the app falls back safely to default (Light or System preference) without throwing runtime exceptions.
  2. **Rapid Toggling:** Click the toggle switch 10 times in rapid succession. Verify no race conditions occur, switch state matches DOM class, and `localStorage` retains the final state.
  3. **No Storage Available:** Simulate private browsing / blocked storage (if applicable). Verify the toggle still operates in-memory for the current session without crashing.
- **Expected Results:**
  - No unhandled exceptions in browser console.
  - App degrades gracefully to default theme upon unexpected storage values.

---

## 4. Verification Checklist & Sign-Off Criteria

| Criterion | Requirement | Verified (Y/N) |
| :--- | :--- | :---: |
| **Switch UI State** | Toggle background and knob change state accurately with smooth transition | [ ] |
| **Accessibility** | `role="switch"` and `aria-checked` accurately reflect active state | [ ] |
| **DOM Class** | `dark` class added to / removed from `document.documentElement` (`<html class="dark">`) | [ ] |
| **Text Contrast** | All text, headings, and descriptions remain legible (WCAG AA) | [ ] |
| **Surface Contrast** | Cards, inputs, modals, and navigation panels display appropriate dark backgrounds | [ ] |
| **Persistence** | Selection saved to `localStorage` and persists across soft and hard reloads | [ ] |
| **Routing** | Theme remains consistent during SPA client navigation | [ ] |
| **Mobile UX** | Layout, drawer, and touch targets work without visual breakage on mobile | [ ] |
| **Console Cleanliness** | Zero console errors or unhandled warnings during theme changes | [ ] |
