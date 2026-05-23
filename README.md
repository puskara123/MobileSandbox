# MobileSandbox

MobileSandbox is an Android application and local analysis server for scanning
Android apps for permission-based privacy and malware risk.

The Android app scans installed apps or APK files before installation, extracts
requested permissions, sends them to a FastAPI backend, and displays a risk
score with detected PII/sensitive permissions. The backend combines static
permission weights, a trained scikit-learn model, Bayesian priors, package-local
feedback, and scan history stored in SQLite.

## Repository Layout

```text
MobileSandbox/
|-- analysis_server/              # FastAPI backend, ML scoring, SQLite storage
|   |-- main.py                   # API entry point
|   |-- ml_engine.py              # Permission risk scoring and model loading
|   |-- db_manager.py             # SQLite schema, feedback, history
|   |-- test_backend.py           # Pytest backend regression tests
|   |-- requirements.txt          # Python backend dependencies
|   |-- dataset/data.csv          # Training dataset
|   `-- model/                    # Trained model and scoring metadata
|-- mobile_app/                   # Android/Kotlin application
|   |-- app/build.gradle          # App dependencies and API base URL config
|   |-- app/src/main/...          # Kotlin source, layouts, resources
|   `-- gradlew                   # Gradle wrapper
|-- docs/                         # Architecture, testing, demo, handover docs
|-- requirements.txt              # Root Python dependency entry point
`-- LICENSE
```

## Tech Stack

- Android: Kotlin, Android Gradle Plugin 8.2.2, Gradle 8.2 wrapper, Material
  Components, Retrofit, Gson, Coroutines, Lottie.
- Backend: Python 3.10+ recommended, FastAPI, Uvicorn, Pydantic, pandas, NumPy,
  scikit-learn, joblib, SQLite.
- ML: Permission-feature dataset, GradientBoostingClassifier, static permission
  risk table, known-safe package caps, package-scoped feedback adjustment.

## Prerequisites

- Python 3.10 or newer.
- Android Studio or Android SDK with `adb`.
- JDK 17.
- A physical Android device or emulator.
- For emulator backend access: use `http://10.0.2.2:8000/`.
- For physical device backend access: use your host machine LAN IP, for example
  `http://192.168.1.42:8000/`.

## Backend Setup

From the repository root:

```bash
cd analysis_server
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000
```

The server initializes `signatures.db` on startup and loads the model from
`analysis_server/model/ml_model.joblib`. If the model is missing, the backend
attempts to train from `analysis_server/dataset/data.csv`.

Useful backend URLs:

- API health/open docs: `http://localhost:8000/docs`
- Scan history: `http://localhost:8000/scan/history`
- Feedback history: `http://localhost:8000/feedback/history`
- Rating progression: `http://localhost:8000/ratings/progression`
- Aggregate stats: `http://localhost:8000/stats`
- Scoring calibration: `http://localhost:8000/calibrate`

## Android Setup

Open `mobile_app/` in Android Studio, or build from the terminal.

For emulator usage, no extra configuration is required because the default API
base URL is `http://10.0.2.2:8000/`.

For a physical device, create `mobile_app/local.properties`:

```properties
sdk.dir=/absolute/path/to/Android/Sdk
analysis.api.base.url=http://YOUR_COMPUTER_LAN_IP:8000/
```

An example is provided at `mobile_app/local.properties.example`.

Build and install:

```bash
cd mobile_app
./gradlew :app:assembleDebug
adb install -r app/build/outputs/apk/debug/app-debug.apk
```

## Running The Full System

1. Start the backend:

   ```bash
   cd analysis_server
   source venv/bin/activate
   uvicorn main:app --host 0.0.0.0 --port 8000
   ```

2. Confirm the API is reachable:

   ```bash
   curl http://localhost:8000/calibrate
   ```

3. Build/install the Android app from `mobile_app/`.
4. Launch **Data Leakage Sandbox** on the device.
5. Tap the scan button to analyze installed user apps.
6. Use **Pre-install APK scan** to choose one APK or a full split APK set before
   installing.
7. Open the History tab to view backend scan records.

## Backend API Contract

### `POST /analyze`

Request:

```json
{
  "package_name": "com.example.app",
  "permissions": ["android.permission.INTERNET"],
  "user_id": "anonymous"
}
```

Response:

```json
{
  "app": "com.example.app",
  "risk_level": "SAFE",
  "score": 12,
  "score_min": 12,
  "score_max": 12,
  "score_precise": 12.3,
  "leak_type": "Low Risk / No Critical Leak (Range: 12-12)",
  "pii_detected": [],
  "sensitive_detected": [],
  "detected_threats": [],
  "confidence": 0.91
}
```

### `POST /feedback`

Request:

```json
{
  "package_name": "com.example.app",
  "permissions": ["android.permission.INTERNET"],
  "is_malware": false,
  "user_notes": "",
  "user_id": "anonymous"
}
```

## Testing

Backend tests:

```bash
cd analysis_server
source venv/bin/activate
python -m pytest test_backend.py -v
```

Android build verification:

```bash
cd mobile_app
./gradlew :app:assembleDebug
```

More details are in [docs/testing.md](docs/testing.md).

## Documentation

- [Architecture](docs/architecture.md)
- [Setup Guide](docs/setup.md)
- [Testing Guide](docs/testing.md)
- [Demo Script](docs/demo.md)
- [Handover Checklist](docs/handover.md)
- [Reproducibility Checklist](docs/reproducibility-checklist.md)
- [Dependencies](DEPENDENCIES.md)

## Project Reports

- [Project Handover Report](MobileSandbox_ProjectHandoverReport.pdf)
- [Final PE Report](MobileSandboxFinalPEReport.pdf)
- [Original Handover Checklist DOCX](iiitb_Project%20Handover%20Checklist.docx)

## Convenience Commands

The root `Makefile` provides shortcuts:

```bash
make backend-install
make backend-run
make backend-test
make android-build
make db-view
make db-progression
```

## Common Issues

- **Android app cannot connect to backend on emulator:** use
  `http://10.0.2.2:8000/`, not `localhost`.
- **Physical device cannot connect:** make sure phone and laptop are on the same
  network, the backend is started with `--host 0.0.0.0`, and
  `analysis.api.base.url` points to the laptop LAN IP.
- **Joblib/scikit-learn model load error:** use the project virtual environment
  and dependencies from `analysis_server/requirements.txt`. If necessary,
  retrain the model from `dataset/data.csv`.
- **Split APK install fails:** select `base.apk` and all matching
  `split_config.*.apk` files from the same bundle together.

## License

This project is released under the MIT License. See [LICENSE](LICENSE).
