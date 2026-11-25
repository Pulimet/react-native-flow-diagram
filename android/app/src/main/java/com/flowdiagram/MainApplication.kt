package com.flowdiagram

import android.app.Application
import com.facebook.react.PackageList
import com.facebook.react.ReactApplication
import com.facebook.react.ReactHost
import com.facebook.react.ReactNativeApplicationEntryPoint.loadReactNative
import com.facebook.react.defaults.DefaultReactHost.getDefaultReactHost
import net.alexandroid.flowdiagram.FlowDiagram
import okhttp3.OkHttpClient
import com.facebook.react.modules.network.OkHttpClientProvider
import com.facebook.react.modules.network.ReactCookieJarContainer


class MainApplication : Application(), ReactApplication {

    override fun onCreate() {
        FlowDiagram.init(this)
        FlowDiagram.logSync("MainApplication.onCreate -> Start - (Sync Native Example)")
        super.onCreate()
        setupOkHttpClient()
        loadReactNative(this)
        FlowDiagram.logSync("MainApplication.onCreate -> End - Sync NativeExample - (Sync Native Example)")
    }

    private fun setupOkHttpClient() {
        val okHttpClient = OkHttpClient.Builder()
            .cookieJar(ReactCookieJarContainer())
            .addInterceptor(FlowDiagram.interceptor)
            .build()

        OkHttpClientProvider.setOkHttpClientFactory {
            okHttpClient
        }
        FlowDiagram.logSync("MainApplication.setupOkHttpClient -> Done - (Sync Native Example)")
    }

    override val reactHost: ReactHost by lazy {
        getDefaultReactHost(
            context = applicationContext,
            packageList = PackageList(this).packages.apply {
                // Packages that cannot be autolinked yet can be added manually here, for example:
                // add(MyReactNativePackage())
            },
        )
    }
}
