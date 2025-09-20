# Description

A React Native logging utility that enables enhanced, structured logging. It includes built-in support for parsing logs
to extract workflow steps and visualize them as interactive flow diagrams, helping developers easily track and analyze
app behavior and processes.

### Event Reporting Flow
<img width="555" height="158" alt="image" src="https://github.com/user-attachments/assets/114e4c11-5d09-4c0c-be27-0574e36bcbc6" />

### Measurement Script Flow
<img width="1037" height="272" alt="image" src="https://github.com/user-attachments/assets/dfb4ffb9-2921-47aa-ab39-231f3fd8e0ee" />


# Output Demonstration
<img width="100%" alt="Flow Diagram Example" src="https://github.com/user-attachments/assets/f8b9a901-1c85-4bc3-b13d-376d8c1cf1ce" />
<img width="100%" alt="Table with all logs" src="https://github.com/user-attachments/assets/09545e63-e44f-4e85-9012-c54eb7784035" />
<img width="512" height="174" alt="Table wit network requests/responses" src="https://github.com/user-attachments/assets/685193b1-fcdd-4a10-b3f4-94795a294435" />
<img width="989" height="784" alt="Example of the events shown in the diagram" src="https://github.com/user-attachments/assets/6f02efef-64a9-4170-9013-38ede201b8b8" />


## How to send log events
Network requests from native (iOS & Android) and React Native are logged automatically.

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
## React Native

1. Install npm package
    ```shell
    npm i react-native-flow-diagram
    ```
    ```shell
    cd ios
    ```    
    ```shell
    pod install
    ```
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

# Launch Measurements

## Script configuration

Add to your package.json:

```json
"scripts": {
  "flow-setup": "cd node_modules/react-native-flow-diagram/py && python3 -m venv .venv && . .venv/bin/activate && PIP_TRUSTED_HOST='pypi.org pypi.python.org files.pythonhosted.org' PIP_DEFAULT_TIMEOUT=1000 pip install poetry && poetry install",
  "flow": "node_modules/react-native-flow-diagram/py/.venv/bin/python node_modules/react-native-flow-diagram/py/src/flow/main.py",
  "flow:android": "npm run flow -- --platform android",
  "flow:ios_simulator": "npm run flow -- --platform ios_simulator",
  "flow:ios_device": "npm run flow -- --platform ios_device"
}
```    

Launch the setup script once:
```shell
    npm run flow-setup
```

## Launch Measurement Flow

### Android
```shell
    npm run flow:android
``` 

Launch with extras: **TBD**

### iOS Simulator
```shell
    npm run flow:ios_simulator
```

Launch with bundle settings: **TBD**


### iOS Real Device
```shell
    npm run flow:ios_device
```

Launch with bundle settings: **TBD**




