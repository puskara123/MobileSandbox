"""
test_plain_english.py — Tests for plain_english.py.

These tests never touch the trained ML model: plain_english.py only reads
static tables off ml_engine (PERMISSION_RISK_TABLE, DANGEROUS_COMBOS,
HIGH_RISK_THRESHOLD, classify_permission), none of which require
load_or_train(). No autouse DB/model fixture is needed here.
"""

import re

import ml_engine
import plain_english as pe


ANDROID_PREFIX = "android.permission."


def _full(short_perm: str) -> str:
    return ANDROID_PREFIX + short_perm


# ------------------------------------------------------------------
# 1. Every permission in PERMISSION_RISK_TABLE belongs to a group.
# ------------------------------------------------------------------

def test_every_scored_permission_has_a_group():
    missing = [
        perm for perm in ml_engine.PERMISSION_RISK_TABLE
        if perm not in pe.PERMISSION_TO_GROUP
    ]
    assert not missing, f"Permissions with no plain-English group: {missing}"


# ------------------------------------------------------------------
# 2. Every permission scoring >= HIGH_RISK_THRESHOLD lands in a major group.
# ------------------------------------------------------------------

def test_high_risk_permissions_are_in_major_groups():
    mismatched = []
    for perm, risk in ml_engine.PERMISSION_RISK_TABLE.items():
        bucket = pe.PERMISSION_TO_GROUP.get(perm)
        if bucket is None:
            continue  # already reported by the previous test
        kind, _group_id = bucket
        if risk >= ml_engine.HIGH_RISK_THRESHOLD and kind != "major":
            mismatched.append((perm, risk, kind))
    assert not mismatched, (
        f"High-risk permissions (>= {ml_engine.HIGH_RISK_THRESHOLD}) "
        f"not placed in a major group: {mismatched}"
    )


def test_low_risk_permissions_are_not_in_major_groups():
    """The reverse check: a group shouldn't be 'major' just because one of
    its members happens to be low-risk while its siblings are high-risk is
    fine (group severity is driven by the riskiest member) — but a group
    made up entirely of sub-threshold permissions should never be major."""
    for group_id, group in pe.MAJOR_GROUP_DEFS.items():
        best = max(ml_engine.PERMISSION_RISK_TABLE.get(p, 0.0) for p in group["perms"])
        assert best >= ml_engine.HIGH_RISK_THRESHOLD, (
            f"Major group '{group_id}' has no member scoring >= "
            f"{ml_engine.HIGH_RISK_THRESHOLD} (best={best})"
        )
    for group_id, group in pe.MINOR_GROUP_DEFS.items():
        best = max(ml_engine.PERMISSION_RISK_TABLE.get(p, 0.0) for p in group["perms"])
        assert best < ml_engine.HIGH_RISK_THRESHOLD, (
            f"Minor group '{group_id}' has a member scoring "
            f">= {ml_engine.HIGH_RISK_THRESHOLD} (best={best}) and should be major"
        )


# ------------------------------------------------------------------
# 3. DANGEROUS_COMBOS <-> PATTERN_SENTENCES coverage, both directions.
# ------------------------------------------------------------------

def test_every_dangerous_combo_has_a_sentence():
    missing = [
        combo for combo, _mult in ml_engine.DANGEROUS_COMBOS
        if frozenset(combo) not in pe.PATTERN_SENTENCES
    ]
    assert not missing, f"DANGEROUS_COMBOS with no plain-English sentence: {missing}"


def test_every_pattern_sentence_matches_a_real_combo():
    known_combos = {frozenset(combo) for combo, _mult in ml_engine.DANGEROUS_COMBOS}
    extra = [combo for combo in pe.PATTERN_SENTENCES if combo not in known_combos]
    assert not extra, f"Pattern sentences for combos ml_engine doesn't score: {extra}"


# ------------------------------------------------------------------
# 4. Grouped permissions collapse to one reason.
# ------------------------------------------------------------------

def test_sms_trio_produces_one_reason():
    result = pe.explain(
        [_full("READ_SMS"), _full("SEND_SMS"), _full("RECEIVE_SMS")],
        "DANGEROUS",
    )
    assert len(result["risk_reasons"]) == 1
    assert result["risk_reasons"][0]["group"] == "sms"


