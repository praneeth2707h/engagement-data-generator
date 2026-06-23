# Engagement Data Generator

A simulation platform for generating realistic pharmaceutical engagement data across multi-channel campaigns.

## What It Does

Upload a trigger file (list of users), configure your campaign settings, and generate a fully simulated engagement dataset — complete with journey progression, behavioral scoring, fatigue modelling, and an Excel workbook ready for analysis.

## Quick Start

### Run locally

1. Install Python 3.10 or later from https://python.org
2. Open a terminal in this folder and run:

```bash
pip install -r requirements.txt
streamlit run app.py
```

3. A browser window will open automatically at http://localhost:8501

### Run on Streamlit Cloud

See the deployment instructions in `PROJECT_RELEASE_PACKAGE.md`.

## How to Use

1. **Upload Files** — Upload your trigger file (CSV/Excel) and optionally a historical engagement file.
2. **Campaign Setup** — Enter campaign dates, ad journey, and target engagement rates.
3. **Business Rules** — Configure cooling periods, re-entry rules, and capacity caps.
4. **Run Simulation** — Click Run and watch the simulation execute.
5. **Results** — Download the Excel workbook with events, state, metrics, and validation.

## Input File Format

Your trigger file must be a CSV or Excel file with these columns:

| Column | Description |
|---|---|
| `Campaign_ID` | Campaign identifier |
| `User_ID` | Unique user identifier |
| `Trigger_Name` | Name of the trigger event |
| `Segment` | User segment label |

## Requirements

- Python 3.10+
- pandas, openpyxl, streamlit, numpy (installed automatically via `requirements.txt`)

## Running Tests

```bash
pip install pytest
pytest tests/
```

Expected: **1,111 tests pass, 0 failures.**

## Version

1.0.0 — Certified 2026-06-23
