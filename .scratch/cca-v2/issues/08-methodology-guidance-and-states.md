# 08 — Methodology, guidance, and empty/error/loading states

**What to build:** The trust-and-orientation layer that makes the dashboard
usable by a Ministry user who has never seen it, and honest when data is missing.
Split the v1 bottom-of-page FAQ: **general methodology** (how Sector Indices are
computed, how Supply/Access aggregate, why scores are relative, and the
"why isn't the national average 50?" explainer) moves behind a **Methodology link
in the header** that opens a drawer; **per-Indicator detail** stays contextual in
the Decomposition View. Add "guide just enough" affordances and explicit states.

**Blocked by:** 03 (shell), 06 (decomposition, for the contextual per-Indicator
detail).

**Status:** ready-for-agent

- [ ] A header "Methodology" link opens a drawer covering general methodology,
      including the average-≠-50 explanation and the no-composite-score rule
      (ADR-0002).
- [ ] Per-Indicator methodology (what it is, reference year, data source) is
      available contextually within the Decomposition View, not only in the
      Methodology drawer.
- [ ] A dynamic one-line subtitle reflects the current Sector and measure and
      states the colour direction/range.
- [ ] A single dismissible intro card appears on first visit (scan → rank →
      drill) and does not reappear once dismissed; no stepped guided tour.
- [ ] Explicit states: data-unavailable banner when the processed layer can't be
      read; a District with no score reads clearly as "No data" (map + list); a
      loading affordance shows while callbacks resolve.
- [ ] All labels use the domain glossary vocabulary (CONTEXT.md).
