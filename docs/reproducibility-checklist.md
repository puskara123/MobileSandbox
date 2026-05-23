## Fresh Clone Verification

Backend:

```bash
make backend-install
make backend-run
```

In another terminal:

```bash
curl http://localhost:8000/calibrate
make backend-test
```

Android:

```bash
cd mobile_app
./gradlew :app:assembleDebug
```

For emulator testing, keep the default API URL `http://10.0.2.2:8000/`.
For physical-device testing, copy `mobile_app/local.properties.example` to
`mobile_app/local.properties` and set `analysis.api.base.url` to the laptop LAN
IP.


