---
status: accepted
---

# Reprocessing stays simple: append-only, versioned processed runs

Reprocessing historical raw data (to fix a bug in the validation/scoring code without needing anyone to resubmit anything) is supported, but deliberately kept simple for v1. Each successful pipeline run writes a new, timestamped set of rows into the processed/indices layer rather than updating existing ones; the dashboard always reads whichever run is marked current (e.g. via a `computed_at` timestamp or an explicit `is_current` flag). This gives a clear, versioned trail of exactly which run produced what's currently live, without building a general-purpose "replay all history from scratch on demand" tool — that can be built later, as a one-off script, if and when there's an actual reason to reprocess years of history at once. This depends on raw data actually being retained somewhere reprocessable — see [ADR-0016](0016-raw-data-lake-interim-storage.md) for where it currently lives.

**Consequence**: the processed layer becomes append-only too, so its storage grows with every refresh, not just the raw layer's — acceptable at this data volume (a few hundred rows per sector per district per refresh cycle).
