# Description

A React Native logging utility that enables enhanced, structured logging. It includes built-in support for parsing logs
to extract workflow steps and visualize them as interactive flow diagrams, helping developers easily track and analyze
app behavior and processes.

# Output Demonstration
<img width="100%" alt="Flow Diagram Example" src="https://github.com/user-attachments/assets/f8b9a901-1c85-4bc3-b13d-376d8c1cf1ce" />
<img width="100%" alt="Table with all logs" src="https://github.com/user-attachments/assets/09545e63-e44f-4e85-9012-c54eb7784035" />
<img width="512" height="174" alt="Table wit network requests/responses" src="https://github.com/user-attachments/assets/685193b1-fcdd-4a10-b3f4-94795a294435" />

## How to send log events
Network requests from native and RN logged automatically.

### RN
```typescript
import {logAsync, logSync} from 'react-native-flow-diagram';
logSync('App.tsx -> Start (Sync RN Example)');
logAsync('App.tsx -> Network call successful (Async RN Example)');
```

### Android
```kotlin
// import net.alexandroid.flowdiagram.LogTime
LogTime.logSync("MainActivity.onCreate -> Start - (Sync Native Example)")
LogTime.logAsync("MainActivity.makeNetworkRequest -> onResponse - (Async Native Example)")
```

### iOS
```groovy
FlowDiagramUtil.logSync(message: "AppDelegate.didFinishLaunchingWithOptions (Sync Native Example)")
FlowDiagramUtil.logAsync(message: "AppDelegate.makeNetworkRequest -> Network call successful(Sync Native Example)")
```



# Installation -> Adding to your project
## Android

1. Install npm package
    ```shell
    npm i react-native-flow-diagram
    ```
2. Add to settings.gradle
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

5. MainActivity -> onCreate() (Optional: Support special launch mode)
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
    ```groovy
    import FlowDiagramModule
    
    class AppDelegate: RCTAppDelegate {
        override func application(_ application: UIApplication, didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey : Any]? = nil) -> Bool {
            FlowDiagramUtil.onAppLaunched(true)
            // Remaining code
        }
    }    
    ```


# Installation -> How to run sample project
```shell
    npm install
```
```shell
    cd ios
```
```shell
    pod install
```

Open xCode/Android Studio and launch.

# Launch Measurements ([Working on...])

## Script configuration

### Android

### iOS Simulator

### iOS Real Device

## Launch 


