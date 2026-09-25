package com.example.dataleakage

import android.os.Bundle
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView
import androidx.cardview.widget.CardView
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import com.example.dataleakage.api.RetrofitClient
import com.example.dataleakage.api.ScanRecord
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

class ScanHistoryActivity : AppCompatActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_scan_history)

        val rv = findViewById<RecyclerView>(R.id.rvHistory)
        rv.layoutManager = LinearLayoutManager(this)

        lifecycleScope.launch {
            try {
                val response = withContext(Dispatchers.IO) {
                    RetrofitClient.api.getScanHistory()
                }
                rv.adapter = ScanHistoryAdapter(response.scans)
            } catch (e: Exception) {
                Toast.makeText(this@ScanHistoryActivity,
                    "Failed to load history: ${e.message}", Toast.LENGTH_LONG).show()
            }
        }
    }
}

// ─────────────────────────────────────────────────────────
//  RecyclerView Adapter
// ─────────────────────────────────────────────────────────

class ScanHistoryAdapter(private val items: List<ScanRecord>)
    : RecyclerView.Adapter<ScanHistoryAdapter.VH>() {

    inner class VH(view: View) : RecyclerView.ViewHolder(view) {
        val tvPackage   = view.findViewById<TextView>(R.id.tvPackage)
        val tvRiskLevel = view.findViewById<TextView>(R.id.tvRiskLevel)
        val tvScore     = view.findViewById<TextView>(R.id.tvScore)
        val tvTimestamp = view.findViewById<TextView>(R.id.tvTimestamp)
    }

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): VH {
        val v = LayoutInflater.from(parent.context)
            .inflate(R.layout.item_scan_history, parent, false)
        return VH(v)
    }

    override fun getItemCount() = items.size

    override fun onBindViewHolder(holder: VH, position: Int) {
        val item = items[position]

        holder.tvPackage.text = "📦 ${item.package_name}"

        // RiskLevel is the single source of truth for colour/emoji/name, so
        // this can never drift out of sync with the result cards again —
        // it previously had its own hard-coded set where SUSPICIOUS and
        // HANDLE_WITH_CARE's emoji/colour were accidentally swapped.
        val riskLevel = RiskLevel.fromCode(item.risk_level)
        holder.tvRiskLevel.text = "${riskLevel.emoji} ${riskLevel.displayName}"
        holder.tvRiskLevel.backgroundTintList =
            android.content.res.ColorStateList.valueOf(riskLevel.color)

        holder.tvScore.text = "Score: ${"%.1f".format(item.score)}"

        // Show only date + time portion (trim microseconds)
        val ts = item.timestamp?.take(19)?.replace("T", "  ") ?: ""
        holder.tvTimestamp.text = ts
    }
}