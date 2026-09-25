package com.example.dataleakage.api

data class AnalysisRequest(
    val package_name: String,
    val permissions: List<String>
)

data class AnalysisResponse(
    val app: String,
    val risk_level: String,
    val score: Int,
    val score_min: Int,
    val score_max: Int,
    val score_precise: Double = 0.0,
    val leak_type: String,
    val pii_detected: List<String>,
    val sensitive_detected: List<String>,
    val detected_threats: List<String>,
    // Added in Step 2 (analysis_server/plain_english.py). Nullable, not
    // defaulted: Gson leaves a field missing from the JSON as null, not as
    // whatever default this data class declares — so these three MUST be
    // nullable for AnalysisResponse to deserialize safely against a server
    // from before Step 2, where these keys don't exist in the response at
    // all. See RiskExplanation.kt for how the app falls back when they're null.
    val risk_summary: String? = null,
    val risk_reasons: List<RiskReason>? = null,
    val risk_patterns: List<String>? = null,
    val minor_permissions: List<String>? = null
)

/** One plain-English reason, matching plain_english.py's risk_reasons entries exactly. */
data class RiskReason(
    val group: String,
    val title: String,
    val access: String,
    val why: String
)

data class FeedbackRequest(
    val package_name: String,
    val permissions: List<String>,
    val is_malware: Boolean,
    val user_notes: String = ""
)

data class FeedbackResponse(
    val status: String,
    val `package`: String = "",
    val is_malware: Boolean = false
)

data class ScanRecord(
    val id: Int = 0,
    val package_name: String,
    val risk_level: String,
    val score: Double,
    val leak_type: String?,
    val pii_detected: String?,
    val sensitive_detected: String?,
    val detected_threats: String?,
    val timestamp: String?,
    // Added in Step 2; null/blank for scans saved before that migration.
    val risk_summary: String? = null
)

data class ScanHistoryResponse(
    val scans: List<ScanRecord>
)