package net.alexandroid.flowdiagram

import android.content.ContentValues
import android.content.Context
import android.os.Build
import android.os.Environment
import android.provider.MediaStore
import java.io.BufferedWriter
import java.io.File
import java.io.OutputStream
import java.io.OutputStreamWriter

internal class StreamSink(stream: OutputStream) : Sink {
    private val writer = BufferedWriter(OutputStreamWriter(stream, Charsets.UTF_8), 16 * 1024)

    override fun write(line: String) {
        writer.write(line)
        writer.write("\n")
    }

    override fun flush() = writer.flush()

    override fun close() = writer.close()
}

internal object Sinks {
    private const val KEEP_RUNS = 20

    /** Primary: getExternalFilesDir("flowdiagram")/runs/<runId>.jsonl. Falls back to Downloads when unavailable. */
    fun open(context: Context, runId: String, forceDownloads: Boolean): Sink? {
        if (!forceDownloads) {
            try {
                openPrimary(context, runId)?.let { return it }
            } catch (_: Exception) {
            }
        }
        return openDownloads(context, runId)
    }

    private fun openPrimary(context: Context, runId: String): Sink? {
        val base = context.getExternalFilesDir("flowdiagram") ?: return null
        val dir = File(base, "runs")
        if (!dir.isDirectory && !dir.mkdirs()) return null
        pruneOldRuns(dir)
        return StreamSink(File(dir, "$runId.jsonl").outputStream())
    }

    private fun pruneOldRuns(dir: File) {
        val files = dir.listFiles { f -> f.name.endsWith(".jsonl") } ?: return
        files.sortedByDescending { it.lastModified() }.drop(KEEP_RUNS - 1).forEach { it.delete() }
    }

    // MediaStore.Downloads needs API 29+
    private fun openDownloads(context: Context, runId: String): Sink? {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.Q) return null
        val rel = "${Environment.DIRECTORY_DOWNLOADS}/flowdiagram/${context.packageName}"
        val values = ContentValues().apply {
            put(MediaStore.MediaColumns.DISPLAY_NAME, "$runId.jsonl")
            put(MediaStore.MediaColumns.MIME_TYPE, "application/octet-stream")
            put(MediaStore.MediaColumns.RELATIVE_PATH, rel)
        }
        val resolver = context.contentResolver
        val uri = resolver.insert(MediaStore.Downloads.EXTERNAL_CONTENT_URI, values) ?: return null
        val out = resolver.openOutputStream(uri) ?: return null
        return StreamSink(out)
    }
}
