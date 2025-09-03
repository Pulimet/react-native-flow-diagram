package net.alexandroid.flowdiagram

import okhttp3.Interceptor
import okhttp3.Response

class LoggingInterceptor : Interceptor {
    override fun intercept(chain: Interceptor.Chain): Response {
        val request = chain.request()
        val requestUrl = request.url.toString()
        log(requestUrl, LogType.NE_REQUEST)
        val startTime = System.currentTimeMillis()
        val response = chain.proceed(request)
        val endTime = System.currentTimeMillis()
        val responseCode = response.code
        val elapsedTime = endTime - startTime
        log(requestUrl, LogType.NE_RESPONSE, responseCode, elapsedTime)
        return response
    }

    private fun log(
        requestUrl: String,
        logType: LogType,
        responseCode: Int = 0,
        elapsedTime: Long = 0
    ) {
        if (!requestUrl.contains("symbolicate") && !requestUrl.contains("localhost")) {
            LogTime.logNetwork(requestUrl, logType, responseCode, elapsedTime)
        }
    }
}