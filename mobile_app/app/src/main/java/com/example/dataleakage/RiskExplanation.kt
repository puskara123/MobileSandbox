package com.example.dataleakage

import com.example.dataleakage.api.AnalysisResponse
import com.example.dataleakage.api.RiskReason

/**
 * What a result card (or a History row) actually needs to display for the
 * plain-English explanation of a scan. Deliberately plain Kotlin with no
 * Android imports, so RiskExplanationTest.kt can run as a fast, plain-JVM
 * unit test.
 *
 * [hasPlainEnglish] is false only when the server didn't send the new
 * fields at all (a pre-Step-2 backend) — never merely because a SAFE app
 * happens to have zero reasons, which is a normal, valid result.
 */
data class RiskExplanation(
    val hasPlainEnglish: Boolean,
    val summary: String,
    val reasons: List<RiskReason>,
    val patterns: List<String>,
    val minorPermissions: List<String>,
) {
    companion object {
        /**
         * Builds a RiskExplanation from an /analyze response.
         *
         * risk_summary is the fallback signal: all four new fields were
         * added together in Step 2, so a server that doesn't know about
         * them yet leaves all four as null (Gson's behaviour for a JSON
         * key that's simply absent, not present-but-empty). Checking just
         * this one field is enough to detect that case.
         */
        fun from(response: AnalysisResponse): RiskExplanation {
            val summary = response.risk_summary
                ?: return RiskExplanation(
                    hasPlainEnglish = false,
                    summary = "",
                    reasons = emptyList(),
                    patterns = emptyList(),
                    minorPermissions = emptyList(),
                )
            return RiskExplanation(
                hasPlainEnglish = true,
                summary = summary,
                reasons = response.risk_reasons ?: emptyList(),
                patterns = response.risk_patterns ?: emptyList(),
                minorPermissions = response.minor_permissions ?: emptyList(),
            )
        }
    }
}