"""Shared collision-avoidance for files this pipeline writes once and never overwrites (ADR-0015, ADR-0016)."""

from __future__ import annotations

from pathlib import Path


def next_available_path(directory: Path, stem: str, suffix: str) -> Path:
    """The first `directory/stem<suffix>`, or `directory/stem-2<suffix>`, `-3`, ... that doesn't already exist."""
    candidate = directory / f"{stem}{suffix}"
    counter = 2
    while candidate.exists():
        candidate = directory / f"{stem}-{counter}{suffix}"
        counter += 1
    return candidate
