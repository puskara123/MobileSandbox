.PHONY: backend-install backend-run backend-test android-build db-view db-progression

backend-install:
	cd analysis_server && python3 -m venv venv && . venv/bin/activate && pip install -r requirements.txt

backend-run:
	cd analysis_server && . venv/bin/activate && uvicorn main:app --host 0.0.0.0 --port 8000

backend-test:
	cd analysis_server && . venv/bin/activate && python -m pytest test_backend.py -v

android-build:
	cd mobile_app && ./gradlew :app:assembleDebug

db-view:
	cd analysis_server && . venv/bin/activate && python view_db.py

db-progression:
	cd analysis_server && . venv/bin/activate && python view_db.py progression
