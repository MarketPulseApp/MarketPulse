# Global Topbar Theme Toggle & Settings Cleanup - Verification Test Plan

**Document ID:** TP-FE-GLOBALTHEME-001  
**Feature:** Phase 2 Stage 3: Global Dark Mode Switch  
**Target Application:** MarketPulse Web Dashboard (`web_dashboard`)  
**Components Under Test:** 
- `web_dashboard/src/components/layout/Topbar.tsx` (Global Theme Toggle)
- `web_dashboard/src/pages/Settings.tsx` (Legacy Preferences / Toggle Removal)
- `web_dashboard/src/ThemeContext.tsx` (Theme Provider & State Hook)
**Role:** Test Engineer  
**Status:** Ready for Execution  

---

## 1. Overview & Objectives

In Phase 2 Stage 3, the dark mode toggle is elevated from the localized Settings page into the global Topbar navigation header, positioned directly adjacent to the Account icon (`UserCircle`). Concurrently, the legacy "Preferences" section (containing the redundant dark theme toggle switch) is cleanly excised from `Settings.tsx`.

This test plan defines the end-to-end verification procedures to ensure:
1. **Instant Root Class Application:** Toggling the theme from the Topbar immediately adds or removes the `dark` class on the HTML document root (`<html class="dark">` / `document.documentElement.classList`) without delay, animation lag, or requiring a page reload.
2. **Settings Page Cleanup:** The `Settings.tsx` view no longer contains the old "Preferences" card, "Dark Theme" label, description text, or switch button, while all ML Trading Configuration controls remain fully functional.
3. **Global Accessibility & Persistence:** The theme toggle is accessible from any route via the persistent Topbar, and the user's preference is reliably stored in `localStorage` (`theme: 'dark' | 'light'`) and respected across client-side route transitions and browser hard reloads.
4. **Visual Hierarchy & Accessibility:** The toggle button integrates seamlessly into the Topbar layout across desktop, tablet, and mobile viewports with proper ARIA attributes, keyboard navigation, and WCAG AA contrast compliance.

---

## 2. Test Environment & Prerequisites

- **Frontend URL:** `http://localhost:5173` (or active Vite development server port)
- **Supported Browsers:** Chromium-based (Google Chrome, Microsoft Edge, Brave), Mozilla Firefox, WebKit (Apple Safari)
- **Screen Viewports:**
  - Desktop: 1440x900px, 1280x800px
  - Tablet: 768x1024px (iPad portrait / landscape)
  - Mobile: 375x812px (iPhone X/13), 390x844px (Pixel / Galaxy)
- **DevTools Open:**
  - **Elements / Inspector:** Monitor `<html class="...">` tag mutations in real time.
  - **Console Tab:** Verify absence of React warnings, syntax errors, or null reference errors.
  - **Application / Storage Tab:** Monitor `localStorage` key `theme`.
- **Prerequisites:** User is logged in with valid JWT token in `localStorage` (`token`) so that authenticated dashboard layouts and `Topbar` render.

---

## 3. System Architecture & State Flow

```
+---------------------------------------------------------------------------------------+
| Topbar.tsx                                                                            |
|  [Logo / Overview]              [ThemeToggle Button (Sun/Moon)]  [Bell]  [UserCircle] |
+---------------------------------------------------|-----------------------------------+
                                                    |
                                          onClick: toggleTheme()
                                                    |
                                                    v
+---------------------------------------------------------------------------------------+
| ThemeContext.tsx (useTheme Hook)                                                      |
|                                                                                       |
|  setIsDark(prev => !prev)                                                             |
|                                                                                       |
|  useEffect Trigger:                                                                   |
|    if (isDark) {                                                                      |
|      document.documentElement.classList.add('dark');                                  |
|      localStorage.setItem('theme', 'dark');                                           |
|    } else {                                                                           |
|      document.documentElement.classList.remove('dark');                               |
|      localStorage.setItem('theme', 'light');                                          |
|    }                                                                                  |
+---------------------------------------------------|-----------------------------------+
                                                    |
                         +--------------------------+--------------------------+
                         |                                                     |
                         v                                                     v
+-----------------------------------------------+     +---------------------------------+
| DOM Document Root                             |     | localStorage                    |
| <html class="dark"> (Instant Tailwind cascade)|     | key: "theme", value: "dark"     |
+-----------------------------------------------+     +---------------------------------+
```

