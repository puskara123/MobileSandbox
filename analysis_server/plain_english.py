"""
plain_english.py — Turns raw Android permissions into plain-English risk
explanations for non-technical users.

This module only reads static data from ml_engine (the permission risk
table, the dangerous-combo list, and the classify_permission fallback).
It never calls ml_engine.load_or_train() or touches the trained model, so
importing this module — or running its test suite — never loads or trains
the sklearn model.

Public entry point:
    explain(permissions, level) -> {
        "risk_summary":      str,
        "risk_reasons":      [{"group", "title", "access", "why"}, ...],  # worst first
        "risk_patterns":     [str, ...],   # at most 2, most severe first
        "minor_permissions": [str, ...],
    }
"""

import ml_engine

# ============================================================
# Group definitions
# ============================================================
# Each major group carries the four pieces of text shown to the user, plus
# a short "phrase" used only to build the one-line summary sentence.
#
# Whether a group counts as "major" or "minor" is NOT set by hand here —
# it falls out of which dict it's defined in, and a test in
# test_plain_english.py checks that placement against
# ml_engine.PERMISSION_RISK_TABLE's own HIGH_RISK_THRESHOLD (6.0), so the
# two tables can't silently drift apart.

MAJOR_GROUP_DEFS = {
    "sms": {
        "perms": ["READ_SMS", "SEND_SMS", "RECEIVE_SMS", "RECEIVE_MMS"],
        "title": "Text messages",
        "access": "Can read and send your SMS",
        "why": "Could see your OTPs and bank alerts, or send paid messages without you knowing",
        "phrase": "read your text messages",
    },
    "call_log": {
        "perms": ["READ_CALL_LOG", "WRITE_CALL_LOG"],
        "title": "Call history",
        "access": "Can see and change your list of calls",
        "why": "Could learn who you talk to and when, or erase evidence of its own calls",
        "phrase": "see your call history",
    },
    "phone_calls": {
        "perms": ["CALL_PHONE", "ANSWER_PHONE_CALLS"],
        "title": "Phone calls",
        "access": "Can make or answer calls on its own",
        "why": "Could call premium-rate numbers or answer calls without asking you first",
        "phrase": "make calls on your behalf",
    },
    "phone_identity": {
        "perms": ["READ_PHONE_STATE", "READ_PHONE_NUMBERS"],
        "title": "Phone identity",
        "access": "Can see your phone number and device details",
        "why": "Could be used to identify and track this exact phone across different apps",
        "phrase": "identify your exact phone",
    },
    "contacts": {
        "perms": ["READ_CONTACTS", "WRITE_CONTACTS"],
        "title": "Contacts",
        "access": "Can see everyone in your contacts",
        "why": "Your friends' and family's numbers could be shared or used for spam",
        "phrase": "see your contacts",
    },
    "location": {
        "perms": ["ACCESS_FINE_LOCATION", "ACCESS_COARSE_LOCATION", "FOREGROUND_SERVICE_LOCATION"],
        "title": "Location",
        "access": "Can see where you are while you're using the app",
        "why": "Could reveal your home, workplace, or daily movements",
        "phrase": "see your location",
    },
    "background_location": {
        "perms": ["ACCESS_BACKGROUND_LOCATION"],
        "title": "Location (background)",
        "access": "Can see where you are even when the app is closed",
        "why": "Could track your movements and daily routine around the clock",
        "phrase": "track you even when the app is closed",
    },
    "accounts": {
        "perms": ["GET_ACCOUNTS", "AUTHENTICATE_ACCOUNTS", "MANAGE_ACCOUNTS",
                  "USE_CREDENTIALS", "READ_PROFILE", "READ_SOCIAL_STREAM"],
        "title": "Accounts",
        "access": "Can see accounts on your phone and use saved sign-in details",
        "why": "Could access other apps or services you're already signed into",
        "phrase": "use your saved accounts",
    },
    "camera": {
        "perms": ["CAMERA"],
        "title": "Camera",
        "access": "Can take photos or video",
        "why": "Could capture images of you or your surroundings without a clear reason",
        "phrase": "use your camera",
    },
    "microphone": {
        "perms": ["RECORD_AUDIO"],
        "title": "Microphone",
        "access": "Can record audio",
        "why": "Could listen to conversations while the app is running",
        "phrase": "record audio",
    },
    "files": {
        "perms": ["READ_EXTERNAL_STORAGE", "WRITE_EXTERNAL_STORAGE",
                  "READ_MEDIA_IMAGES", "READ_MEDIA_VIDEO", "READ_MEDIA_AUDIO"],
        "title": "Photos and files",
        "access": "Can see and change your photos, videos, and other files",
        "why": "Could view or delete personal photos and documents stored on your phone",
        "phrase": "see your photos and files",
    },
    "all_files": {
        "perms": ["MANAGE_EXTERNAL_STORAGE"],
        "title": "All files",
        "access": "Can see and change nearly every file on your phone",
        "why": "Goes beyond its own files to reach almost anything stored on your device",
        "phrase": "access almost every file on your phone",
    },
    "install_apps": {
        "perms": ["INSTALL_PACKAGES", "REQUEST_INSTALL_PACKAGES"],
        "title": "Installing apps",
        "access": "Can install other apps",
        "why": "Could quietly add more software to your phone without asking each time",
        "phrase": "install other apps",
    },
    "draw_over_apps": {
        "perms": ["SYSTEM_ALERT_WINDOW"],
        "title": "Drawing over other apps",
        "access": "Can show content on top of whatever app you're using",
        "why": "Could show fake buttons or login screens to trick you",
        "phrase": "draw over other apps",
    },
    "health_sensors": {
        "perms": ["BODY_SENSORS"],
        "title": "Body sensors",
        "access": "Can read health sensors, like your heart rate",
        "why": "Could reveal sensitive health information about you",
        "phrase": "read your body sensors",
    },
}

