# Project Release Package

**Product:** PharmaForce IQ — Engagement Data Generator
**Version:** 1.0.0
**Release Date:** 2026-06-23
**Status:** CERTIFIED — Ready for GitHub → Streamlit Deployment

---

## 1. Final Repository Structure

The repository contains one top-level application folder. Everything needed to run, test, and deploy the application lives inside it.

```
engagement_data_generator/         ← root of the GitHub repository
│
├── app.py                         ← Streamlit entry point
├── requirements.txt               ← Python dependencies
├── .gitignore                     ← Git exclusion rules
├── README.md                      ← User-facing documentation
│
├── core/                          ← Simulation pipeline (production code)
├── models/                        ← Data models and config schemas
├── utils/                         ← Shared utilities
├── ui/                            ← Streamlit page components
└── tests/                         ← Full test suite (1,111 tests)
```

---

## 2. Exact Folder Tree

```
engagement_data_generator/
│
├── app.py
├── requirements.txt
├── .gitignore
├── README.md
│
├── core/
│   ├── __init__.py
│   ├── audience_manager.py
│   ├── behavior_engine.py
│   ├── config_loader.py
│   ├── engagement_generator.py
│   ├── excel_exporter.py
│   ├── input_loader.py
│   ├── journey_engine.py
│   ├── simulation_orchestrator.py
│   ├── user_state_manager.py
│   └── validation_engine.py
│
├── models/
│   ├── __init__.py
│   ├── ad_config.py
│   ├── capacity_row.py
│   ├── channel_config.py
│   ├── config_registry.py
│   ├── enums.py
│   ├── rule_config.py
│   ├── segment_config.py
│   ├── simulation_result.py
│   ├── trigger_config.py
│   └── user_state.py
│
├── utils/
│   ├── __init__.py
│   ├── constants.py
│   ├── date_utils.py
│   ├── excel_utils.py
│   ├── exceptions.py
│   ├── logger.py
│   ├── schema_validator.py
│   └── version.py
│
├── ui/
│   ├── __init__.py
│   ├── business_rules_page.py
│   ├── campaign_page.py
│   ├── results_page.py
│   ├── run_page.py
│   ├── state.py
│   └── upload_page.py
│
└── tests/
    ├── __init__.py
    ├── test_core/
    │   ├── __init__.py
    │   ├── conftest.py
    │   ├── test_audience_manager.py
    │   ├── test_behavior_engine.py
    │   ├── test_config_loader.py
    │   ├── test_engagement_generator.py
    │   ├── test_excel_exporter.py
    │   ├── test_input_loader.py
    │   ├── test_journey_engine.py
    │   ├── test_simulation_orchestrator.py
    │   ├── test_user_state_manager.py
    │   └── test_validation_engine.py
    ├── test_e2e/
    │   ├── __init__.py
    │   ├── test_business_rule_certification.py
    │   ├── test_historical_window_certification.py
    │   ├── test_multirun_persistence_certification.py
    │   ├── test_multitrigger_certification.py
    │   └── test_scale_certification.py
    ├── test_models/
    │   ├── __init__.py
    │   ├── test_ad_config.py
    │   ├── test_capacity_row.py
    │   ├── test_config_registry.py
    │   ├── test_config_registry_weights.py
    │   ├── test_enums.py
    │   ├── test_segment_config.py
    │   ├── test_trigger_config.py
    │   └── test_user_state.py
    ├── test_ui/
    │   ├── __init__.py
    │   └── test_smoke.py
    ├── test_utils/
    │   ├── __init__.py
    │   └── test_schema_validator.py
    └── unit/
        ├── __init__.py
        └── test_date_utils.py
```

**Totals:** 37 production Python files (9,093 lines) · 34 test files (15,178 lines) · 1,111 tests · 0 failures

---

## 3. Required Production Files

These files must be present for the application to run. Do not delete any of them.

