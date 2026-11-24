package com.flowdiagram

import android.content.Intent
import android.os.Bundle
import com.facebook.react.ReactActivity
import com.facebook.react.ReactActivityDelegate
import com.facebook.react.defaults.DefaultNewArchitectureEntryPoint.fabricEnabled
import com.facebook.react.defaults.DefaultReactActivityDelegate
import net.alexandroid.flowdiagram.FlowDiagram
import okhttp3.Call
import okhttp3.Callback
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.Response
import java.io.IOException
import com.facebook.react.modules.network.OkHttpClientProvider
import kotlinx.coroutines.CoroutineScope
import kotlin.coroutines.CoroutineContext
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.delay


class MainActivity : ReactActivity(), CoroutineScope {
    override val coroutineContext: CoroutineContext = Dispatchers.IO

    override fun getMainComponentName(): String = "FlowDiagram"

    override fun createReactActivityDelegate(): ReactActivityDelegate =
        DefaultReactActivityDelegate(this, mainComponentName, fabricEnabled)

    public override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        FlowDiagram.onIntent(intent)
        FlowDiagram.logSync("MainActivity.onCreate -> Start - (Sync Native Example)")
        makeNetworkRequest()
        initAsyncLibrary()
        initSyncLibrary()
        FlowDiagram.logSync("MainActivity.onCreate -> End - (Sync Native Example)")
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        FlowDiagram.onIntent(intent)
    }

    private fun makeNetworkRequest() {
        val request = Request.Builder()
            .url("https://api.agify.io/?name=Alexey")
            .build()
        val okHttpClient = OkHttpClientProvider.getOkHttpClient()
        okHttpClient.newCall(request).enqueue(object : Callback {
            override fun onFailure(call: Call, e: IOException) {
                FlowDiagram.logAsync("MainActivity.makeNetworkRequest -> onFailure - (Async Native Example)")
            }

            override fun onResponse(call: Call, response: Response) {
                FlowDiagram.logAsync("MainActivity.makeNetworkRequest -> onResponse - (Async Native Example)")
                response.body?.close()
            }
        })
    }

    private fun initAsyncLibrary() {
        launch {
            FlowDiagram.logAsync("MainActivity.initAsyncLibrary -> Start - (Async Native Example)")
            delay(2000)
            FlowDiagram.logAsync("MainActivity.initAsyncLibrary -> End - (Async Native Example)")
        }
    }

    private fun initSyncLibrary() {
        FlowDiagram.logSync("MainActivity.initSyncLibrary -> Start - (Sync Native Example)")
        Thread.sleep(500)
        FlowDiagram.logSync("MainActivity.initSyncLibrary -> End - (Sync Native Example)")
    }
}
