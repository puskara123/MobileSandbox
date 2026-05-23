# Setup Guide

This guide starts from a fresh clone and ends with the backend and Android app
running together.

## 1. Clone

```bash
git clone https://github.com/hrdhruv/MobileSandbox.git
cd MobileSandbox
```

## 2. Backend

```bash
cd analysis_server
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python3 main.py
```

Keep this terminal running. 


## 3. Android App

Open `mobile_app/` in Android Studio.

For emulator:

- Keep the default backend URL: `http://10.0.2.2:8000/`.
- Start an emulator.
- Run the app from Android Studio.

For physical device:

1. Find your laptop IP address on the same Wi-Fi network.
2. Copy the example config:

   ```bash
   cp mobile_app/local.properties.example mobile_app/local.properties
   ```

3. Set:

   ```properties
   analysis.api.base.url=http://YOUR_LAPTOP_IP:8000/
   ```

4. Build and install:

   ```bash
   cd mobile_app
   ./gradlew :app:assembleDebug
   adb install -r app/build/outputs/apk/debug/app-debug.apk
   ```

## 4. Quick Smoke Test

Backend:

```bash
curl http://localhost:8000/calibrate
```

Android:

1. Open **Data Leakage Sandbox**.
2. Tap the scan button.
3. Confirm result cards appear.
4. Tap the History tab and confirm scan entries load.

## 5. Database Tools

Inspect the SQLite database:

```bash
cd analysis_server
source venv/bin/activate
python view_db.py
python view_db.py progression
```
