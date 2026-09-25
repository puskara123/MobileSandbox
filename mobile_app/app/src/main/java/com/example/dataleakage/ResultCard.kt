package com.example.dataleakage

import android.content.Context
import android.graphics.Color
import android.graphics.Typeface
import android.graphics.drawable.Drawable
import android.view.Gravity
import android.view.View
import android.widget.ImageView
import android.widget.LinearLayout
import android.widget.TextView
import com.example.dataleakage.ui.SpeedometerView
import com.google.android.material.card.MaterialCardView

/**
 * Builds a single scan-result card. Used by both the "scan all installed
 * apps" flow and the "pre-install APK" flow in MainActivity, which
 * previously built this same markup by hand in two separate, near-duplicate
 * functions (`addAppResult` / `addPreInstallScanResult`).
 *
 * The two flows differ only in:
 *   - [topExtra]: extra content shown right under the app name (the
 *     pre-install flow's sandbox-hint text; installed-app cards pass null).
 *   - [bottomExtra]: extra content shown after the risk details, before the
 *     feedback row (the pre-install flow's Install/Reject buttons;
 *     installed-app cards pass null).
 *   - [feedbackContent]: each flow builds its own "mark safe / malware"
 *     buttons and click behaviour, since their exact wording/icons differ
 *     and their submitFeedback closures capture different data.
 *
 * The PII / Sensitive detail lines are intentionally left as-is here —
 * Step 4 replaces this block with the plain-English reasons from
 * plain_english.py's /analyze response.
 */
object ResultCard {

    data class Data(
        val appName: String,
        val packageName: String,
        val icon: Drawable?,
        val level: String,
        val score: Int,
        val pii: List<String>,
        val sensitive: List<String>,
    )

    fun build(
        context: Context,
        data: Data,
        topExtra: ((inner: LinearLayout) -> Unit)? = null,
        bottomExtra: ((inner: LinearLayout) -> Unit)? = null,
        feedbackContent: (row: LinearLayout) -> Unit,
    ): MaterialCardView {
        val riskLevel = RiskLevel.fromCode(data.level)

        val cardView = MaterialCardView(context).apply {
            radius = 48f
            cardElevation = 18f
            layoutParams = LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT
            ).also { it.setMargins(0, 0, 0, 48) }
        }

        val row = LinearLayout(context).apply { orientation = LinearLayout.HORIZONTAL }

        val stripe = View(context).apply {
            setBackgroundColor(riskLevel.color)
            layoutParams = LinearLayout.LayoutParams(12, LinearLayout.LayoutParams.MATCH_PARENT)
        }
        row.addView(stripe)

        val inner = LinearLayout(context).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(48, 36, 48, 36)
            layoutParams = LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT
            )
        }

        // ---- Header: icon + app name + package name ----
        val headerRow = LinearLayout(context).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
        }

        val iconView = ImageView(context).apply {
            layoutParams = LinearLayout.LayoutParams(96, 96).also { it.rightMargin = 24 }
            setImageDrawable(data.icon ?: context.packageManager.defaultActivityIcon)
        }

        val nameColumn = LinearLayout(context).apply {
            orientation = LinearLayout.VERTICAL
            layoutParams = LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f)
        }

        val title = TextView(context).apply {
            text = data.appName
            textSize = 20f
            setTextColor(Color.parseColor("#1A237E"))
            typeface = Typeface.DEFAULT_BOLD
        }

        val packageLabel = TextView(context).apply {
            text = data.packageName
            textSize = 12f
            setTextColor(Color.parseColor("#757575"))
        }

        nameColumn.addView(title)
        nameColumn.addView(packageLabel)
        headerRow.addView(iconView)
        headerRow.addView(nameColumn)

        // ---- Badge + single score (was "min - max", always equal in practice) ----
        val badgeAndScore = LinearLayout(context).apply {
            orientation = LinearLayout.HORIZONTAL
            setPadding(0, 16, 0, 16)
        }

        val riskBadge = TextView(context).apply {
            text = riskLevel.displayName
            textSize = 14f
            typeface = Typeface.DEFAULT_BOLD
            setTextColor(riskLevel.color)
            layoutParams = LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f)
        }

        val scoreLabel = TextView(context).apply {
            text = "${data.score} / 100"
            textSize = 28f
            setTextColor(riskLevel.color)
            typeface = Typeface.DEFAULT_BOLD
        }

        badgeAndScore.addView(riskBadge)
        badgeAndScore.addView(scoreLabel)

        val speedometer = SpeedometerView(context).apply {
            layoutParams = LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, 280)
            setScore(data.score)
        }

        // ---- Risk details (Step 4 replaces this block) ----
        val piiText = TextView(context).apply {
            text = "PII: ${if (data.pii.isEmpty()) "None" else data.pii.joinToString(", ")}"
            textSize = 12f
            setTextColor(Color.parseColor("#000000"))
            layoutParams = LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT
            ).also { it.topMargin = 16 }
        }

        val sensitiveText = TextView(context).apply {
            text = "Sensitive: ${if (data.sensitive.isEmpty()) "None" else data.sensitive.joinToString(", ")}"
            textSize = 12f
            setTextColor(Color.parseColor("#000000"))
            layoutParams = LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT
            ).also { it.topMargin = 8 }
        }

        inner.addView(headerRow)
        topExtra?.invoke(inner)
        inner.addView(badgeAndScore)
        inner.addView(speedometer)
        inner.addView(piiText)
        inner.addView(sensitiveText)
        bottomExtra?.invoke(inner)

        val feedbackLayout = LinearLayout(context).apply {
            orientation = LinearLayout.HORIZONTAL
            setPadding(0, 24, 0, 0)
        }
        feedbackContent(feedbackLayout)
        inner.addView(feedbackLayout)

        row.addView(inner)
        cardView.addView(row)
        return cardView
    }
}