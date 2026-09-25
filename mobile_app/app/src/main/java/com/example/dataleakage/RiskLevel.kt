package com.example.dataleakage

/**
 * Single source of truth for the four risk levels: backend code, display
 * name, colour, and emoji. Every screen that shows a risk level (result
 * cards, the speedometer, and the History tab) reads from here instead of
 * keeping its own copy — that's what let the card and History tab colours
 * drift out of sync with each other before this file existed.
 *
 * Colour values match what MainActivity's cards already used. Colours are
 * plain packed-ARGB Int literals (equivalent to Color.parseColor(hex))
 * rather than calls to android.graphics.Color, so this file has no
 * Android-framework dependency and RiskLevelTest.kt can run as a fast, plain
 * JVM unit test (android.graphics.Color.parseColor is a stub outside a real
 * device/emulator and throws in local unit tests).
 *
 * Score thresholds mirror the backend's own boundaries (see main.py's
 * /calibrate endpoint and ml_engine.py's classify_score): SAFE < 30,
 * HANDLE_WITH_CARE 30–55, SUSPICIOUS 55–75, DANGEROUS >= 75.
 */
enum class RiskLevel(
    val code: String,
    val displayName: String,
    val color: Int,
    val emoji: String,
) {
    SAFE("SAFE", "SAFE", 0xFF2ECC71.toInt(), "\uD83D\uDFE2"),                       // 🟢
    HANDLE_WITH_CARE("HANDLE_WITH_CARE", "HANDLE WITH CARE", 0xFFF39C12.toInt(), "\uD83D\uDFE1"), // 🟡
    SUSPICIOUS("SUSPICIOUS", "SUSPICIOUS", 0xFFE67E22.toInt(), "\uD83D\uDFE0"),      // 🟠
    DANGEROUS("DANGEROUS", "DANGEROUS", 0xFFE74C3C.toInt(), "\uD83D\uDD34");         // 🔴

    companion object {
        /**
         * Maps a backend risk_level code to a RiskLevel. An unrecognised or
         * null code falls back to SAFE — matching the behaviour of the old
         * per-screen `when (level) { ... else -> green }` blocks this
         * replaces.
         */
        fun fromCode(code: String?): RiskLevel =
            values().find { it.code == code } ?: SAFE

        /** Maps a 0–100 score to a RiskLevel using the backend's own thresholds. */
        fun forScore(score: Int): RiskLevel = when {
            score >= 75 -> DANGEROUS
            score >= 55 -> SUSPICIOUS
            score >= 30 -> HANDLE_WITH_CARE
            else -> SAFE
        }
    }
}