MINOR_GROUP_DEFS = {
    "activity": {
        "perms": ["ACTIVITY_RECOGNITION"],
        "label": "Detect physical activity (walking, driving, etc.)",
    },
    "nearby": {
        "perms": ["BLUETOOTH", "BLUETOOTH_ADMIN", "BLUETOOTH_CONNECT",
                  "BLUETOOTH_SCAN", "NEARBY_WIFI_DEVICES", "NFC",
                  "ACCESS_WIFI_STATE", "CHANGE_WIFI_STATE"],
        "label": "Connect to nearby devices and Wi-Fi",
    },
    "biometrics": {
        "perms": ["USE_BIOMETRIC", "USE_FINGERPRINT"],
        "label": "Use fingerprint or face unlock",
    },
    "autostart": {
        "perms": ["RECEIVE_BOOT_COMPLETED"],
        "label": "Start automatically when your phone turns on",
    },
    "background": {
        "perms": ["FOREGROUND_SERVICE", "WAKE_LOCK", "SCHEDULE_EXACT_ALARM"],
        "label": "Keep running in the background",
    },
    "internet": {
        "perms": ["INTERNET", "ACCESS_NETWORK_STATE", "CHANGE_NETWORK_STATE"],
        "label": "Connect to the internet",
    },
    "notifications": {
        "perms": ["POST_NOTIFICATIONS", "ACCESS_NOTIFICATION_POLICY", "VIBRATE"],
        "label": "Send notifications or vibrate your phone",
    },
    "basic_settings": {
        "perms": ["SET_WALLPAPER", "SET_ALARM", "EXPAND_STATUS_BAR", "FLASHLIGHT",
                  "READ_SYNC_SETTINGS", "WRITE_SYNC_SETTINGS"],
        "label": "Change minor phone settings",
    },
    "purchases": {
        "perms": ["BILLING"],
        "label": "Handle in-app purchases",
    },
}

# ============================================================
# Dangerous-combo sentences
# ============================================================
# Keyed by the exact permission sets ml_engine.DANGEROUS_COMBOS already
# scores. test_plain_english.py checks every combo there has a sentence
# here, and vice versa, so the two lists can't quietly diverge.

