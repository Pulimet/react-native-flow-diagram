package net.alexandroid.flowdiagram

import android.app.Activity
import android.app.Application
import android.content.ComponentCallbacks2
import android.content.Context
import android.content.Intent
import android.content.pm.ApplicationInfo
import android.content.res.Configuration
import android.os.Build
import android.os.Bundle
import android.os.Process
import android.os.SystemClock
import okhttp3.Interceptor
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import java.util.concurrent.Executors

/**
 * FlowDiagram v2 recorder. Call [init] first in Application.onCreate and [onIntent] from the launch
 * Activity (onCreate and onNewIntent). Events are buffered until the intent says whether to record.
 * When recording, one JSON Lines file per launch is written, see docs/v2/schema.md.
 */
object FlowDiagram {
    const val EXTRA_FLAG = "FlowDiagramFlag"
    const val EXTRA_RUN_ID = "FlowDiagramRunId"
    const val EXTRA_SINK = "FlowDiagramSink"
    private const val SINK_DOWNLOADS = "downloads"

    @Volatile
    private var recorder: Recorder? = null
    private var appContext: Context? = null
    private var alwaysOn = false
    private var t0Name = "process_start"
    private var appInitMs = 0.0

    /** OkHttp interceptor recording request and response pairs. */
    val interceptor: Interceptor = FlowDiagramInterceptor()

    @JvmStatic
    @JvmOverloads
    @Synchronized
    fun init(context: Context, alwaysOn: Boolean = false) {
        if (recorder != null) return
        val app = context.applicationContext ?: context
        // One file per launch: other processes of the app do not record.
        if (processName(app) != app.packageName) return
        this.alwaysOn = alwaysOn
        appContext = app

        val nowNanos = SystemClock.elapsedRealtimeNanos()
        val startMs = if (Build.VERSION.SDK_INT >= 33) {
            Process.getStartRequestedElapsedRealtime()
        } else {
            Process.getStartElapsedRealtime()
        }
        var t0Nanos = startMs * 1_000_000L
        val sinceStartMs = (nowNanos - t0Nanos) / 1_000_000.0
        if (sinceStartMs < 0 || sinceStartMs > 60_000) {
            // Implausible process start, fall back to app init as t0
            t0Nanos = nowNanos
            t0Name = "app_init"
            appInitMs = 0.0
        } else {
            t0Name = "process_start"
            appInitMs = sinceStartMs
        }

        val executor = Executors.newSingleThreadScheduledExecutor { r ->
            Thread(r, "FlowDiagramWriter").apply { isDaemon = true }
        }
        recorder = Recorder({ SystemClock.elapsedRealtimeNanos() }, t0Nanos, executor)

        (app as? Application)?.let { registerFlushHooks(it) }
    }

    /** Reads the launch flag and run id. Without the flag the buffer is dropped and recording is off for good. */
    @JvmStatic
    fun onIntent(intent: Intent?) {
        val rec = recorder ?: return
        if (rec.state != Recorder.State.PENDING) return
        val ctx = appContext ?: return
        val flagged = intent?.getBooleanExtra(EXTRA_FLAG, false) == true
        if (!flagged && !alwaysOn) {
            rec.disable()
            return
        }
        val runId = intent?.getStringExtra(EXTRA_RUN_ID)?.takeIf { isSafeRunId(it) } ?: timestampRunId()
        val downloads = intent?.getStringExtra(EXTRA_SINK) == SINK_DOWNLOADS
        rec.enable({ header(ctx, runId) }) { Sinks.open(ctx, runId, downloads) }
    }

    @JvmStatic
    @JvmOverloads
    fun logSync(
        message: String,
        logType: LogType = LogType.AD,
        logLevel: LogLevel = LogLevel.DEBUG
    ) {
        recorder?.event(logType.src(), "SYNC", logLevel.name, message)
    }

    @JvmStatic
    @JvmOverloads
    fun logAsync(
        message: String,
        logType: LogType = LogType.AD,
        logLevel: LogLevel = LogLevel.DEBUG
    ) {
        recorder?.event(logType.src(), "ASYNC", logLevel.name, message)
    }

    /** Writes run_end and stops recording. Optional: the script pulls the file without it. */
    @JvmStatic
    fun end() {
        recorder?.end("flush")
    }

    internal fun netRequest(reqId: Int, url: String) {
        recorder?.net("REQ", reqId, url)
    }

    internal fun netResponse(reqId: Int, url: String, status: Int, durMs: Long) {
        recorder?.net("RSP", reqId, url, status, durMs)
    }

    private fun LogType.src() = if (this == LogType.RN) "RN" else "AD"

    private fun header(ctx: Context, runId: String): String {
        val debuggable = (ctx.applicationInfo.flags and ApplicationInfo.FLAG_DEBUGGABLE) != 0
        val version = try {
            ctx.packageManager.getPackageInfo(ctx.packageName, 0).versionName
        } catch (_: Exception) {
            null
        }
        return JsonLines.header(
            runId = runId,
            appId = ctx.packageName,
            appVersion = version ?: "",
            build = if (debuggable) "debug" else "release",
            debuggable = debuggable,
            os = Build.VERSION.RELEASE ?: "",
            device = Build.MODEL ?: "",
            t0 = t0Name,
            appInitMs = appInitMs
        )
    }

    private fun registerFlushHooks(app: Application) {
        app.registerComponentCallbacks(object : ComponentCallbacks2 {
            override fun onTrimMemory(level: Int) {
                recorder?.flush()
            }

            override fun onConfigurationChanged(newConfig: Configuration) {}
            override fun onLowMemory() {
                recorder?.flush()
            }
        })
        app.registerActivityLifecycleCallbacks(object : Application.ActivityLifecycleCallbacks {
            override fun onActivityStopped(activity: Activity) {
                recorder?.flush()
            }

            override fun onActivityCreated(activity: Activity, savedInstanceState: Bundle?) {}
            override fun onActivityStarted(activity: Activity) {}
            override fun onActivityResumed(activity: Activity) {}
            override fun onActivityPaused(activity: Activity) {}
            override fun onActivitySaveInstanceState(activity: Activity, outState: Bundle) {}
            override fun onActivityDestroyed(activity: Activity) {}
        })
    }

    private fun processName(ctx: Context): String? =
        if (Build.VERSION.SDK_INT >= 28) {
            Application.getProcessName()
        } else {
            ctx.packageName
        }

    // Run id becomes a file name
    private fun isSafeRunId(id: String) = id.isNotEmpty() && id.length <= 128 && id.all { it.isLetterOrDigit() || it in "-_." } && !id.startsWith(".")

    private fun timestampRunId() = SimpleDateFormat("yyyyMMdd-HHmmss", Locale.US).format(Date())
}