### Settings Page Before vs. After (Phase 2 Stage 3)

```
BEFORE:
+-------------------------------------------------------+
| Settings.tsx                                          |
|  - [Card 1] ML Trading Configuration                  |
|  - [Card 2] Preferences (Dark Theme switch) <-- REMOVE|
+-------------------------------------------------------+

AFTER:
+-------------------------------------------------------+
| Settings.tsx                                          |
|  - [Card 1] ML Trading Configuration (Sole focus)     |
+-------------------------------------------------------+
```

---

## 4. Test Cases

### TC-GT-01: Global Topbar Theme Toggle Placement & Icon Rendering
**Objective:** Verify that the theme toggle button renders in the Topbar, adjacent to the Account icon, with proper visual indicators.

- **Preconditions:**
  - User logged in and navigating on any dashboard route (e.g. `/`, `/settings`, `/paper-trading`).
- **Steps:**
  1. Inspect the right side of the Topbar.
  2. Verify the layout order of navigation items in the top-right flex cluster:
     - Notification icon (`Bell`)
     - Theme Toggle button (Moon `Lucide` icon when in Light mode / Sun `Lucide` icon when in Dark mode)
     - User Account container (`UserCircle` + "Admin" badge)
  3. Inspect the toggle button element:
     - Button has accessible attributes: `aria-label="Toggle theme"` or `aria-label="Switch to dark mode"` / `"Switch to light mode"`.
     - Styling conforms to Topbar icon buttons (`p-2`, rounded hover effects `hover:bg-gray-100 dark:hover:bg-gray-700`).
  4. Hover over the button and observe feedback states.
- **Expected Results:**
  - The toggle button is clearly visible, vertically aligned within the 64px (`h-16`) Topbar.
  - Sizing is harmonious with adjacent icons (20px icon size, consistent padding).
  - Hover state provides smooth visual feedback with no layout shift.

---

### TC-GT-02: Instant Application of `dark` Class to Document Root (`<html>`)
**Objective:** Confirm that clicking the Topbar theme toggle immediately adds `dark` to `<html class="...">` without page refresh or latency.

- **Preconditions:**
  - Application is initially in **Light Mode** (`<html class="">` or `<html>` without `dark` class).
  - DevTools **Elements** panel open, focused on the `<html>` root tag.
- **Steps:**
  1. Observe the current class attribute of `document.documentElement`:
     ```js
     document.documentElement.classList.contains('dark'); // returns false
     ```
  2. Click the Topbar theme toggle button once.
  3. Immediately observe the `<html>` tag in DevTools Elements and evaluate via console:
     ```js
     document.documentElement.classList.contains('dark'); // must return true
     ```
  4. Verify the visual styling instantaneously transitions:
     - Topbar background transitions to `dark:bg-gray-800` and border to `dark:border-gray-700`.
     - Sidebar background transitions to `dark:bg-gray-800`.
     - Main layout background transitions to `dark:bg-gray-900` with text `dark:text-gray-100`.
     - Current page content (cards, tables, buttons) applies Tailwind dark styles.
  5. Click the Topbar theme toggle button a second time.
  6. Immediately observe the `<html>` tag:
     ```js
     document.documentElement.classList.contains('dark'); // must return false
     ```
  7. Verify all surfaces immediately revert to Light Mode styles (`bg-white`, `bg-gray-50`, `text-gray-800`).
- **Expected Results:**
  - The `dark` class is appended/removed synchronously with the state change.
  - Latency is under 16ms (within 1 browser frame).
  - Zero full-page reload or route re-mounting occurs.
  - No flickering or unstyled elements appear.

---

### TC-GT-03: Complete Removal of Old Toggle from `Settings.tsx`
**Objective:** Verify that the old Preferences card and dark mode toggle switch are completely eliminated from `Settings.tsx`.