| File | Purpose |
|---|---|
| `app.py` | Streamlit application entry point — the only file you run |
| `core/simulation_orchestrator.py` | Master pipeline controller |
| `core/engagement_generator.py` | Core engagement simulation engine |
| `core/audience_manager.py` | User eligibility and audience resolution |
| `core/behavior_engine.py` | Per-user behavioral simulation (RNG-seeded) |
| `core/journey_engine.py` | Ad journey progression and cooling logic |
| `core/user_state_manager.py` | User state initialization and finalization |
| `core/validation_engine.py` | Quality scoring and rule validation |
| `core/excel_exporter.py` | Excel workbook generation |
| `core/config_loader.py` | Campaign configuration loading |
| `core/input_loader.py` | Trigger and historical file loading |
| `models/config_registry.py` | Central configuration schema |
| `models/simulation_result.py` | Immutable result envelope |
| `models/enums.py` | Shared enumerations |
| `models/ad_config.py` | Ad configuration model |
| `models/trigger_config.py` | Trigger configuration model |
| `models/segment_config.py` | Segment configuration model |
| `models/channel_config.py` | Channel configuration model |
| `models/rule_config.py` | Rule configuration model |
| `models/capacity_row.py` | Capacity tracking model |
| `models/user_state.py` | User state model |
| `utils/constants.py` | Shared constants (delimiters, column names) |
| `utils/exceptions.py` | Custom exception hierarchy |
| `utils/logger.py` | Centralized logging setup |
| `utils/schema_validator.py` | Input file schema validation |
| `utils/date_utils.py` | Date arithmetic helpers |
| `utils/excel_utils.py` | Excel formatting helpers |
| `utils/version.py` | Application version constants |
| `ui/state.py` | Streamlit session state manager |
| `ui/upload_page.py` | File upload page |
| `ui/campaign_page.py` | Campaign configuration page |
| `ui/business_rules_page.py` | Business rules configuration page |
| `ui/run_page.py` | Simulation execution page |
| `ui/results_page.py` | Results and download page |

---

## 4. Required Documentation Files

Keep these in the repository root alongside `app.py`.

| File | Purpose |
|---|---|
| `README.md` | User-facing setup and usage guide (create before upload) |
| `requirements.txt` | Python dependency list (create before upload) |
| `.gitignore` | Prevents test artifacts from being uploaded to GitHub |

---

## 5. Test Files to Retain

All test files should be committed to the repository. They prove correctness and allow any developer to verify the application works after making changes.

```
tests/test_core/          — 10 unit test files (743 tests)
tests/test_models/        — 8 unit test files (57 tests)
tests/test_utils/         — 1 unit test file (45 tests)
tests/test_e2e/           — 5 end-to-end certification files (266 tests)
tests/test_ui/            — 1 smoke test file
tests/unit/               — 1 utility test file
```

**How to run all tests:**
```bash
cd engagement_data_generator
pip install -r requirements.txt
pytest tests/
```

---

## 6. Files Safe to Archive

These files document the development process. They are not needed to run the application but are valuable historical records. Move them to a separate folder called `project_archive/` outside the repository, or store them in a shared drive.

- All `STAGE_*` certification reports (`STAGE_12` through `STAGE_16`)
- All `ARCH_RISK_*` remediation reports
- All `WAVE_*` execution reports
- All `PHASE_*` execution plans and gate reviews
- All `*_IMPLEMENTATION_REPORT.md` files
- `PROJECT_MASTER_REGISTER.md`, `PROJECT_MEMORY.md`, `PROJECT_BACKLOG.md`
- `TRACEABILITY_MATRIX.md`, `USER_STATE_DICTIONARY.md`
- `RELEASE_GATES.md`, `GOVERNANCE_SYNC_REPORT.md`
- `PROJECT_RELEASE_PACKAGE.md` (this document) — archive after setup is complete
- `REPOSITORY_CLEANUP_REPORT.md` — archive after cleanup is done
- `STAGE_11_STREAMLIT_MVP_IMPLEMENTATION.md` — archive

---

## 7. Files Safe to Delete

These are generated artifacts created automatically by Python and pytest. They do not belong in a repository.

```
__pycache__/              — Python bytecode cache (all occurrences)
*.pyc                     — Compiled Python files
.pytest_cache/            — pytest run cache
.coverage                 — Coverage data file
.coverage.*               — Coverage partial files
```

The `.gitignore` file below prevents these from ever being uploaded to GitHub.

---

## 8. Python Dependency Inventory

The application uses four third-party libraries. All other imports are from Python's standard library.