# ------------------------------------------------------------------
# 5. Reasons come out worst-first.
# ------------------------------------------------------------------

def test_reasons_are_worst_first():
    # SEND_SMS (9.8) > ACCESS_BACKGROUND_LOCATION (9.5) > CAMERA (7.0)
    result = pe.explain(
        [_full("CAMERA"), _full("SEND_SMS"), _full("ACCESS_BACKGROUND_LOCATION")],
        "DANGEROUS",
    )
    groups_in_order = [r["group"] for r in result["risk_reasons"]]
    assert groups_in_order == ["sms", "background_location", "camera"]


def test_reasons_tie_break_keeps_table_order():
    # READ_CONTACTS (8.5) and ACCESS_FINE_LOCATION (8.5) tie exactly.
    # MAJOR_GROUP_DEFS lists "contacts" before "location".
    result = pe.explain(
        [_full("ACCESS_FINE_LOCATION"), _full("READ_CONTACTS")],
        "SUSPICIOUS",
    )
    groups_in_order = [r["group"] for r in result["risk_reasons"]]
    assert groups_in_order == ["contacts", "location"]


# ------------------------------------------------------------------
# 6. Fallback behaviour for permissions with no named group.
# ------------------------------------------------------------------

def test_unknown_standard_pii_permission_falls_back():
    # Not a real Android permission, but shaped like one and matches a
    # PII keyword ("LOCATION") so classify_permission should flag it as PII.
    result = pe.explain([_full("ACCESS_MOCK_LOCATION")], "HANDLE_WITH_CARE")
    assert any(r["group"] == "other_pii" for r in result["risk_reasons"])


def test_unknown_standard_device_permission_falls_back_to_minor():
    # Matches a SENSITIVE keyword ("BLUETOOTH") but isn't one of our exact
    # named permissions.
    result = pe.explain([_full("BLUETOOTH_PRIVILEGED")], "SAFE")
    assert pe.FALLBACK_DEVICE_LABEL in result["minor_permissions"]
    assert result["risk_reasons"] == []


def test_unknown_standard_low_risk_permission_counted_as_technical():
    result = pe.explain([_full("READ_LOGS")], "SAFE")
    assert any("Other technical permissions" in label for label in result["minor_permissions"])


def test_vendor_permission_never_becomes_a_reason():
    result = pe.explain(["com.google.android.c2dm.permission.RECEIVE"], "SAFE")
    assert result["risk_reasons"] == []
    assert any("Other technical permissions" in label for label in result["minor_permissions"])


def test_technical_fallback_counts_are_combined():
    result = pe.explain(
        ["com.google.android.c2dm.permission.RECEIVE", _full("READ_LOGS")],
        "SAFE",
    )
    assert "Other technical permissions (2)" in result["minor_permissions"]


# ------------------------------------------------------------------
# 7. No jargon leaks into any output text.
# ------------------------------------------------------------------

CODE_PATTERN = re.compile(r"\b[A-Z][A-Z_]{2,}\b")


def _all_output_strings(result):
    strings = [result["risk_summary"]]
    for reason in result["risk_reasons"]:
        strings.extend([reason["title"], reason["access"], reason["why"]])
    strings.extend(result["risk_patterns"])
    strings.extend(result["minor_permissions"])
    return strings


def test_no_jargon_in_a_fully_loaded_example():
    result = pe.explain(
        [
            _full("READ_SMS"), _full("SEND_SMS"), _full("RECEIVE_SMS"),
            _full("READ_CONTACTS"), _full("ACCESS_FINE_LOCATION"),
            _full("ACCESS_BACKGROUND_LOCATION"), _full("CAMERA"),
            _full("RECORD_AUDIO"), _full("RECEIVE_BOOT_COMPLETED"),
            _full("INSTALL_PACKAGES"), _full("VIBRATE"),
            "com.google.android.c2dm.permission.RECEIVE",
        ],
        "DANGEROUS",
    )
    # Everyday abbreviations that happen to be all-caps but are NOT
    # permission-style jargon — a non-technical reader already knows these.
    ALLOWED_ACRONYMS = {"SMS", "OTP", "OTPS"}

    for text in _all_output_strings(result):
        assert "android.permission" not in text.lower(), text
        codes = [m for m in CODE_PATTERN.findall(text) if m not in ALLOWED_ACRONYMS]
        assert not codes, f"Looks like a permission code leaked into: {text!r} ({codes})"