- **Preconditions:**
  - Navigate to `/settings`.
- **Steps:**
  1. Visually review the entire Settings page layout from top to bottom.
  2. Verify that only the "ML Trading Configuration" card renders beneath the "Settings" page header.
  3. Inspect DOM elements:
     - Search DOM for heading text matching `"Preferences"`:
       ```js
       Array.from(document.querySelectorAll('h2, h3')).some(el => el.textContent?.includes('Preferences')); // must be false
       ```
     - Search DOM for label text matching `"Dark Theme"`:
       ```js
       Array.from(document.querySelectorAll('*')).some(el => el.textContent === 'Dark Theme'); // must be false
       ```
     - Search DOM for description text `"Toggle dark mode for the dashboard."`:
       ```js
       Array.from(document.querySelectorAll('*')).some(el => el.textContent?.includes('Toggle dark mode for the dashboard')); // must be false
       ```
     - Search DOM for role switch buttons:
       ```js
       document.querySelectorAll('button[role="switch"]').length; // must be 0
       ```
  4. Verify that `useTheme` is no longer imported or called unnecessarily inside `Settings.tsx` (unless explicitly needed for other settings).
  5. Check ML Trading Configuration functionality:
     - Click each strategy card (Zero-Loss Random Forest, Social Sentiment Scalper, Options Flow StatArb, Omni-Fusion Ensemble).
     - Move the Confidence Threshold slider.
     - Click "Save Configuration".
- **Expected Results:**
  - Zero remnant traces of the Preferences section or old theme switch in `Settings.tsx`.
  - No orphaned styling or blank whitespace containers at the bottom of `/settings`.
  - ML Trading Configuration operates without errors or console warnings.

---

### TC-GT-04: `localStorage` Synchronization & Page Reload Persistence
**Objective:** Verify that the theme setting persists in browser storage and initializes with zero Flash of Unstyled Content (FOUC).

- **Preconditions:**
  - User is on any page with DevTools **Application > Local Storage** open.
- **Steps:**
  1. In the console, execute `localStorage.clear()` or verify existing `theme` key.
  2. Click the Topbar theme toggle to activate **Dark Mode**.
  3. Inspect `localStorage`:
     - Key `theme` must equal `"dark"`.
  4. Perform a standard browser reload (`F5` or `Ctrl+R` / `Cmd+R`).
  5. Inspect the initial render:
     - Document root must immediately mount with `<html class="dark">`.
     - Page renders dark styling instantly with no light-mode flicker.
     - Topbar toggle icon displays the Sun icon (indicating active dark mode).
  6. Perform a hard reload (`Ctrl+Shift+R` / `Cmd+Shift+R`).
  7. Verify `<html class="dark">` and dark theme styling persist.
  8. Click the Topbar theme toggle to activate **Light Mode**.
  9. Inspect `localStorage`:
     - Key `theme` must equal `"light"`.
  10. Reload the page; verify Light Mode persists with zero flicker.
- **Expected Results:**
  - `localStorage` accurately tracks the active theme at all times.
  - Page reload immediately re-hydrates the saved theme without visual flashes.

---

### TC-GT-05: Cross-Route Navigation Consistency
**Objective:** Confirm that the active theme remains stable while navigating across different dashboard routes.

- **Preconditions:**
  - User is on Dashboard (`/`).
- **Steps:**
  1. Toggle theme to **Dark Mode** via the Topbar toggle.
  2. Using the Sidebar navigation, sequentially visit each route:
     - `/paper-trading`
     - `/settings`
     - `/admin`
     - `/sentiment`
     - `/macro`
     - `/analytics`
     - `/why`
  3. On each page, verify:
     - `<html class="dark">` remains present on the root.
     - The page body, cards, tables, charts, and text render with dark mode colors.
     - The Topbar toggle remains in the Sun (Dark Mode active) state.
  4. While on `/settings`, click the Topbar toggle to switch back to **Light Mode**.
  5. Verify `/settings` instantly switches to light mode.
  6. Navigate back to `/` and `/paper-trading`.
  7. Verify all pages remain in Light Mode.
