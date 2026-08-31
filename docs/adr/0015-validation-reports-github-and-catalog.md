---
status: accepted
---

# Validation results are recorded in both GitHub and the Postgres catalog

Each validation pipeline run ([ADR-0012](0012-database-gated-data-publish-pipeline.md)) produces a pass/fail result and the [ADR-0008](0008-winsorize-before-minmax.md) distribution/winsorization report. Relying on GitHub Actions' own log retention isn't enough — logs expire (commonly 90 days), and the report exists specifically to answer "why was this submission accepted or rejected," indefinitely.

The report is recorded in two places: committed to the GitHub repository as a versioned result (not just an ephemeral workflow log or artifact), and summarised/referenced from the Postgres catalog entry for that submission — so the catalog, which the audit trail ultimately points back to, doesn't require cross-referencing GitHub to know why a submission has the status it has.