| Library | Version | Purpose |
|---|---|---|
| `pandas` | 2.3.3 | DataFrame operations — the core data structure for all simulation state |
| `openpyxl` | 3.1.5 | Excel workbook generation (.xlsx export) |
| `streamlit` | 1.58.0 | Web application framework — the user interface |
| `numpy` | 2.2.6 | Numerical operations (used internally by pandas) |

**Dev-only (not needed to run the app):**

| Library | Version | Purpose |
|---|---|---|
| `pytest` | 9.1.1 | Test runner |

---

## 9. Final requirements.txt

Create a file named `requirements.txt` in the `engagement_data_generator/` folder with exactly this content:

```
pandas>=2.0.0
openpyxl>=3.1.0
streamlit>=1.30.0
numpy>=1.24.0
```

**Note:** Version ranges (>=) rather than exact pins are used so that Streamlit Cloud can resolve compatible versions automatically. If you need exact reproducibility, use the pinned versions: `pandas==2.3.3`, `openpyxl==3.1.5`, `streamlit==1.58.0`, `numpy==2.2.6`.

---

## 10. Final .gitignore

Create a file named `.gitignore` in the `engagement_data_generator/` folder with exactly this content:

```
# Python bytecode
__pycache__/
*.py[cod]
*.pyo

# Test artifacts
.pytest_cache/
.coverage
.coverage.*
htmlcov/

# Virtual environments
.venv/
venv/
env/

# OS files
.DS_Store
Thumbs.db

# Editor files
.vscode/
.idea/
*.swp

# Streamlit local config
.streamlit/secrets.toml

# Local outputs and temp files
*.log
```

---

## 11. README.md Outline

Create a file named `README.md` in the `engagement_data_generator/` folder. Here is the exact content to use:

```markdown
# Engagement Data Generator

A simulation platform for generating realistic pharmaceutical engagement data across multi-channel campaigns.

## What It Does

Upload a trigger file (list of users), configure your campaign settings, and generate a fully simulated engagement dataset — complete with journey progression, behavioral scoring, fatigue modelling, and an Excel workbook ready for analysis.

## Quick Start

### Run locally

1. Install Python 3.10 or later from https://python.org
2. Open a terminal in this folder and run:
   pip install -r requirements.txt
   streamlit run app.py
3. A browser window will open automatically at http://localhost:8501

### Run on Streamlit Cloud

See the Streamlit deployment section below.

## How to Use

1. **Upload Files** — Upload your trigger file (CSV/Excel) and optionally a historical engagement file.
2. **Campaign Setup** — Enter campaign dates, ad journey, and target engagement rates.
3. **Business Rules** — Configure cooling periods, re-entry rules, and capacity caps.
4. **Run Simulation** — Click Run and watch the simulation execute.
5. **Results** — Download the Excel workbook with events, state, metrics, and validation.

## Input File Format

Your trigger file must be a CSV or Excel file with these columns:
- `Campaign_ID` — Campaign identifier
- `User_ID` — Unique user identifier
- `Trigger_Name` — Name of the trigger event
- `Segment` — User segment label

## Requirements

- Python 3.10+
- pandas, openpyxl, streamlit, numpy (installed via requirements.txt)

## Running Tests

pip install pytest
pytest tests/

## Version

1.0.0
```

---

## 12. Streamlit Entry Point

The application entry point is `app.py` in the root of the repository folder.

**To run locally:**
```bash
streamlit run app.py
```

**The app has 5 pages, accessible from the left sidebar:**
1. Upload Files — load trigger CSV/Excel and optional historical data
2. Campaign Setup — dates, ads, triggers, segments
3. Business Rules — cooling, re-entry, caps, fatigue
4. Run Simulation — execute the pipeline with a single click
5. Results — view summary metrics and download the Excel workbook

**Streamlit Cloud entry point setting:** `app.py` (the default — no change needed)

---

## 13. Deployment File Inventory

These are the only files Streamlit Cloud needs to deploy the application:

