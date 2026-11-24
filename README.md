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
        // The true parameter enables detailed logging for app launch measurement
        // Another option is false - it will log only when measurement script 
        // is launched with -extra True (it will use option 5 below)
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
            // The true parameter enables detailed logging for app launch measurement
            // Another option is false - it will log only when measurement script launched with -extra True 
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
"flow-setup": "cd node_modules/react-native-flow-diagram/py && python3 -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt",
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

The host needs only `adb` (Android) or Xcode command line tools (iOS). Measure **release builds**
(Android release APK, iOS Release configuration with Development signing).
The script launches the app with the FlowDiagram flag and a fresh run id, pulls the JSON Lines run file
the app wrote, and builds the CSV, averages and PNG. Raw run files are kept in `<output-dir>/<date>/raw/`.
See `docs/v2/phase4-python.md` for details.

## Launch Measurement Flow

```shell
    npm run flow:android -- --launch_times 10
    npm run flow:ios_simulator -- --launch_times 10
    npm run flow:ios_device -- --launch_times 10 --udid <udid>
    npm run flow -- --from-dir output/26-11-24/raw      # rebuild reports from saved run files, no device
```

Emulator and simulator results are labeled "functional, not representative". Use physical devices for numbers.

## Configuration Options

```
  usage: main.py [-h] [--platform {android,ios_device,ios_simulator,auto}] [--output-dir OUTPUT_DIR]
                 [--launch_times N] [--package PACKAGE] [--activity ACTIVITY] [--bundle_id BUNDLE_ID]
                 [--serial SERIAL] [--udid UDID] [--compile-mode {speed-profile,speed,verify,none}]
                 [--t0 {process_start,app_init}] [--sink {auto,downloads}] [--allow-debuggable]
                 [--wait_time SECONDS] [--poll-interval SECONDS] [--stable-polls N] [--timeout SECONDS]
                 [--from-dir DIR] [--open_csv OPEN_CSV] [--open_png OPEN_PNG]
```

| Option | Default | Meaning |
|---|---|---|
| `--platform` | `android` | Target. `auto` picks the only ready target. |
| `--launch_times` | 1 | Number of cold launches. |
| `--serial` / `--udid` | auto | Pick the Android device or the iOS device/simulator when several are connected. |
| `--compile-mode` | `speed-profile` | Android dexopt mode applied before measuring. `none` keeps the current state. |
| `--t0` | `process_start` | Time origin. `app_init` gives numbers comparable with v1. |
| `--wait_time` | 10 | Seconds to wait after launch before the first fetch. |
| `--poll-interval`, `--stable-polls`, `--timeout` | 1, 2, 60 | Completion detection when the app wrote no `run_end`. |
| `--sink` | `auto` | Android run file location (`downloads` forces the Download fallback). |
| `--allow-debuggable` | off | Measure a debug build anyway. |
| `--from-dir` | | Build reports from saved `*.jsonl` files. |

The v1 `--extra` flag is ignored (the flag is always passed). Logcat / os_log collection was removed.
