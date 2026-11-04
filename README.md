<<<<<<< HEAD
# AXIOM / Anuraksana Predictive Maintenance Portal

Anuraksana is a local predictive-maintenance portal using NASA C-MAPSS FD001 simulated turbofan readings and a trained Random Forest remaining-useful-life model.

Features include machine risk ranking, automatic demo rotation, sensor/RUL trends, a detailed interactive 3D engine, model comparison metrics, persistent work orders, and optional Telegram alerts with worker acknowledgements.

The 3D view visualizes the selected engine prediction. Its component panel offers related sensor trends and inspection guidance; FD001 does not provide independent component-failure diagnoses. Motion is illustrative, not measured hardware speed.

## Start

Windows: double-click `Install-and-Run.cmd`. It installs locked Node dependencies, builds React, creates a Python virtual environment and installs `backend/requirements.txt`, then serves the portal at **http://127.0.0.1:8767/**. Keep the terminal open. Python 3.11–3.13 and Node 22.12+ are required. No retraining is needed: the trained model and FD001 data are included.

From PowerShell, run the installer with the explicit current-directory prefix:

```powershell
cd C:\Users\Satyarth\Desktop\industrial-digital-twin
.\Install-and-Run.cmd
```

On this computer, after the build and installed dependencies:

```powershell
cd C:\Users\Satyarth\Desktop\industrial-digital-twin
.venv\Scripts\python.exe run.py
```

For frontend development, keep the backend running and use `npm run dev`; Vite proxies `/api` to port 8767. Production uses the Python server for both frontend assets and API. Building while someone is using the production app can briefly invalidate its assets; reload after the build completes.

## Use the FD001 page

1. Select **FD001 Maintenance** in the sidebar.
2. The default table shows the five most urgent engines; choose four or all machines if desired. The 100 reference engines are sorted by lowest predicted remaining life.
3. Inspect an engine to see observed cycles, predicted remaining cycles, estimated end-of-life cycle and sensor/RUL trends. Select any of the 21 original sensors.
4. Draft a work order, enter an assignee and notes, then move through Draft → Approved → In progress → Completed. Cancellation is available before completion. Creating the same prediction-linked draft twice opens the same order.
5. Use sensor replay to run genuine FD001 rows through the model. At least 30 consecutive cycles are required; each advance adds up to 30 observations.
6. Review model metrics or download the 100-engine evaluation CSV.

## Model and interpretation

The model uses trailing 30-cycle windows (last, mean, standard deviation and slope), excludes engine identity, splits development engines 80/20, selects hyperparameters using held-out engines, refits using all 100 training engines and evaluates once on the official 100 test engines. `backend/ml.py` contains the reproducible training pipeline. Tests recompute final predictions from the saved model and verify the saved metrics.

| Official FD001 test metric | Result |
|---|---:|
| MAE | 14.36 cycles |
| RMSE | 19.52 cycles |
| Alert precision | 95.45% |
| Alert recall | 84.00% |
| Baseline MAE | 35.92 cycles |

Alert threshold is RUL ≤30 cycles. Priority: Critical ≤15; High ≤30; Medium ≤60; Low >60. The displayed urgency index is `100 * clamp((60 - RUL) / 60, 0, 1)`; it is **not a failure probability**. Metrics are aggregate test results, not individual confidence intervals.

**Component limitation:** FD001's known fault scenario is high-pressure compressor degradation. HPC inspection focus is explicitly a dataset prior, not a learned component diagnosis. Engine RUL and observed cycle + RUL provide an estimated engine life timeline, not independently validated bearing/fan/compressor lifetimes. Cycles cannot be converted to days or hours without additional operating information. Inspection and maintenance require engineer review.

## Permanent storage

Both FD001 and 3D simulation work orders are stored in **`backend/data/portal.sqlite3`**. They survive browser reload, browser storage clearing and server restarts. Simulation drafts retain their original readings and suggestions. FD001 orders retain the original prediction and model version. The UI reports failed saves instead of claiming success.

To back up: stop the server, then copy `backend/data/portal.sqlite3` to a safe location. If backing up while running, use SQLite's backup API; do not copy only the main file while WAL writes are active. Do not delete this database when rebuilding the UI. Machine simulation settings remain in local browser storage; transient simulation alerts/history remain session-only.

Data: `backend/data/raw/`. Trained model, metadata, metrics and predictions: `backend/artifacts/`. The database is local and unauthenticated; the server binds only to loopback. This is a local demonstration, not a multi-user deployed maintenance system.

## Verification

```powershell
npm test
npm run build
cd backend
python -m unittest discover -s tests -v
cd ..
npm run test:e2e
```

The Playwright suite requires a locally installed Chromium (`npx playwright install chromium`) and Python with the backend dependencies. It starts the production server when none is running. Browser tests create clearly marked QA work orders and replay sessions; run them against a disposable project copy if you need a clean demonstration database.

See `TEST_REPORT.md` for checks performed during this integration.

## User guide and visual design

Open **User guide** in the portal header for all sections, output interpretation and a seven-minute presentation script. The same guide is saved as `USER_GUIDE.md`. The portal opens on FD001 Maintenance. The light workspace, white cards, coral emphasis and compact navigation follow the supplied video reference. Hover navigation icons to see section names; keyboard users receive accessible names and visible focus outlines. Motion respects reduced-motion preferences.


## Repository contents and local configuration

The trained model, FD001 data and browser-ready 3D GLB are included. Dependencies, build output, local databases, Telegram credentials and runtime logs are excluded. A fresh installation creates its own database; your existing work orders are not published to GitHub.

For Telegram setup, follow `TELEGRAM_SETUP.md` and use `backend/telegram.example.json` as the credential-free example. Never commit `backend/telegram.local.json`. The running portal polls for worker responses; starting inspection requires portal approval of the linked work order.

The optional **AI Agent Hub** link and `Launch-AI-Agent.cmd` refer to a separate local project on port 8990. That project's source is outside this repository and is not required for the FD001 portal. Configure it separately if you want to use that integration.

See `USER_GUIDE.md` for the latest workflow. Older verification reports describe earlier versions; browser end-to-end test selectors may need updates after UI changes.
=======
# Predictive-Maintenance-Software-only-DEVIATHON-
This Repo is only for software which i make on NASA Dataset for predictive maintainance
>>>>>>> f47366c9c923f60c61e3f71bbb50ddc1049eced3