| File | Required? | Notes |
|---|---|---|
| `app.py` | ✅ Yes | Entry point |
| `requirements.txt` | ✅ Yes | Tells Streamlit Cloud what to install |
| `core/*.py` | ✅ Yes | All 11 files |
| `models/*.py` | ✅ Yes | All 10 files |
| `utils/*.py` | ✅ Yes | All 8 files |
| `ui/*.py` | ✅ Yes | All 6 files |
| `tests/` | Optional | Safe to include; not executed by Streamlit Cloud |
| `README.md` | Recommended | Displayed on GitHub |
| `.gitignore` | Recommended | Keeps repository clean |
| `__pycache__/` | ❌ No | Exclude via .gitignore |
| `*.md` cert reports | ❌ No | Do not upload to GitHub |

---

## 14. Local Folder Organization Instructions

Before uploading to GitHub, organize your local folder like this:

**Step 1 — Create your working folder**

On your computer, create a folder structure like this:

```
PharmaForceIQ/
├── engagement_data_generator/    ← This is what goes on GitHub
│   ├── app.py
│   ├── requirements.txt
│   ├── .gitignore
│   ├── README.md
│   ├── core/
│   ├── models/
│   ├── utils/
│   ├── ui/
│   └── tests/
│
└── project_archive/              ← Keep this locally, NOT on GitHub
    ├── STAGE_12_*.md
    ├── STAGE_13_*.md
    ├── STAGE_14_*.md
    ├── STAGE_15_*.md
    ├── STAGE_16_*.md
    ├── ARCH_RISK_*.md
    ├── WAVE_*.md
    ├── PHASE_*.md
    └── (all other .md docs)
```

**Step 2 — Create the two new files**

Inside `engagement_data_generator/`, create:
- `requirements.txt` — copy the content from Section 9 above
- `.gitignore` — copy the content from Section 10 above
- `README.md` — copy the content from Section 11 above

**Step 3 — Delete generated artifacts**

Inside `engagement_data_generator/`, delete:
- Any `__pycache__/` folders
- Any `.pyc` files
- `.coverage` and `.coverage.*` files
- `.pytest_cache/` folders

---

## 15. GitHub Repository Setup Instructions

**If you do not have a GitHub account:**
1. Go to https://github.com and click "Sign up"
2. Choose a free plan
3. Verify your email address

**Create a new repository:**
1. Log in to GitHub
2. Click the green **"New"** button (top left, next to your username)
3. Fill in:
   - **Repository name:** `engagement-data-generator`
   - **Description:** `PharmaForce IQ — Pharmaceutical engagement simulation platform`
   - **Visibility:** Choose **Private** (recommended for internal tools) or Public
   - ✅ Check **"Add a README file"** — uncheck this if you already created README.md
   - Leave everything else as default
4. Click **"Create repository"**

---

## 16. GitHub Upload Instructions (Non-Technical)

**The easiest method — GitHub Desktop (recommended for non-technical users):**

1. Download **GitHub Desktop** from https://desktop.github.com
2. Install and sign in with your GitHub account
3. In GitHub Desktop: click **File → Clone Repository**
4. Select the `engagement-data-generator` repository you just created
5. Choose a location on your computer — this creates a local copy
6. Copy all files from your `engagement_data_generator/` folder into the cloned folder
7. In GitHub Desktop, you will see all the new files listed on the left
8. At the bottom left, type a summary like: `Initial release v1.0.0`
9. Click **"Commit to main"**
10. Click **"Push origin"** (top right)
11. Go to https://github.com/YOUR_USERNAME/engagement-data-generator to verify

**Alternative — Upload directly on GitHub.com (for small changes):**
1. Go to your repository page on GitHub
2. Click **"Add file" → "Upload files"**
3. Drag and drop files from your `engagement_data_generator/` folder
4. Scroll down, add a commit message, and click **"Commit changes"**

**Note:** The drag-and-drop method works for individual files but not for uploading entire folder structures. Use GitHub Desktop for uploading the full project.

---

## 17. Streamlit Deployment Instructions

Streamlit Cloud deploys your app directly from GitHub — no server needed.

**Steps:**

1. Go to https://share.streamlit.io
2. Sign in with your GitHub account
3. Click **"New app"**
4. Fill in:
   - **Repository:** `YOUR_USERNAME/engagement-data-generator`
   - **Branch:** `main`
   - **Main file path:** `app.py`
5. Click **"Deploy!"**
6. Wait 2–3 minutes for the first deployment to complete
7. Your app will be live at a URL like: `https://YOUR_APP_NAME.streamlit.app`

