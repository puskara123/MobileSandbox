# Testing Guide

## Backend Tests

```bash
cd analysis_server
source venv/bin/activate
python -m pytest test_backend.py -v
```

The tests use a temporary SQLite database through pytest fixtures, so they do
not intentionally modify `analysis_server/signatures.db`.

Covered behavior:

- Safe, medium-risk, and high-risk permission scoring.
- Scan history insert/retrieval.
- Duplicate scan suppression.
- Feedback aggregation.
- Package-scoped feedback adjustment.
- Aggregate stats.
- Known-safe score caps.
- Zero-permission safe baseline.

## Android Build Test

```bash
cd mobile_app
./gradlew :app:assembleDebug
```

Expected output APK:

```text
mobile_app/app/build/outputs/apk/debug/app-debug.apk
```

## Manual End-to-End Test

1. Start backend:

   ```bash
   cd analysis_server
   source venv/bin/activate
   uvicorn main:app --host 0.0.0.0 --port 8000
   ```

2. Confirm backend:

   ```bash
   curl http://localhost:8000/calibrate
   ```

3. Install Android app.
4. Tap scan and confirm result cards appear.
5. Submit one safe/malware feedback item.
6. Open:

   ```text
   http://localhost:8000/feedback/history
   http://localhost:8000/scan/history
   ```

7. Confirm the submitted feedback and scan are persisted.

## Known Environment Note

The checked-in joblib model must be loaded with a compatible scikit-learn/joblib
environment. Use the virtual environment created from
`analysis_server/requirements.txt`. If model loading fails after dependency
changes, retrain from `dataset/data.csv` so the model artifact matches the local
scikit-learn version.
