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
 * The risk-details block (built by [buildDetailsSection]) shows the
 * plain-English summary, reasons, dangerous-combo warnings and minor
 * permissions from Step 2's /analyze response — or, for a server from
 * before that step, falls back to the old raw PII/Sensitive lines. See
 * RiskExplanation.kt for how that fallback is detected.
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
        val explanation: RiskExplanation,
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

        // ---- Risk details: plain-English explanation, or the old raw
        // PII/Sensitive lines when talking to a pre-Step-2 server ----
        val detailsSection = buildDetailsSection(context, data.explanation, data.pii, data.sensitive)

        inner.addView(headerRow)
        topExtra?.invoke(inner)
        inner.addView(badgeAndScore)
        inner.addView(speedometer)
        inner.addView(detailsSection)
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

    /**
     * The risk-details block, top to bottom: summary sentence, "What this
     * app can access" reasons (hidden if none), dangerous-combo warning
     * box(es), then a collapsible "Other minor permissions (N)". Falls back
     * to the old raw PII/Sensitive lines entirely when [explanation] has no
     * plain English available (a pre-Step-2 server).
     */
    private fun buildDetailsSection(
        context: Context,
        explanation: RiskExplanation,
        pii: List<String>,
        sensitive: List<String>,
    ): LinearLayout {
        val section = LinearLayout(context).apply {
            orientation = LinearLayout.VERTICAL
            layoutParams = LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT
            ).also { it.topMargin = 16 }
        }

        if (!explanation.hasPlainEnglish) {
            // Old backend fallback — same raw lines as before Step 4, just
            // bumped from 12sp to match this step's larger, more readable sizes.
            section.addView(TextView(context).apply {
                text = "PII: ${if (pii.isEmpty()) "None" else pii.joinToString(", ")}"
                textSize = 14f
                setTextColor(Color.parseColor("#000000"))
            })
            section.addView(TextView(context).apply {
                text = "Sensitive: ${if (sensitive.isEmpty()) "None" else sensitive.joinToString(", ")}"
                textSize = 13f
                setTextColor(Color.parseColor("#424242"))
                setPadding(0, 8, 0, 0)
            })
            return section
        }

        // ---- 1. Summary sentence ----
        section.addView(TextView(context).apply {
            text = explanation.summary
            textSize = 14f
            typeface = Typeface.DEFAULT_BOLD
            setTextColor(Color.parseColor("#212121"))
        })

        // ---- 2. "What this app can access" (hidden entirely if no reasons) ----
        if (explanation.reasons.isNotEmpty()) {
            section.addView(TextView(context).apply {
                text = "What this app can access"
                textSize = 14f
                typeface = Typeface.DEFAULT_BOLD
                setTextColor(Color.parseColor("#1A237E"))
                setPadding(0, 20, 0, 8)
            })
            for (reason in explanation.reasons) {
                section.addView(LinearLayout(context).apply {
                    orientation = LinearLayout.VERTICAL
                    setPadding(0, 8, 0, 8)
                    addView(TextView(context).apply {
                        text = reason.title
                        textSize = 14f
                        typeface = Typeface.DEFAULT_BOLD
                        setTextColor(Color.parseColor("#212121"))
                    })
                    addView(TextView(context).apply {
                        text = reason.access
                        textSize = 14f
                        setTextColor(Color.parseColor("#424242"))
                    })
                    addView(TextView(context).apply {
                        text = "Why it matters: ${reason.why}"
                        textSize = 13f
                        setTextColor(Color.parseColor("#757575"))
                        setPadding(0, 4, 0, 0)
                    })
                })
            }
        }

        // ---- 3. Dangerous-combo warning box(es) ----
        for (pattern in explanation.patterns) {
            section.addView(TextView(context).apply {
                text = "\u26A0 $pattern" // ⚠
                textSize = 13f
                setTextColor(Color.parseColor("#E65100"))
                setBackgroundColor(Color.parseColor("#FFF3E0"))
                setPadding(24, 16, 24, 16)
                layoutParams = LinearLayout.LayoutParams(
                    LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT
                ).also { it.topMargin = 12 }
            })
        }

        // ---- 4. Collapsible "Other minor permissions (N)" ----
        if (explanation.minorPermissions.isNotEmpty()) {
            val count = explanation.minorPermissions.size
            val minorList = TextView(context).apply {
                text = explanation.minorPermissions.joinToString("\n") { "\u2022 $it" } // •
                textSize = 13f
                setTextColor(Color.parseColor("#616161"))
                setPadding(24, 8, 0, 0)
                visibility = View.GONE
            }
            var expanded = false
            val minorHeader = TextView(context).apply {
                text = "\u25B8 Other minor permissions ($count)" // ▸
                textSize = 13f
                setTextColor(Color.parseColor("#5C6BC0"))
                setPadding(0, 16, 0, 0)
                setOnClickListener {
                    expanded = !expanded
                    minorList.visibility = if (expanded) View.VISIBLE else View.GONE
                    text = "${if (expanded) "\u25BE" else "\u25B8"} Other minor permissions ($count)" // ▾ / ▸
                }
            }
            section.addView(minorHeader)
            section.addView(minorList)
        }

        return section
    }
}