PATTERN_SENTENCES = {
    frozenset({"ACCESS_FINE_LOCATION", "READ_CONTACTS", "READ_SMS"}):
        "Together, these could let someone track where you go, see who you know, "
        "and read your private messages.",
    frozenset({"SEND_SMS", "RECEIVE_SMS", "READ_SMS"}):
        "Together, these let an app read, send, and receive texts on its own — "
        "including sending paid messages without you noticing.",
    frozenset({"CAMERA", "RECORD_AUDIO", "ACCESS_FINE_LOCATION"}):
        "Together, these could let an app watch, listen to, and track you at the same time.",
    frozenset({"INSTALL_PACKAGES", "SYSTEM_ALERT_WINDOW"}):
        "Together, these could let an app install other apps and draw fake screens "
        "on top of what you're using, without your say-so.",
    frozenset({"CAMERA", "RECORD_AUDIO"}):
        "Together, these let an app record video and audio at the same time.",
    frozenset({"ACCESS_BACKGROUND_LOCATION", "READ_CONTACTS"}):
        "Together, these could let someone track your location even when the app "
        "is closed, and see who you know.",
    frozenset({"RECEIVE_BOOT_COMPLETED", "INSTALL_PACKAGES"}):
        "Together, these let an app start itself automatically and install other "
        "apps without being opened by you.",
}

# ============================================================
# Fallback text for permissions with no named group
# ============================================================

FALLBACK_PII_GROUP = "other_pii"
FALLBACK_PII_TITLE = "Other personal information"
FALLBACK_PII_ACCESS = "Can access other personal information not listed above"
FALLBACK_PII_WHY = "This permission isn't common, so it's worth checking what the app needs it for"
FALLBACK_PII_PHRASE = "access other personal information"

FALLBACK_DEVICE_LABEL = "Other phone features"

SAFE_LEVEL = "SAFE"


# ============================================================
# Derived lookups (built once at import time)
# ============================================================

def _build_permission_to_group():
    mapping = {}
    for group_id, group in MAJOR_GROUP_DEFS.items():
        for p in group["perms"]:
            mapping[p] = ("major", group_id)
    for group_id, group in MINOR_GROUP_DEFS.items():
        for p in group["perms"]:
            mapping[p] = ("minor", group_id)
    return mapping


PERMISSION_TO_GROUP = _build_permission_to_group()


def _short_key(full_perm: str) -> str:
    return full_perm.strip().split(".")[-1].upper()


# ============================================================
# Public API
# ============================================================

def explain(permissions, level):
    """
    permissions: iterable of permission strings, e.g. "android.permission.READ_SMS"
                 or a bare "READ_SMS", or a vendor permission such as
                 "com.google.android.c2dm.permission.RECEIVE".
    level: one of ml_engine's four risk codes ("SAFE", "HANDLE_WITH_CARE",
           "SUSPICIOUS", "DANGEROUS"). Anything else is treated like a
           non-SAFE level.
    """
    short_to_original = {}
    for p in permissions:
        short_to_original.setdefault(_short_key(p), p)
    short_keys = set(short_to_original.keys())

    # ---- Named major groups present in this app, worst (highest risk
    #      permission actually present) first. Ties keep MAJOR_GROUP_DEFS
    #      order because sort() is stable.
    major_reasons = []
    for group_id, group in MAJOR_GROUP_DEFS.items():
        present = [p for p in group["perms"] if p in short_keys]
        if not present:
            continue
        present_max = max(ml_engine.PERMISSION_RISK_TABLE.get(p, 0.0) for p in present)
        major_reasons.append({
            "group": group_id,
            "title": group["title"],
            "access": group["access"],
            "why": group["why"],
            "phrase": group["phrase"],
            "_sort": present_max,
        })
    major_reasons.sort(key=lambda r: r["_sort"], reverse=True)

    # ---- Named minor groups present, table order.
    minor_labels = []
    for group_id, group in MINOR_GROUP_DEFS.items():
        if any(p in short_keys for p in group["perms"]):
            minor_labels.append(group["label"])

    # ---- Anything not covered by a named group.
    other_technical_count = 0
    saw_other_pii = False
    saw_other_device = False
    for key in short_keys:
        if key in PERMISSION_TO_GROUP:
            continue
        original = short_to_original[key]
        if original.strip().lower().startswith("android.permission."):
            category = ml_engine.classify_permission(key)
            if category == "PII":
                saw_other_pii = True
            elif category == "SENSITIVE":
                saw_other_device = True
            else:
                other_technical_count += 1
        else:
            other_technical_count += 1

    if saw_other_pii:
        major_reasons.append({
            "group": FALLBACK_PII_GROUP,
            "title": FALLBACK_PII_TITLE,
            "access": FALLBACK_PII_ACCESS,
            "why": FALLBACK_PII_WHY,
            "phrase": FALLBACK_PII_PHRASE,
        })
    if saw_other_device:
        minor_labels.append(FALLBACK_DEVICE_LABEL)
    if other_technical_count > 0:
        minor_labels.append(f"Other technical permissions ({other_technical_count})")

    summary = _build_summary(level, major_reasons)
    risk_patterns = _match_patterns(short_keys)

    risk_reasons = [
        {"group": r["group"], "title": r["title"], "access": r["access"], "why": r["why"]}
        for r in major_reasons
    ]

    return {
        "risk_summary": summary,
        "risk_reasons": risk_reasons,
        "risk_patterns": risk_patterns,
        "minor_permissions": minor_labels,
    }


