# 01 — Project scaffold

**What to build:** A working Python project that a developer can clone, create a virtual environment for, install dependencies, and run `pytest` successfully. This means a `pyproject.toml` (or `requirements.txt`) with the project's core dependencies declared, a directory layout for the scoring engine package and tests, and a test runner configuration so that `pytest` exits cleanly (even with zero real tests). The `.gitignore` should cover the virtual environment and common Python artifacts.

**Blocked by:** None — can start immediately.

**Status:** done

- [x] `pyproject.toml` exists with project metadata and core dependencies (at minimum: pandas, numpy, pytest)
- [x] Directory layout established for the scoring engine package, GRID3 client, data pipeline, dashboard app, synthetic data generator, and tests
- [x] `pytest` runs and exits cleanly from a fresh virtual environment install
- [x] `.gitignore` updated for venv, `__pycache__`, `.pytest_cache`, and other Python artifacts (already covered pre-existing; no change needed)
