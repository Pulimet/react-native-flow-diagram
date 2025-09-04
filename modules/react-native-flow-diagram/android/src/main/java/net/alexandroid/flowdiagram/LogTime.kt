package net.alexandroid.flowdiagram

import android.content.Intent
import android.util.Log

object LogTime {
    var appOnCreateTime: Long = 0
    var isLogEnabled = false
    private const val LOG_TAG = "FlowDiagramTime"
    private const val INTENT_FLAG = "FlowDiagramFlag"
    private const val LOG_MS_CHARS = 9
    private var recentLogTime: Long = 0
    private var messageCounter = HashMap<String, Int>() // HashMap to store message and its counter

    fun onApplicationOnCreate(logsEnabled: Boolean = false) {
        appOnCreateTime = System.currentTimeMillis()
        recentLogTime = appOnCreateTime
        isLogEnabled = logsEnabled
    }

    val loggingInterceptor = LoggingInterceptor()

    fun onIntent(intent: Intent) {
        isLogEnabled = intent.getBooleanExtra(INTENT_FLAG, false)
    }

    fun getTimeSinceAppLaunch(): String = (System.currentTimeMillis() - appOnCreateTime).toString()

    fun logNetwork(
        message: String,
        logType: LogType = LogType.AD,
        responseCode: Int = 0,
        elapsedTime: Long = 0
    ) {
        when (logType) {
            LogType.NE_REQUEST -> logNeRequest(message)
            LogType.NE_RESPONSE -> logNeResponse(message, responseCode, elapsedTime)
            else -> {}
        }
    }

    fun logSync(
        message: String,
        logType: LogType = LogType.AD,
        logLevel: LogLevel = LogLevel.DEBUG
    ) {
        val type = addSpaces(logType.name, 2)
        val messageWithSuffix = addSuffixToMessage(message)
        logI("${sinceCreated()} => [$type][${logLevel.name}][SYNC] $messageWithSuffix")
        recentLogTime = System.currentTimeMillis()
    }

    fun logAsync(
        message: String,
        logType: LogType = LogType.AD,
        logLevel: LogLevel = LogLevel.DEBUG
    ) {
        val type = addSpaces(logType.name, 2)
        val messageWithSuffix = addSuffixToMessage(message)
        logI("${sinceCreated()} => [$type][${logLevel.name}][ASYNC] $messageWithSuffix")
    }


    private fun logNeRequest(message: String) {
        val messageWithSuffix = addSuffixToMessage("[NET][REQ] $message")
        logI("${sinceCreated()} => $messageWithSuffix")
    }

    private fun logNeResponse(message: String, responseCode: Int, elapsedTime: Long) {
        val messageWithSuffix = addSuffixToMessage("[NET][RSP] $message")
        logI(
            "${sinceCreated()} => " +
                    "$messageWithSuffix, " +
                    "Status: $responseCode, " +
                    "Elapsed time: $elapsedTime"
        )
    }

    // Helpers
    private fun logI(text: String) = Log.i(LOG_TAG, text)


    private fun sinceCreated() =
        addSpaces(
            formatChunksOfThree(
                System.currentTimeMillis() - appOnCreateTime
            )
        )

    private fun sinceRecent() =
        addSpaces(
            formatChunksOfThree(
                System.currentTimeMillis() - recentLogTime
            )
        )

    private fun formatChunksOfThree(input: Long) = if (input < 1000) {
        input.toString()
    } else {
        input.toString()
            .reversed()
            .chunked(3)
            .joinToString(" ")
            .reversed()
    }

    private fun zeroTime() =
        addSpaces(
            "0"
        )

    private fun addSpaces(time: String, spacesNum: Int = LOG_MS_CHARS): String {
        val text = StringBuilder(time)
        val spaces = spacesNum - text.length
        if (spaces > 0) text.append(" ".repeat(spaces))
        return text.toString()
    }

    private fun addSuffixToMessage(message: String): String {
        val counter = messageCounter.getOrDefault(message, 0)
        if (counter > 0) {
            messageCounter[message] = counter + 1
            return "$message($counter)"
        } else {
            messageCounter[message] = 1
            return message
        }
    }

}