def _build_summary(level, major_reasons):
    if level == SAFE_LEVEL:
        if not major_reasons:
            return "It doesn't ask for access to your personal information."
        return f"Low overall risk. The most sensitive thing it can do is {major_reasons[0]['phrase']}."
    if len(major_reasons) >= 2:
        return f"Mainly because it can {major_reasons[0]['phrase']} and {major_reasons[1]['phrase']}."
    if len(major_reasons) == 1:
        return f"Mainly because it can {major_reasons[0]['phrase']}."
    return "No single permission stands out, but its overall mix of permissions raised the risk."


def _match_patterns(short_keys):
    matches = []
    for combo_perms, multiplier in ml_engine.DANGEROUS_COMBOS:
        if combo_perms.issubset(short_keys):
            sentence = PATTERN_SENTENCES.get(frozenset(combo_perms))
            if sentence:
                matches.append((multiplier, sentence))
    matches.sort(key=lambda m: m[0], reverse=True)
    return [sentence for _, sentence in matches[:2]]


# ============================================================
# Manual wording review: `python plain_english.py`
# ============================================================

if __name__ == "__main__":
    samples = {
        "Messaging app (com.example.messenger)": (
            "HANDLE_WITH_CARE",
            [
                "android.permission.READ_CONTACTS",
                "android.permission.READ_SMS",
                "android.permission.SEND_SMS",
                "android.permission.INTERNET",
                "android.permission.VIBRATE",
            ],
        ),
        "Flashlight app (com.example.flashlight)": (
            "SAFE",
            [
                "android.permission.CAMERA",
                "android.permission.VIBRATE",
            ],
        ),
        "Spyware-like app (com.example.suspicious)": (
            "DANGEROUS",
            [
                "android.permission.ACCESS_FINE_LOCATION",
                "android.permission.ACCESS_BACKGROUND_LOCATION",
                "android.permission.READ_CONTACTS",
                "android.permission.READ_SMS",
                "android.permission.CAMERA",
                "android.permission.RECORD_AUDIO",
                "android.permission.RECEIVE_BOOT_COMPLETED",
                "com.google.android.c2dm.permission.RECEIVE",
            ],
        ),
    }

    for name, (level, perms) in samples.items():
        print("=" * 70)
        print(name, f"[{level}]")
        result = explain(perms, level)
        print("\nSummary:", result["risk_summary"])
        print("\nWhat this app can access:")
        for reason in result["risk_reasons"]:
            print(f"  - {reason['title']}: {reason['access']}")
            print(f"      Why it matters: {reason['why']}")
        if result["risk_patterns"]:
            print("\nPatterns:")
            for sentence in result["risk_patterns"]:
                print(f"  ⚠ {sentence}")
        if result["minor_permissions"]:
            print("\nMinor permissions:", ", ".join(result["minor_permissions"]))
        print()
