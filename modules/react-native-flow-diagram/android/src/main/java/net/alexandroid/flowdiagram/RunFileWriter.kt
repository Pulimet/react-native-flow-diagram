package net.alexandroid.flowdiagram

import android.content.ContentValues
import android.content.Context
import android.content.Intent
import android.os.Build
import android.os.Environment
import android.provider.MediaStore
import org.json.JSONObject
import java.io.File
import java.io.OutputStream

/**
 * Phase 0 spike: writes a JSON Lines file per run when the launch intent carries
 * FlowDiagramFlag=true and FlowDiagramRunId=<id>.
 * Primary: getExternalFilesDir("flowdiagram")/runs/<runId>.jsonl
 * Fallback (FlowDiagramSink=downloads): Download/flowdiagram/<package>/<runId>.jsonl via MediaStore.
 */
object RunFileWriter {
    private const val EXTRA_FLAG = "FlowDiagramFlag"
    private const val EXTRA_RUN_ID = "FlowDiagramRunId"
    private const val EXTRA_SINK = "FlowDiagramSink"

    private val lines = mutableListOf<String>()
    private var runId: String? = null
    private var startMs = 0L

    fun start(context: Context, intent: Intent) {
        if (!intent.getBooleanExtra(EXTRA_FLAG, false)) return
        val id = intent.getStringExtra(EXTRA_RUN_ID) ?: return
        runId = id
        startMs = System.currentTimeMillis()
        lines.clear()
        line("run_start", JSONObject().put("platform", "android").put("api", Build.VERSION.SDK_INT)
            .put("debuggable", (context.applicationInfo.flags and android.content.pm.ApplicationInfo.FLAG_DEBUGGABLE) != 0))
        line("event", JSONObject().put("name", "spike.event.1"))
        line("event", JSONObject().put("name", "spike.event.2"))
        line("run_end", JSONObject())
        val downloads = intent.getStringExtra(EXTRA_SINK) == "downloads"
        Thread {
            if (downloads) writeDownloads(context, id) else writePrimary(context, id)
        }.start()
    }

    private fun line(type: String, body: JSONObject) {
        body.put("type", type).put("runId", runId).put("t", System.currentTimeMillis() - startMs)
        lines.add(body.toString())
    }

    private fun payload(): String = lines.joinToString("\n", postfix = "\n")

    private fun writePrimary(context: Context, id: String) {
        val base = context.getExternalFilesDir("flowdiagram") ?: return
        val dir = File(base, "runs").apply { mkdirs() }
        File(dir, "$id.jsonl").writeText(payload())
    }

    private fun writeDownloads(context: Context, id: String) {
        val rel = "${Environment.DIRECTORY_DOWNLOADS}/flowdiagram/${context.packageName}"
        val values = ContentValues().apply {
            put(MediaStore.MediaColumns.DISPLAY_NAME, "$id.jsonl")
            put(MediaStore.MediaColumns.MIME_TYPE, "application/octet-stream")
            put(MediaStore.MediaColumns.RELATIVE_PATH, rel)
        }
        val uri = context.contentResolver.insert(MediaStore.Downloads.EXTERNAL_CONTENT_URI, values) ?: return
        val out: OutputStream = context.contentResolver.openOutputStream(uri) ?: return
        out.use { it.write(payload().toByteArray()) }
    }
}
