"""Static + catalog-driven content for the Methodology FAQ.

Two levels, per the spec: general methodology (static, doesn't depend on the
database) and per-indicator detail (driven by `metadata.indicator_definitions`
via `cca.storage.io.read_indicator_catalog`).
"""

from __future__ import annotations

import pandas as pd

GENERAL_FAQ: list[tuple[str, str]] = [
    (
        "How is a Sector Index calculated?",
        "Each Indicator is winsorised at the 1st/99th percentile, oriented so higher "
        "always means more capacity, then min-max normalised to 0-100 across all 116 "
        "districts. Indicators are averaged (equal weight) within a Dimension, and "
        "Dimensions are averaged within a Sector to produce the Sector Index.",
    ),
    (
        "How do Supply and Access combine?",
        "For Health, Education, Agriculture, and Infrastructure, the Sector Index is "
        "the equal-weighted average of its Supply Dimension score and its Access "
        "Dimension score. Environment has no Dimensions — its Indicators average "
        "directly into the Sector Index.",
    ),
    (
        "Why are scores relative rather than fixed benchmarks?",
        "Indicators are normalised against the current 116-district cohort, not "
        "against an externally set target, so a score reflects a district's standing "
        "relative to the rest of Zambia today rather than an absolute pass/fail line.",
    ),
    (
        "Why do some districts show a data-completeness flag?",
        "When one or more Indicators are missing for a district in a given Dimension "
        "or Sector, the missing ones are dropped and the remainder re-averaged — not "
        "imputed. The completeness flag marks any score computed this way, so it can "
        "be treated with appropriate caution.",
    ),
    (
        "Why do urban districts show a note on their Agriculture score?",
        "Mostly-urban districts (e.g. Lusaka, Ndola) naturally score lower on "
        "Agriculture Indicators because of urban land use, not a failure of "
        "agricultural capacity — the annotation exists to prevent that misreading.",
    ),
    (
        "Why does an Indicator's value show a reference year?",
        "Indicators refresh on different cycles, so a Snapshot can mix reference "
        "years within the same Sector Index. Each Indicator's own reference year is "
        "shown alongside its value so it's clear how current that figure is.",
    ),
]


def build_indicator_faq_rows(indicator_catalog: pd.DataFrame) -> list[dict]:
    """Per-indicator rows for the FAQ's data-source table, grouped by Sector/Dimension."""
    if indicator_catalog.empty:
        return []
    ordered = indicator_catalog.sort_values(
        ["sector", "dimension", "indicator_id"], na_position="first"
    )
    return ordered.to_dict("records")
