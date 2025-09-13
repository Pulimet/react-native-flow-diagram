package com.flowdiagram

import android.app.Application
import com.facebook.react.PackageList
import com.facebook.react.ReactApplication
import com.facebook.react.ReactHost
import com.facebook.react.ReactNativeHost
import com.facebook.react.ReactPackage
import com.facebook.react.defaults.DefaultNewArchitectureEntryPoint.load
import com.facebook.react.defaults.DefaultReactHost.getDefaultReactHost
import com.facebook.react.defaults.DefaultReactNativeHost
import com.facebook.react.soloader.OpenSourceMergedSoMapping
import com.facebook.soloader.SoLoader
import net.alexandroid.flowdiagram.LogTime
import okhttp3.OkHttpClient
import com.facebook.react.modules.network.OkHttpClientProvider
import com.facebook.react.modules.network.ReactCookieJarContainer


class MainApplication : Application(), ReactApplication {

    override fun onCreate() {
        LogTime.onApplicationOnCreate(true)
        LogTime.logSync("MainApplication.onCreate -> Start - (Sync Native Example)")
        super.onCreate()
        setupOkHttpClient()
        initRN()
        LogTime.logSync("MainApplication.onCreate -> End - Sync NativeExample - (Sync Native Example)")
    }

    private fun setupOkHttpClient() {
        val okHttpClient = OkHttpClient.Builder()
            .cookieJar(ReactCookieJarContainer())
            .addInterceptor(LogTime.loggingInterceptor)
            .build()

        OkHttpClientProvider.setOkHttpClientFactory {
            okHttpClient
        }
        LogTime.logSync("MainApplication.setupOkHttpClient -> Done - (Sync Native Example)")
    }

    private fun initRN() {
        SoLoader.init(this, OpenSourceMergedSoMapping)
        load()
    }

    // React Native Setup
    override val reactNativeHost: ReactNativeHost =
        object : DefaultReactNativeHost(this) {
            override fun getPackages(): List<ReactPackage> =
                PackageList(this).packages.apply {
                    // Packages that cannot be autolinked yet can be added manually here, for example:
                    // add(MyReactNativePackage())
                }

            override fun getJSMainModuleName(): String = "index"

            override fun getUseDeveloperSupport(): Boolean = BuildConfig.DEBUG

            override val isNewArchEnabled: Boolean = BuildConfig.IS_NEW_ARCHITECTURE_ENABLED
            override val isHermesEnabled: Boolean = BuildConfig.IS_HERMES_ENABLED
        }

    override val reactHost: ReactHost
        get() = getDefaultReactHost(applicationContext, reactNativeHost)
}
