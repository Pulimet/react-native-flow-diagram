# Description

A React Native logging utility that enables enhanced, structured logging. It includes built-in support for parsing logs to extract workflow steps and visualize them as interactive flow diagrams, helping developers easily track and analyze app behavior and processes.

# Getting Started
## Android
1. Add to settings.gradle
    ```groovy
    include ':react-native-flow-diagram'
    project(':react-native-flow-diagram').projectDir = new File(rootProject.projectDir, '../node_modules/react-native-flow-diagram/android')
    ```
2. Sync Gradle
3. Android -> Application class
    ```kotlin
    // import net.alexandroid.flowdiagram.FlowDiagramModule
    
    override fun onCreate() {
        FlowDiagramModule.onApplicationOnCreate() // <-- Add this line before "super.onCreate()"
        super.onCreate()
        // Remaining code
    }
    ```

## iOS
1. Add to AppDelegate.swift
    ```
    import FlowDiagramModule
    
    class AppDelegate: RCTAppDelegate {
      override func application(_ application: UIApplication, didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey : Any]? = nil) -> Bool {
        FlowDiagramUtil.onAppLaunched()
        // Remaining code
      }
    }    
    ```
