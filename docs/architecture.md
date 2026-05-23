# Architecture

MobileSandbox has two runtime components:

```text
Android app  --->  FastAPI backend  --->  SQLite database
     |                  |
     |                  +-- scikit-learn model + permission scoring rules
     |
     +-- installed app scan / pre-install APK scan
```

## Android App

The Android app lives in `mobile_app/app/src/main`.

Important files:

- `MainActivity.kt`: main UI, installed-app scan, pre-install APK scan,
  feedback submission, history tab.
- `AppScanner.kt`: reads installed apps and requested permissions using
  `PackageManager`.
- `ApkPreInstallStaging.kt`: copies selected APKs to app-private cache and reads
  `PackageInfo` before installation.
- `SplitApkSessionInstall.kt`: installs base/split APKs through
  `PackageInstaller.Session`.
- `InstallCommitReceiver.kt`: handles install confirmation callbacks.
- `api/RetrofitClient.kt`: Retrofit API client.
- `api/AnalysisModels.kt`: request/response models shared with backend API.
- `ui/SpeedometerView.kt`: custom 0-100 risk score meter.

Main app flows:

1. **Installed app scan**
   - User taps scan.
   - `AppScanner.getInstalledApps(false)` lists user apps.
   - `AppScanner.getPermissions(packageName)` extracts permissions.
   - App calls backend `POST /analyze`.
   - Result card is rendered with risk level, score, PII, sensitive permissions,
     and feedback buttons.

2. **Pre-install APK scan**
   - User chooses one APK or multiple split APK files.
   - APKs are staged in app-private cache.
   - `PackageManager.getPackageArchiveInfo` reads package metadata without
     installing.
   - Permissions are analyzed by the backend.
   - User can reject/delete staged files or continue to system install.

3. **Feedback**
   - User marks a result as safe or malware.
   - App calls backend `POST /feedback`.
   - Backend records package-scoped feedback and uses it in future scoring.

## Backend

The backend lives in `analysis_server`.

Important files:

- `main.py`: FastAPI app and route definitions.
- `ml_engine.py`: scoring engine, model loading/training, adaptive feedback.
- `db_manager.py`: SQLite schema migration, scan history, feedback, stats.
- `test_backend.py`: backend regression tests.
- `model/`: trained model, metadata, permission risk map, known-safe caps.
- `dataset/data.csv`: training dataset.

Backend endpoints:

- `POST /analyze`: score one app from package name and permissions.
- `POST /feedback`: store user feedback and apply adaptive update.
- `GET /scan/history`: recent scans.
- `GET /feedback/history`: all feedback.
- `GET /ratings/progression`: chronological user ratings by package.
- `GET /stats`: aggregate scan/feedback statistics.
- `GET /calibrate`: scoring thresholds and model configuration.
- `POST /retrain`: background retrain from feedback.

## Scoring Design

`ml_engine.analyze_permissions()` blends several signals:

- Static permission risk weights on a 0-10 scale.
- Trained GradientBoostingClassifier probability signal.
- Safe-biased Bayesian prior.
- Dangerous permission combination multipliers.
- Dampeners for sparse apps and apps with low high-risk permission ratio.
- Known-safe package score caps.
- Package-scoped feedback adjustment.

The final score is scaled to 0-100 and classified:

- `SAFE`: score `< 30`
- `HANDLE_WITH_CARE`: score `30-54`
- `SUSPICIOUS`: score `55-74`
- `DANGEROUS`: score `>= 75`

## Persistence

SQLite database: `analysis_server/signatures.db`.

Tables:

- `feedback`: user feedback rows with package, permissions, malware label,
  notes, timestamp, user id.
- `scan_history`: saved analysis results with package, level, score, detected
  permission categories, confidence, timestamp, user id.

The database schema is created and migrated by `db_manager.init_db()` on backend
startup.
