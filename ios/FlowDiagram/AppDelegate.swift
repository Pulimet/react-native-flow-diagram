import UIKit
import React
import React_RCTAppDelegate
import ReactAppDependencyProvider
import FlowDiagramModule
import Foundation

@main
class AppDelegate: RCTAppDelegate {
  override func application(_ application: UIApplication, didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey : Any]? = nil) -> Bool {
    FlowDiagramUtil.onAppLaunched(true)
    FlowDiagramUtil.logSync(message: "AppDelegate.didFinishLaunchingWithOptions -> Start (Sync Native Example)")
  
    self.moduleName = "FlowDiagram"
    self.dependencyProvider = RCTAppDependencyProvider()

    // You can add your custom initial props in the dictionary below.
    // They will be passed down to the ViewController used by React Native.
    self.initialProps = [:]
    
    makeNetworkRequest()
    initAsyncLibrary()
    initSyncLibrary()
    
    FlowDiagramUtil.logSync(message: "AppDelegate.didFinishLaunchingWithOptions -> End (Sync Native Example)")

    return super.application(application, didFinishLaunchingWithOptions: launchOptions)
  }

  override func sourceURL(for bridge: RCTBridge) -> URL? {
    self.bundleURL()
  }

  override func bundleURL() -> URL? {
#if DEBUG
    RCTBundleURLProvider.sharedSettings().jsBundleURL(forBundleRoot: "index")
#else
    Bundle.main.url(forResource: "main", withExtension: "jsbundle")
#endif
  }
  
  private func makeNetworkRequest() {
      guard let url = URL(string: "https://api.agify.io/?name=Alexey") else {
          print("AppDelegate -> makeNetworkRequest-> Invalid URL")
          return
      }

      let task = URLSession.shared.dataTask(with: url) { data, response, error in
          if let error = error {
              print("AppDelegate -> makeNetworkRequest -> Network call failed: \(error.localizedDescription)")
              return
          }

          if let httpResponse = response as? HTTPURLResponse {
            // MainActivity.onCreate -> Start - (Sync Native Example)
            FlowDiagramUtil.logAsync(message: "AppDelegate.makeNetworkRequest -> Network call successful(Sync Native Example)")
          }
          // No need to manually close response body in Swift
      }
      task.resume()
  }
  
  private func initAsyncLibrary() {
      // Creates an asynchronous task that doesn't block the current thread.
      Task {
          FlowDiagramUtil.logAsync(message: "AppDelegate.initAsyncLibrary -> Start - (Async Native Example)")
          // Suspends this task for 2 seconds without blocking the thread.
          // The value is in nanoseconds, so 2_000_000_000 is 2 seconds.
          try await Task.sleep(nanoseconds: 2_000_000_000)
          FlowDiagramUtil.logAsync(message: "AppDelegate.initAsyncLibrary -> End - (Async Native Example)")
      }
  }
  
  private func initSyncLibrary() {
      FlowDiagramUtil.logSync(message: "AppDelegate.initSyncLibrary -> Start - (Sync Native Example)")
      // Blocks the current thread for 0.5 seconds.
      Thread.sleep(forTimeInterval: 0.5)
      FlowDiagramUtil.logSync(message: "AppDelegate.initSyncLibrary -> End - (Sync Native Example)")
  }
    
}