- **Expected Results:**
  - Route changes preserve the active theme without resetting or glitching.
  - Topbar remains globally mounted and synchronized across client-side transitions.

---

### TC-GT-06: Accessibility, Keyboard Interaction, & Contrast
**Objective:** Ensure the Topbar toggle meets WCAG AA accessibility standards.

- **Preconditions:**
  - Navigate to any dashboard page.
- **Steps:**
  1. Use the `Tab` key on the keyboard to navigate through the Topbar controls.
  2. Verify that focus reaches the Theme Toggle button.
  3. Inspect visual focus indicator:
     - Must show clear focus ring (e.g. `focus:outline-none focus:ring-2 focus:ring-indigo-500` or `focus:ring-blue-500`).
  4. Press `Enter` or `Space`:
     - Theme must toggle instantly.
     - Focus must remain on the toggle button.
  5. Inspect screen reader accessibility:
     - Button must have an informative `aria-label` describing the action (e.g. `"Switch to dark mode"` / `"Switch to light mode"`).
  6. Perform contrast checks on text and icons against the Topbar background in both light (`#ffffff`) and dark (`#1f2937`) modes:
     - Text/icon contrast must be >= 4.5:1.
- **Expected Results:**
  - Full keyboard accessibility without requiring mouse input.
  - Clear focus indicator visible in both modes.
  - Screen reader accessible with accurate dynamic labels.

---

### TC-GT-07: Responsive & Mobile Viewport Compatibility
**Objective:** Verify that the Topbar theme toggle renders cleanly and operates responsively on mobile and tablet screens.

- **Preconditions:**
  - Open DevTools Device Mode (e.g. 375px width, iPhone SE / 13).
- **Steps:**
  1. Inspect the mobile Topbar layout:
     - Left: Hamburger menu button (`Menu`).
     - Right: Flex cluster containing Notification (`Bell`), Theme Toggle, and Account button (`UserCircle`).
  2. Verify that the Theme Toggle button remains visible, fully tappable, and is not hidden or obscured by text or borders.
  3. Tap the Theme Toggle button:
     - Verify instant touch response with minimal tap target of 40x40px (or padded 44x44px target area).
     - Theme toggles instantly to Dark Mode.
  4. Open the mobile sidebar drawer (`Menu` click):
     - Drawer renders dark background (`dark:bg-gray-800`) and dark theme navigation links.
  5. Close drawer and rotate screen to landscape (e.g. 667px / 844px width):
     - Ensure no layout wrapping, overlapping icons, or horizontal scrolling occurs.
- **Expected Results:**
  - Topbar items fit neatly without collision on screens down to 360px width.
  - Mobile touch target is responsive and easy to tap.

---

## 5. Automated / Console Verification Scripts

### Script 1: Browser DevTools Console Automated Test Runner
Run this snippet directly in the browser DevTools console on `http://localhost:5173/settings` to automatically validate DOM root class manipulation, `localStorage` synchronization, and absence of legacy toggle in Settings:

