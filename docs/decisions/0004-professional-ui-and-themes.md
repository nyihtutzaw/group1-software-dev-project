# 0004 — A plainer, professional visual style with light and dark themes

**Date:** 2026-11-02 · **Status:** Accepted

## Context

The first UI kit copied the mock-up's editorial look: serif page titles, mono uppercase labels and
section headings, borderless form controls and a tinted grey page. It read more like a magazine than
a registry tool, and dark mode followed the system with no way to switch.

## Decision

- **The mock-up sets structure and content; the UI kit sets the look.** Pages keep the mock-up's
  screens, sections, labels and states, but are drawn with the restyled kit.
- **Light theme:** white page and surfaces, neutral grey lines and text, the CRVR teal (`--accent`)
  as the theme colour for primary buttons, the active menu item, links and focus rings.
- **Dark theme:** neutral dark surfaces with a brighter teal accent. Same token names, so components
  need no changes.
- **Type:** Inter for the interface and JetBrains Mono for codes, serials and hashes only. No serif;
  no uppercase mono labels.
- **Forms:** a label above a bordered control with an accent focus ring.
- **Shell:** sidebar with brand, menu and the signed-in user; a top bar with a breadcrumb, the theme
  toggle, notifications, the user and sign out.
- **Theme switch:** follows the system until the user picks one with the toggle (sun/moon in the top
  bar and on the sign-in page). The choice is stored in `localStorage` (`crvr-theme`) and applied
  by a small script in `index.html` before the first paint, so there is no flash.

## Consequences

- All features change look at once, because they already used the kit and tokens. Pages that build
  their own rows still only need tokens (`bg-surface`, `text-faint`, `border-line`, …).
- New colours still go in `src/index.css` as tokens, defined for both themes.
- `src/lib/theme.ts` (`useTheme`) and `src/layout/ThemeToggle.tsx` own the theme switch.
