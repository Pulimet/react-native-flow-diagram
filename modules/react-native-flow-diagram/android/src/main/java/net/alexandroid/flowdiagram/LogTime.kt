package net.alexandroid.flowdiagram

import android.content.Context
import android.content.Intent
import okhttp3.Interceptor

/** v1 entry points, kept as thin aliases of [FlowDiagram] until 2.1. Log output (Logcat) was removed. */
@Deprecated("Use FlowDiagram", ReplaceWith("FlowDiagram"))
object LogTime {

    @Deprecated("Use FlowDiagram.init(context, alwaysOn)")
    fun onApplicationOnCreate(logsEnabled: Boolean = false) {
        currentApplication()?.let { FlowDiagram.init(it, logsEnabled) }
    }

    @Deprecated("Use FlowDiagram.init(context, alwaysOn)")
    fun onApplicationOnCreate(context: Context, logsEnabled: Boolean = false) {
        FlowDiagram.init(context, logsEnabled)
    }

    @Deprecated("Use FlowDiagram.interceptor")
    val loggingInterceptor: Interceptor
        get() = FlowDiagram.interceptor

    @Deprecated("Use FlowDiagram.onIntent(intent)")
    fun onIntent(intent: Intent) = FlowDiagram.onIntent(intent)

    @Deprecated("Use FlowDiagram.logSync")
    fun logSync(
        message: String,
        logType: LogType = LogType.AD,
        logLevel: LogLevel = LogLevel.DEBUG
    ) = FlowDiagram.logSync(message, logType, logLevel)

    @Deprecated("Use FlowDiagram.logAsync")
    fun logAsync(
        message: String,
        logType: LogType = LogType.AD,
        logLevel: LogLevel = LogLevel.DEBUG
    ) = FlowDiagram.logAsync(message, logType, logLevel)

    // The v1 signature had no Context. Application.onCreate runs after ActivityThread set the app.
    private fun currentApplication(): Context? = try {
        Class.forName("android.app.ActivityThread").getMethod("currentApplication").invoke(null) as? Context
    } catch (_: Exception) {
        null
    }
}
