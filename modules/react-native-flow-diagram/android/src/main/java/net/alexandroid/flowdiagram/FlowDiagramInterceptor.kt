package net.alexandroid.flowdiagram

import okhttp3.Interceptor
import okhttp3.Response
import java.util.concurrent.atomic.AtomicInteger

internal class FlowDiagramInterceptor : Interceptor {
    private val nextReqId = AtomicInteger(1)

    override fun intercept(chain: Interceptor.Chain): Response {
        val request = chain.request()
        val url = request.url.toString()
        if (isIgnored(url)) return chain.proceed(request)
        val reqId = nextReqId.getAndIncrement()
        FlowDiagram.netRequest(reqId, url)
        val startNanos = System.nanoTime()
        val response = chain.proceed(request)
        val durMs = (System.nanoTime() - startNanos) / 1_000_000
        FlowDiagram.netResponse(reqId, url, response.code, durMs)
        return response
    }

    // Same filter as v1: dev server and local network traffic is not app traffic
    private fun isIgnored(url: String) =
        url.contains("symbolicate") || url.contains("localhost") ||
            url.contains("10.0") || url.contains("192.168")
}