```javascript
(async function runGlobalThemeVerification() {
  console.group('%c[MarketPulse Test Suite] Phase 2 Stage 3: Global Theme Verification', 'color: #3b82f6; font-weight: bold; font-size: 14px;');
  
  const results = [];
  const assert = (name, condition, detail = '') => {
    const passed = Boolean(condition);
    results.push({ test: name, passed, detail });
    if (passed) {
      console.log(`%c[PASS]%c ${name}`, 'color: #10b981; font-weight: bold;', 'color: inherit;');
    } else {
      console.error(`%c[FAIL]%c ${name} - ${detail}`, 'color: #ef4444; font-weight: bold;', 'color: inherit;');
    }
  };

  // 1. Check Settings Page Cleanup
  const isSettingsPage = window.location.pathname.includes('/settings');
  if (isSettingsPage) {
    const prefHeaders = Array.from(document.querySelectorAll('h2, h3')).filter(el => el.textContent?.trim() === 'Preferences');
    assert('Settings: Preferences heading removed', prefHeaders.length === 0, `Found ${prefHeaders.length} elements`);

    const darkThemeLabels = Array.from(document.querySelectorAll('*')).filter(el => el.children.length === 0 && el.textContent?.trim() === 'Dark Theme');
    assert('Settings: "Dark Theme" label removed', darkThemeLabels.length === 0, `Found ${darkThemeLabels.length} elements`);

    const oldSwitches = document.querySelectorAll('.p-6 button[role="switch"]');
    assert('Settings: Old switch button removed', oldSwitches.length === 0, `Found ${oldSwitches.length} switch buttons`);

    const mlConfig = Array.from(document.querySelectorAll('h2')).some(el => el.textContent?.includes('ML Trading Configuration'));
    assert('Settings: ML Trading Configuration preserved', mlConfig, 'ML Trading Configuration card missing');
  } else {
    console.warn('Navigate to /settings to execute Settings cleanup assertions.');
  }

  // 2. Check Topbar Theme Toggle Button Existence
  const themeButtons = Array.from(document.querySelectorAll('header button, div[class*="h-16"] button')).filter(btn => {
    const aria = btn.getAttribute('aria-label') || '';
    const html = btn.innerHTML;
    return aria.toLowerCase().includes('theme') || html.includes('lucide-sun') || html.includes('lucide-moon') || btn.title?.toLowerCase().includes('theme');
  });
  assert('Topbar: Global theme toggle button present', themeButtons.length >= 1, `Found ${themeButtons.length} candidate buttons`);

  // 3. Root Class & LocalStorage Mutation Test
  const initialTheme = localStorage.getItem('theme') || 'light';
  const initialHasDark = document.documentElement.classList.contains('dark');
  
  // Test Toggle Action
  const toggleBtn = themeButtons[0];
  if (toggleBtn) {
    toggleBtn.click();
    await new Promise(r => setTimeout(r, 50)); // Allow microtask/render cycle
    const toggledHasDark = document.documentElement.classList.contains('dark');
    const toggledStorage = localStorage.getItem('theme');
    
    assert('Toggle: Root dark class flipped', toggledHasDark !== initialHasDark, `Previous: ${initialHasDark}, Now: ${toggledHasDark}`);
    assert('Toggle: localStorage updated', toggledStorage !== initialTheme, `Storage: ${toggledStorage}`);

    // Revert toggle
    toggleBtn.click();
    await new Promise(r => setTimeout(r, 50));
    const restoredHasDark = document.documentElement.classList.contains('dark');
    assert('Toggle: State restored on second click', restoredHasDark === initialHasDark, `Restored to: ${restoredHasDark}`);
  } else {
    assert('Toggle execution', false, 'Toggle button not found to simulate click');
  }

  console.table(results);
  console.groupEnd();
})();
```

---

### Script 2: Vitest / React Testing Library Unit Test Specification
Create or reference unit test specifications for `Topbar.test.tsx` and `Settings.test.tsx`:

```tsx
// web_dashboard/src/components/layout/__tests__/Topbar.test.tsx
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { Topbar } from '../Topbar';
import { ThemeProvider } from '../../../ThemeContext';

describe('Topbar Global Theme Toggle', () => {
  beforeEach(() => {
    localStorage.clear();
    document.documentElement.className = '';
  });

  it('renders the theme toggle button next to account controls', () => {
    render(
      <ThemeProvider>
        <Topbar />
      </ThemeProvider>
    );
    const themeBtn = screen.getByRole('button', { name: /theme|mode/i });
    expect(themeBtn).toBeInTheDocument();
  });

  it('instantly toggles dark class on document.documentElement upon click', () => {
    render(
      <ThemeProvider>
        <Topbar />
      </ThemeProvider>
    );
    const themeBtn = screen.getByRole('button', { name: /theme|mode/i });

    expect(document.documentElement.classList.contains('dark')).toBe(false);

    fireEvent.click(themeBtn);
    expect(document.documentElement.classList.contains('dark')).toBe(true);
    expect(localStorage.getItem('theme')).toBe('dark');

    fireEvent.click(themeBtn);
    expect(document.documentElement.classList.contains('dark')).toBe(false);
    expect(localStorage.getItem('theme')).toBe('light');
  });
});
```

