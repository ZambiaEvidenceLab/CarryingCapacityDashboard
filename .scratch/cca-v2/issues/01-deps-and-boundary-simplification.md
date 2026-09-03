# 01 — Dependencies and build-time boundary simplification

**What to build:** The foundation for the "make it QUICK" map. Add the two new
libraries the v2 dashboard needs, and introduce a build/refresh-time step that
produces a **simplified** GRID3 district-boundary set so the dashboard loads a
few hundred KB of geometry instead of the current ~32.9 MB / ~847k-vertex full
resolution (ADR-0017, lever 1). After this ticket the dashboard still looks like
v1, but the boundaries it serves are light.

**Blocked by:** None — can start immediately.

**Status:** ready-for-agent

- [ ] `dash-mantine-components` and `shapely` are added to `pyproject.toml` and
      install cleanly on the project's Python (3.11+).
- [ ] A simplification step (topology-preserving, ~1–2% tolerance) runs where the
      GRID3 boundaries are cached at data-refresh time — never at page load
      (consistent with ADR-0010 and ADR-0006). It emits a simplified boundary set
      keyed by `district_code`, retaining all 116 Districts.
- [ ] The simplified set is on the order of ~15k total vertices / low-hundreds-KB
      (the prototype achieved 512 KB / 13k vertices at 0.005° tolerance — see
      `.scratch/cca-v2/prototype/prep_data.py`).
- [ ] The dashboard loads the simplified boundaries; the existing v1 map still
      renders all 116 Districts correctly.
- [ ] District identity, names, and provinces are unchanged — only vertex density
      drops.