**Updating the app after changes:**
- Make changes to your files locally
- Commit and push to GitHub via GitHub Desktop
- Streamlit Cloud automatically detects the change and redeploys (takes ~1 minute)

**If the deployment fails:**
- Click "Manage app" → "Logs" to see the error
- Common causes: missing `requirements.txt`, typo in file path, missing `__init__.py`

**Free tier limits on Streamlit Cloud:**
- 1 app per account (free plan)
- App sleeps after 7 days of inactivity (wakes when someone visits)
- No private apps on the free tier — use a private GitHub repository with a paid Streamlit plan for internal use

---

## 18. Team Sharing Instructions

**Share via Streamlit Cloud URL:**
1. After deployment, copy the app URL (e.g. `https://your-app.streamlit.app`)
2. Share that URL with your team — they open it in any browser, no installation needed
3. The app runs entirely in the browser; users do not need Python or GitHub access

**Share the GitHub repository with collaborators:**
1. Go to your GitHub repository
2. Click **Settings → Collaborators**
3. Click **"Add people"** and enter their GitHub username or email
4. Choose **"Write"** access so they can update files, or **"Read"** for view-only

**Share via a private Streamlit deployment (for internal/enterprise use):**
1. Upgrade to Streamlit Cloud Teams (https://streamlit.io/cloud)
2. Set viewer access to specific email addresses or SSO
3. This keeps the app private and accessible only to your team

---

## 19. Backup Strategy

**Primary backup — GitHub:**
Your GitHub repository is your primary backup. Every time you push changes, GitHub stores a full copy with version history. Even if you delete your local files, you can restore everything from GitHub.

**What to back up locally:**

| What | Where | How often |
|---|---|---|
| Full project folder | External drive or cloud (Google Drive, OneDrive) | After every major change |
| `project_archive/` folder | Same as above | Whenever you add new cert documents |
| GitHub repository | Already backed up by GitHub | Automatic |

**Backup procedure (simple):**
1. Zip the entire `PharmaForceIQ/` folder on your computer
2. Name it `PharmaForceIQ_backup_YYYY-MM-DD.zip`
3. Copy to Google Drive, OneDrive, or an external drive
4. Keep the last 3 backups

**Disaster recovery:**
If you lose your local copy, you can always re-clone from GitHub:
```bash
git clone https://github.com/YOUR_USERNAME/engagement-data-generator
```
Or use GitHub Desktop: File → Clone Repository.

---

## 20. Release Checklist

Complete these steps in order before sharing the app with users.

### Before uploading to GitHub

- [ ] Create `requirements.txt` (copy from Section 9)
- [ ] Create `.gitignore` (copy from Section 10)
- [ ] Create `README.md` (copy from Section 11)
- [ ] Delete all `__pycache__/` folders from the project
- [ ] Delete `.coverage` and `.pytest_cache/` artifacts
- [ ] Move all `.md` certification/planning documents to `project_archive/`
- [ ] Verify `app.py` exists in the root of `engagement_data_generator/`
- [ ] Run `pytest tests/` locally one final time — confirm 1,111 tests pass

### GitHub setup

- [ ] Create GitHub account (if needed)
- [ ] Create repository: `engagement-data-generator`
- [ ] Install GitHub Desktop
- [ ] Clone repository to local machine
- [ ] Copy all project files into cloned folder
- [ ] Commit with message: `Initial release v1.0.0 — certified`
- [ ] Push to GitHub
- [ ] Verify files appear correctly at github.com

### Streamlit deployment

- [ ] Go to share.streamlit.io
- [ ] Create new app pointing to `app.py` on `main` branch
- [ ] Wait for deployment to complete
- [ ] Open the app URL and verify it loads
- [ ] Test the Upload page — upload a sample trigger file
- [ ] Test the Run Simulation page — run a small simulation
- [ ] Test the Results page — download the Excel workbook
- [ ] Confirm the workbook opens correctly in Excel

### Team handoff

- [ ] Copy the Streamlit app URL
- [ ] Share URL with intended users
- [ ] Add team members as GitHub collaborators (if they need code access)
- [ ] Create a one-page user guide (optional but recommended)
- [ ] Take a zip backup of the full project folder

---

*Document prepared by Release Manager — Stage 16 certified — 2026-06-23*
