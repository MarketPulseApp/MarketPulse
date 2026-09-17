# Settings Page Cleanup - Verification Test Plan

**Document ID:** TP-FE-SETTINGS-001  
**Feature:** Phase 2 Stage 1: Clean Up Settings  
**Target Application:** MarketPulse Web Dashboard (`web_dashboard/src/pages/Settings.tsx`)  
**Role:** Test Engineer  
**Status:** Ready for Execution  

---

## 1. Overview & Objectives

In Phase 2 Stage 1, the Settings page is streamlined to focus solely on application configuration. Account-specific fields ("User Profile" containing Name and Email) are removed, leaving profile management for a dedicated view in the future.

The objective of this test plan is to verify that:
1. **Profile Fields Removal:** The "User Profile" card, including Name and Email input fields and associated labels/values, is completely removed from the page DOM and visual layout.
2. **ML Trading Configuration Card Preservation:** The ML strategy selector cards, confidence threshold slider, and save actions continue to render and function as expected.
3. **Preferences Card Preservation:** The appearance preferences card (Dark Theme toggle switch) continues to render and function with proper state toggling and styling.
4. **Layout & Visual Hierarchy:** The vertical rhythm, spacing, and responsive layout remain clean, balanced, and free of orphan elements or layout gaps in both light and dark modes.

---

## 2. Test Environment & Prerequisites

- **Application URL:** `http://localhost:5173/settings` (or current dev server port)
- **Browsers:** Chromium (Chrome / Edge), Firefox, WebKit / Safari
- **Tools:** Browser Developer Tools (Elements inspector, Console, Network tab)
- **Prerequisites:** Web dashboard running, user authenticated / navigating to `/settings`.

---

## 3. Test Cases

### TC-SET-01: Absence of Name and Email (Profile Cleanup)
**Objective:** Ensure the User Profile section and its inputs are completely absent.

- **Preconditions:**
  - Navigate to `/settings`.
- **Steps:**
  1. Inspect the visual layout of the page.
  2. Search DOM/inspect elements for headings matching `"User Profile"`.
  3. Search DOM for inputs containing values `"Demo User"` or `"demo@example.com"`.
  4. Search DOM for labels matching `"Name"` or `"Email"`.
  5. Check browser developer console for any undefined references, warnings, or errors.
- **Expected Results:**
  - No "User Profile" heading or section card is rendered.
  - No input fields for "Name" or "Email" exist in the DOM or accessibility tree.
  - Page console shows zero errors or unhandled exceptions related to missing profile data.

---

### TC-SET-02: ML Trading Configuration Card Rendering & Functionality
**Objective:** Confirm the ML Trading Configuration card remains fully intact and functional.

- **Preconditions:**
  - Navigate to `/settings`.
- **Steps:**
  1. Verify the "ML Trading Configuration" card header and card surface render correctly.
  2. Verify all configured strategies render in the grid:
     - Zero-Loss Random Forest
     - Social Sentiment Scalper
     - Options Flow StatArb
     - Omni-Fusion Ensemble
  3. Click to select different strategy cards; confirm active border (`border-blue-500`) and checkmark badge toggle appropriately.
  4. Inspect the Confidence Threshold slider and percentage display badge (e.g. `99.9%`).
  5. Drag or adjust the slider and verify the displayed percentage updates in real-time.
  6. Click "Save Configuration" and verify the save network request (`PUT /api/api/v1/settings/trading`) and status feedback indicator.
- **Expected Results:**
  - Card displays with proper padding, typography, and contrast.
  - Strategy selection and slider adjustments are responsive and maintain state.
  - Save operation triggers and provides user feedback without issue.

---

### TC-SET-03: Preferences Card Rendering & Functionality
**Objective:** Confirm the Preferences card (Appearance / Theme toggle) renders and operates properly.

- **Preconditions:**
  - Navigate to `/settings`.
- **Steps:**
  1. Verify the "Preferences" card header renders below the ML Trading Configuration card.
  2. Verify the "Dark Theme" label and description ("Toggle dark mode for the dashboard.") are visible.
  3. Verify the toggle switch component is present with proper accessibility role (`role="switch"`).
  4. Click the toggle switch to enable Dark Theme:
     - Observe background transitions and knob slide animation (`translate-x-5`).
     - Confirm `aria-checked="true"`.
     - Confirm `dark` class is toggled on the document root (`<html>`).
  5. Click the toggle switch again to return to Light Theme:
     - Confirm knob returns to `translate-x-0` and `aria-checked="false"`.
- **Expected Results:**
  - Preferences card renders smoothly with no visual regressions.
  - Theme toggle correctly switches between Light and Dark modes.

---

### TC-SET-04: Responsive Layout & Visual Hierarchy
**Objective:** Ensure card spacing and page aesthetics remain balanced without the profile card.

- **Preconditions:**
  - Navigate to `/settings`.
- **Steps:**
  1. View page on desktop viewport (>= 1024px). Verify spacing between page title, ML Trading Configuration card, and Preferences card.
  2. Resize viewport to tablet (768px - 1023px) and mobile (< 768px).
  3. Verify card margins, padding, and vertical stacking (`space-y-6`).
  4. Check both Light Mode and Dark Mode aesthetics.
- **Expected Results:**
  - Cards stack cleanly with uniform spacing.
  - No awkward gaps, layout shifts, or horizontal scrollbars occur across viewport sizes.

---

## 4. Verification Checklist

| Check ID | Verification Item | Status | Notes |
| :--- | :--- | :---: | :--- |
| **CHK-01** | "User Profile" card removed | [ ] | Verify card container is absent |
| **CHK-02** | "Name" input & label removed | [ ] | Ensure no input or label in DOM |
| **CHK-03** | "Email" input & label removed | [ ] | Ensure no input or label in DOM |
| **CHK-04** | ML Trading Configuration card intact | [ ] | Strategy selection & threshold functional |
| **CHK-05** | Preferences card intact | [ ] | Dark theme toggle switch functional |
| **CHK-06** | Responsive layout & styling clean | [ ] | Consistent padding/spacing, zero console errors |

---

## 5. Sign-Off Criteria

The Stage 1 Settings cleanup is considered verified and ready for release when all checklist items (**CHK-01** through **CHK-06**) pass with zero console errors and no visual regressions in both light and dark themes.
