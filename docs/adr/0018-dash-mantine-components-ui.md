---
status: accepted
---

# dash-mantine-components as the dashboard UI component library

The v1 dashboard was built from raw Dash `html`/`dcc` primitives with no component library, which made a professional, dense, Ministry-facing layout expensive to hand-build and easy to make look amateur. v2 adopts **dash-mantine-components (DMC)** for layout and controls, on top of the Dash framework already chosen in [ADR-0005](0005-dash-dashboard-framework.md).

DMC was chosen over the two realistic alternatives — dash-bootstrap-components (DBC) and hand-rolled CSS. Its layout primitives (`AppShell`, `Grid`, `Drawer`, `SegmentedControl`, `Tabs`, `Paper`) map directly onto the v2 interaction model, where the national scan stays on screen and per-district detail slides in over it rather than pushing the page down. It looks contemporary and credible in front of MoFNP without a dedicated designer, and it ships light/dark theming and sensible density defaults out of the box. DBC remains the fallback if the team later prefers the more ubiquitous Bootstrap grid.

Trade-off accepted: DMC is a real dependency with its own release cadence and a larger API surface than plain Dash, and pinning it couples the UI to Mantine's major versions. That cost is justified by the volume of bespoke layout and styling code it removes, and it stays within the "keep the code readable and easy to maintain" goal better than hand CSS would. The scoring engine, pipeline, and Postgres layers are untouched — this is a presentation-layer decision only.
