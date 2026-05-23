# Dependencies

This file summarizes the dependency entry points for a new developer.

## Backend

Install from the root:

```bash
pip install -r requirements.txt
```

Or from the backend folder:

```bash
cd analysis_server
pip install -r requirements.txt
```

Backend dependencies are declared in `analysis_server/requirements.txt`:

- `fastapi`
- `uvicorn`
- `pydantic`
- `pandas`
- `numpy`
- `scikit-learn`
- `joblib`

Python 3.10 or newer is recommended.

## Android

Android dependencies are declared in `mobile_app/app/build.gradle`.

Key versions:

- Android Gradle Plugin: `8.2.2`
- Kotlin Gradle plugin: `1.9.22`
- Gradle wrapper: `8.2`
- Java/JDK target: `17`
- Compile SDK: `34`
- Minimum SDK: `22`
- Target SDK: `34`

Main app libraries:

- AndroidX Core KTX
- AppCompat
- Material Components
- Lifecycle Runtime KTX
- Kotlin Coroutines Android
- Retrofit
- Gson converter
- RecyclerView
- CardView
- ConstraintLayout
- Lottie

## Local Configuration

Use `mobile_app/local.properties.example` as the Android local config template.
The actual `mobile_app/local.properties` file is intentionally ignored because
it contains machine-specific paths.