```tsx
// web_dashboard/src/pages/__tests__/Settings.test.tsx
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { Settings } from '../Settings';
import { ThemeProvider } from '../../ThemeContext';

describe('Settings Page Legacy Toggle Removal', () => {
  it('renders ML Trading Configuration but does NOT render Preferences or Dark Theme toggle', () => {
    render(
      <ThemeProvider>
        <Settings />
      </ThemeProvider>
    );

    // Verify ML Trading Configuration is intact
    expect(screen.getByText('ML Trading Configuration')).toBeInTheDocument();

    // Verify Preferences and Dark Theme sections are absent
    expect(screen.queryByText('Preferences')).not.toBeInTheDocument();
    expect(screen.queryByText('Dark Theme')).not.toBeInTheDocument();
    expect(screen.queryByText('Toggle dark mode for the dashboard.')).not.toBeInTheDocument();
    expect(screen.queryByRole('switch')).not.toBeInTheDocument();
  });
});
```

---

## 6. Verification Matrix & Checklist

| Check ID | Verification Item | Target Component | Expected Result | Status | Notes |
| :--- | :--- | :--- | :--- | :---: | :--- |
| **CHK-GT-01** | Topbar Theme Button Rendering | `Topbar.tsx` | Button renders in Topbar header adjacent to Account icon (`UserCircle`) | [ ] | Check icon presence and alignment |
| **CHK-GT-02** | Topbar Dynamic Icon State | `Topbar.tsx` | Displays Moon icon in Light Mode, Sun icon in Dark Mode | [ ] | Visual confirmation of Lucide icon switch |
| **CHK-GT-03** | Instant HTML Root Class Toggle | `<html>` / DOM | `<html class="dark">` added/removed instantly on toggle click | [ ] | Zero delay or reload required |
| **CHK-GT-04** | Tailwind Dark Style Cascade | Dashboard Views | Card surfaces, text, sidebar, and navbar apply dark palette | [ ] | No light borders or text clipping |
| **CHK-GT-05** | Storage Persistence (`theme`) | `localStorage` | Value updates to `'dark'` or `'light'` immediately | [ ] | Inspect Application tab |
| **CHK-GT-06** | Hard Page Reload Persistence | `main.tsx` / Root | Hard refresh loads directly in active theme with zero FOUC | [ ] | Test `Ctrl+Shift+R` in both modes |
| **CHK-GT-07** | Cross-Route State Stability | Router / Layout | Theme remains consistent across navigation to `/settings`, `/`, etc. | [ ] | Test multiple routes in sequence |
| **CHK-GT-08** | "Preferences" Section Removed | `Settings.tsx` | No "Preferences" card header or section container in DOM | [ ] | Inspect `/settings` DOM |
| **CHK-GT-09** | "Dark Theme" Label & Switch Removed | `Settings.tsx` | No "Dark Theme" label, helper text, or `role="switch"` button | [ ] | Ensure 0 matches in DOM |
| **CHK-GT-10** | ML Trading Config Preservation | `Settings.tsx` | Strategy cards, threshold slider, and save button fully intact | [ ] | Verify slider and card selection work |
| **CHK-GT-11** | Keyboard Navigation & Focus Ring | `Topbar.tsx` | Accessible via `Tab`, toggles via `Enter`/`Space`, clear focus ring | [ ] | Test without mouse |
| **CHK-GT-12** | Mobile Viewport Integration | Mobile Topbar | Accessible and uncluttered on 375px screens with >=40px tap area | [ ] | Test in mobile emulation |

---

## 7. Sign-off & Success Criteria

The Phase 2 Stage 3 implementation is deemed **PASSED** and ready for production deployment when:
1. All 12 checks (**CHK-GT-01** through **CHK-GT-12**) in the Verification Matrix are verified and marked complete.
2. Clicking the Topbar theme toggle instantly alters the `dark` class on `<html class="...">` without console errors.
3. No remnants of the old theme switch exist in `Settings.tsx`.
4. The dashboard maintains consistent styling, persistence, and usability across reloads, navigation, and mobile viewports.
