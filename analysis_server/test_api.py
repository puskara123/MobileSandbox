"""
test_api.py — API-level tests for Step 2: confirms /analyze exposes the
plain-English fields from plain_english.explain(), that scan history
stores and serves risk_summary, and that an old database (created before
this step) upgrades cleanly.

Run from analysis_server/ directory:
    python -m pytest test_api.py -v
"""

import sqlite3

import pytest
from fastapi.testclient import TestClient

import db_manager
import main

SAMPLE_PERMISSIONS = [
    "android.permission.READ_SMS",
    "android.permission.SEND_SMS",
    "android.permission.READ_CONTACTS",
    "android.permission.INTERNET",
]


@pytest.fixture(autouse=True)
def use_test_db(tmp_path, monkeypatch):
    """Redirect all DB calls to a temporary file, same convention as test_backend.py."""
    test_db = str(tmp_path / "test.db")
    monkeypatch.setattr(db_manager, "DB_PATH", test_db)
    yield


@pytest.fixture
def client():
    # Entering the context runs main.app's startup event (db_manager.init_db()
    # + ml_engine.load_or_train()) against the DB_PATH patched above.
    with TestClient(main.app) as c:
        yield c


# ------------------------------------------------------------------
# /analyze response shape
# ------------------------------------------------------------------

def test_analyze_keeps_all_existing_fields(client):
    resp = client.post("/analyze", json={
        "package_name": "com.example.testapp",
        "permissions": SAMPLE_PERMISSIONS,
        "user_id": "tester",
    })
    assert resp.status_code == 200
    body = resp.json()
    for field in ("app", "risk_level", "score", "score_min", "score_max",
                  "score_precise", "leak_type", "pii_detected",
                  "sensitive_detected", "detected_threats", "confidence"):
        assert field in body, f"Existing field '{field}' went missing"


def test_analyze_adds_plain_english_fields(client):
    resp = client.post("/analyze", json={
        "package_name": "com.example.testapp",
        "permissions": SAMPLE_PERMISSIONS,
        "user_id": "tester",
    })
    body = resp.json()

    assert isinstance(body["risk_summary"], str) and body["risk_summary"]

    assert isinstance(body["risk_reasons"], list)
    assert len(body["risk_reasons"]) >= 1  # SMS + contacts should surface reasons
    for reason in body["risk_reasons"]:
        assert set(reason.keys()) == {"group", "title", "access", "why"}
        for value in reason.values():
            assert isinstance(value, str) and value

    assert isinstance(body["risk_patterns"], list)
    assert all(isinstance(s, str) for s in body["risk_patterns"])

    assert isinstance(body["minor_permissions"], list)
    assert all(isinstance(s, str) for s in body["minor_permissions"])


def test_analyze_safe_app_has_no_reasons_but_still_has_a_summary(client):
    resp = client.post("/analyze", json={
        "package_name": "com.example.safeapp",
        "permissions": ["android.permission.VIBRATE"],
        "user_id": "tester",
    })
    body = resp.json()
    assert body["risk_reasons"] == []
    assert body["risk_summary"]


# ------------------------------------------------------------------
# Scan history carries the summary through
# ------------------------------------------------------------------

def test_scan_history_includes_risk_summary(client):
    analyze_resp = client.post("/analyze", json={
        "package_name": "com.example.historyapp",
        "permissions": SAMPLE_PERMISSIONS,
        "user_id": "tester",
    })
    expected_summary = analyze_resp.json()["risk_summary"]

    history_resp = client.get("/scan/history")
    assert history_resp.status_code == 200
    scans = history_resp.json()["scans"]

    match = next(s for s in scans if s["package_name"] == "com.example.historyapp")
    assert match["risk_summary"] == expected_summary


# ------------------------------------------------------------------
# Compatibility: old DB and old callers
# ------------------------------------------------------------------

def test_old_database_upgrades_without_error(tmp_path, monkeypatch):
    """
    Simulate a scan_history table from before this step (no risk_summary
    column) and confirm init_db() upgrades it in place without raising.
    """
    old_db = str(tmp_path / "old.db")
    conn = sqlite3.connect(old_db)
    conn.execute("""
        CREATE TABLE scan_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            package_name TEXT NOT NULL,
            risk_level TEXT NOT NULL,
            score REAL NOT NULL,
            leak_type TEXT,
            pii_detected TEXT,
            sensitive_detected TEXT,
            detected_threats TEXT,
            confidence REAL DEFAULT 1.0,
            timestamp TEXT NOT NULL,
            user_id TEXT DEFAULT 'anonymous'
        )
    """)
    conn.execute("""
        CREATE TABLE feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            package_name TEXT NOT NULL,
            permissions TEXT,
            is_malware INTEGER NOT NULL,
            user_notes TEXT DEFAULT '',
            timestamp TEXT NOT NULL,
            user_id TEXT DEFAULT 'anonymous'
        )
    """)
    conn.commit()
    conn.close()

    monkeypatch.setattr(db_manager, "DB_PATH", old_db)
    db_manager.init_db()  # must not raise

    conn = sqlite3.connect(old_db)
    cols = {row[1] for row in conn.execute("PRAGMA table_info(scan_history)")}
    conn.close()
    assert "risk_summary" in cols


def test_save_scan_result_without_risk_summary_still_works(tmp_path, monkeypatch):
    """Callers that don't pass risk_summary (e.g. not-yet-updated code) keep working."""
    test_db = str(tmp_path / "test2.db")
    monkeypatch.setattr(db_manager, "DB_PATH", test_db)
    db_manager.init_db()

    db_manager.save_scan_result(
        package_name="com.example.old_caller",
        risk_level="SAFE",
        score=10.0,
        leak_type="Low Risk",
        pii_detected=[],
        sensitive_detected=[],
        detected_threats=[],
    )

    rows = db_manager.get_scan_history()
    assert rows[0]["package_name"] == "com.example.old_caller"
    assert rows[0]["risk_summary"] == ""