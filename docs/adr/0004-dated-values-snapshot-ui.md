---
status: accepted
---

# Store dated indicator values; dashboard v1 shows latest snapshot only

The database schema stores each Indicator value with an effective date/period from the start, even though the v1 dashboard only ever displays the latest Snapshot and has no year selector or trend view. Indicators update at different times of year across ministries, so the schema needs a time dimension regardless of what the UI shows today. Retrofitting a date column onto an already-populated production table is expensive and risky; adding it now costs nothing and keeps a future "choose a year" feature (already anticipated) to a UI-only change, not a schema migration.

This date is not purely stored-for-later, either: because a district's Sector Index can mix Indicators from different reference years (e.g. a 2024 health figure alongside a 2025 agriculture figure), v1 surfaces each Indicator's own reference year/period next to its value wherever it's shown, so users aren't misled into thinking every number on screen is equally current.