# ------------------------------------------------------------------
# 8. Each summary rule is reachable.
# ------------------------------------------------------------------

def test_summary_safe_no_reasons():
    result = pe.explain([_full("VIBRATE"), _full("INTERNET")], "SAFE")
    assert result["risk_summary"] == "It doesn't ask for access to your personal information."


def test_summary_safe_one_reason():
    result = pe.explain([_full("CAMERA")], "SAFE")
    assert result["risk_summary"] == (
        "Low overall risk. The most sensitive thing it can do is use your camera."
    )


def test_summary_two_or_more_reasons():
    result = pe.explain([_full("READ_SMS"), _full("SEND_SMS"), _full("READ_CONTACTS")], "SUSPICIOUS")
    assert result["risk_summary"] == (
        "Mainly because it can read your text messages and see your contacts."
    )


def test_summary_one_reason_non_safe():
    result = pe.explain([_full("CAMERA"), _full("VIBRATE")], "HANDLE_WITH_CARE")
    assert result["risk_summary"] == "Mainly because it can use your camera."


def test_summary_non_safe_no_major_reasons():
    result = pe.explain([_full("VIBRATE"), _full("INTERNET")], "HANDLE_WITH_CARE")
    assert result["risk_summary"] == (
        "No single permission stands out, but its overall mix of permissions raised the risk."
    )


# ------------------------------------------------------------------
# 9. No empty text fields; "why" text stays short.
# ------------------------------------------------------------------

def test_no_group_definition_has_empty_or_overlong_text():
    for group_id, group in pe.MAJOR_GROUP_DEFS.items():
        for field in ("title", "access", "why", "phrase"):
            assert group[field].strip(), f"{group_id}.{field} is empty"
        assert len(group["why"]) <= 120, f"{group_id}.why is {len(group['why'])} chars"
    for group_id, group in pe.MINOR_GROUP_DEFS.items():
        assert group["label"].strip(), f"{group_id}.label is empty"
    for sentence in pe.PATTERN_SENTENCES.values():
        assert sentence.strip()
    for text in (pe.FALLBACK_PII_TITLE, pe.FALLBACK_PII_ACCESS,
                 pe.FALLBACK_PII_WHY, pe.FALLBACK_PII_PHRASE, pe.FALLBACK_DEVICE_LABEL):
        assert text.strip()
    assert len(pe.FALLBACK_PII_WHY) <= 120


def test_explain_output_has_no_empty_strings():
    result = pe.explain(
        [_full("READ_SMS"), _full("CAMERA"), _full("VIBRATE")],
        "SUSPICIOUS",
    )
    assert result["risk_summary"].strip()
    for reason in result["risk_reasons"]:
        for field in ("group", "title", "access", "why"):
            assert reason[field].strip()
    for label in result["minor_permissions"]:
        assert label.strip()


# ------------------------------------------------------------------
# Extra: patterns are capped at 2 and sorted most-severe-first.
# ------------------------------------------------------------------

def test_patterns_capped_at_two_and_sorted():
    # Matches 3 combos: full spyware (1.50), SMS trojan (1.40), surveillance (1.45)
    result = pe.explain(
        [
            _full("ACCESS_FINE_LOCATION"), _full("READ_CONTACTS"), _full("READ_SMS"),
            _full("SEND_SMS"), _full("RECEIVE_SMS"),
            _full("CAMERA"), _full("RECORD_AUDIO"),
        ],
        "DANGEROUS",
    )
    assert len(result["risk_patterns"]) == 2
    assert result["risk_patterns"][0] == pe.PATTERN_SENTENCES[
        frozenset({"ACCESS_FINE_LOCATION", "READ_CONTACTS", "READ_SMS"})
    ]
    assert result["risk_patterns"][1] == pe.PATTERN_SENTENCES[
        frozenset({"CAMERA", "RECORD_AUDIO", "ACCESS_FINE_LOCATION"})
    ]


def test_no_pattern_match_gives_empty_list():
    result = pe.explain([_full("VIBRATE")], "SAFE")
    assert result["risk_patterns"] == []
