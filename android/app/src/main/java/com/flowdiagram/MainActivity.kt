package com.flowdiagram

import android.os.Bundle
import com.facebook.react.ReactActivity
import com.facebook.react.ReactActivityDelegate
import com.facebook.react.defaults.DefaultNewArchitectureEntryPoint.fabricEnabled
import com.facebook.react.defaults.DefaultReactActivityDelegate
import net.alexandroid.flowdiagram.LogTime
import net.alexandroid.flowdiagram.LogLevel
import okhttp3.Call
import okhttp3.Callback
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.Response
import java.io.IOException
import com.facebook.react.modules.network.OkHttpClientProvider

class MainActivity : ReactActivity() {

    override fun getMainComponentName(): String = "FlowDiagram"

    override fun createReactActivityDelegate(): ReactActivityDelegate =
        DefaultReactActivityDelegate(this, mainComponentName, fabricEnabled)

    public override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        LogTime.onIntent(intent)
        LogTime.logSync("MainActivity.onCreate -> Start - (Sync Native Example)")
        makeNetworkRequest()
        LogTime.logSync("MainActivity.onCreate -> End - (Sync Native Example)")
    }

    private fun makeNetworkRequest() {
        val request = Request.Builder()
            .url("https://api.agify.io/?name=Alexey")
            .build()
        val okHttpClient = OkHttpClientProvider.getOkHttpClient()
        okHttpClient.newCall(request).enqueue(object : Callback {
            override fun onFailure(call: Call, e: IOException) {
                LogTime.logAsync("MainActivity.makeNetworkRequest -> onFailure - (Async Native Example)")
            }

            override fun onResponse(call: Call, response: Response) {
                LogTime.logAsync("MainActivity.makeNetworkRequest -> onResponse - (Async Native Example)")
                response.body?.close()
            }
        })
    }
}
