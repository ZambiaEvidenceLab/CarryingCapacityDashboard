# 08 — Methodology, guidance, and empty/error/loading states

**What to build:** The trust-and-orientation layer that makes the dashboard
usable by a Ministry user who has never seen it, and honest when data is missing.
Split the v1 bottom-of-page FAQ: **general methodology** (how Sector Indices are
computed, how Supply/Access aggregate, why scores are relative, and the
"why isn't the national average 50?" explainer) moves behind a **Methodology link
in the header** that opens a drawer; **per-Indicator detail** stays contextual in
the Decomposition View. Add "guide just enough" affordances and explicit states.

**Reuse from the prototype** (`.scratch/cca-v2/prototype/app.py`): the
`methodology-drawer` content (including the "On the numbers" average-≠-50
explainer) and `subtitle_text`. The first-run card, empty/error/loading states,
and the header-link wiring are new work.

**Blocked by:** 03 (shell), 06 (decomposition, for the contextual per-Indicator
detail).

**Status:** done

- [x] A header "Methodology" link opens a drawer covering general methodology,
      including the average-≠-50 explanation and the no-composite-score rule
      (ADR-0002).
- [x] Per-Indicator methodology (what it is, reference year, data source) is
      available contextually within the Decomposition View, not only in the
      Methodology drawer.
- [x] A dynamic one-line subtitle reflects the current Sector and measure and
      states the colour direction/range.
- [x] A single dismissible intro card appears on first visit (scan → rank →
      drill) and does not reappear once dismissed; no stepped guided tour.
- [x] Explicit states: data-unavailable banner when the processed layer can't be
      read; a District with no score reads clearly as "No data" (map + list); a
      loading affordance shows while callbacks resolve.
- [x] All labels use the domain glossary vocabulary (CONTEXT.md).
