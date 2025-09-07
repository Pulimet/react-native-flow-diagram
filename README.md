# Description

A React Native logging utility that enables enhanced, structured logging. It includes built-in support for parsing logs
to extract workflow steps and visualize them as interactive flow diagrams, helping developers easily track and analyze
app behavior and processes.

# What you got

....

# How to use

.....

# Setup 

## Android

1. Add to settings.gradle
    ```groovy
    include ':react-native-flow-diagram'
    project(':react-native-flow-diagram').projectDir = new File(rootProject.projectDir, '../node_modules/react-native-flow-diagram/android')
    ```
2. Sync Gradle
3. Android -> Application class
    ```kotlin
    // import net.alexandroid.flowdiagram.LogTime
    
    override fun onCreate() {
        LogTime.onApplicationOnCreate(true) // <-- Add this line before "super.onCreate()"
        super.onCreate()
        setupOkHttpClient()
        // Remaining code
    }
    ```
4. Setup OkHttpClient with interceptor:
    ```kotlin
    // import okhttp3.OkHttpClient
    // import com.facebook.react.modules.network.OkHttpClientProvider
    // import com.facebook.react.modules.network.ReactCookieJarContainer
    private fun setupOkHttpClient() {
        val okHttpClient = OkHttpClient.Builder()
            .cookieJar(ReactCookieJarContainer())
            .addInterceptor(LogTime.loggingInterceptor)
            .build()

        OkHttpClientProvider.setOkHttpClientFactory {
            okHttpClient
        }
    }
   ```

5. MainActivity -> onCreate()
    ```kotlin
    class RNMainActivity : ReactActivity() {
        public override fun onCreate(savedInstanceState: Bundle?) {
            super.onCreate()
            LogTime.onIntent(intent)
        }
    }
    ```

## iOS

1. Add to AppDelegate.swift
    ```
    import FlowDiagramModule
    
    class AppDelegate: RCTAppDelegate {
        override func application(_ application: UIApplication, didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey : Any]? = nil) -> Bool {
            FlowDiagramUtil.onAppLaunched(true)
            // Remaining code
        }
    }    
    ```

# How to add log events
### RN
### Android
### iOS

# Measurements

