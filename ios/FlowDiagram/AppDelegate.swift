import UIKit
import FlowDiagramModule
import Foundation

@main
class AppDelegate: UIResponder, UIApplicationDelegate {
  func application(_ application: UIApplication, didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey : Any]? = nil) -> Bool {
    FlowDiagram.onAppLaunched()
    FlowDiagram.logSync(message: "AppDelegate.didFinishLaunchingWithOptions -> Start (Sync Native Example)")
  
    makeNetworkRequest()
    initAsyncLibrary()
    initSyncLibrary()
    
    FlowDiagram.logSync(message: "AppDelegate.didFinishLaunchingWithOptions -> End (Sync Native Example)")

    return true
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
            FlowDiagram.logAsync(message: "AppDelegate.makeNetworkRequest -> Network call successful(Sync Native Example)")
          }
          // No need to manually close response body in Swift
      }
      task.resume()
  }
  
  private func initAsyncLibrary() {
      // Creates an asynchronous task that doesn't block the current thread.
      Task {
          FlowDiagram.logAsync(message: "AppDelegate.initAsyncLibrary -> Start - (Async Native Example)")
          // Suspends this task for 2 seconds without blocking the thread.
          // The value is in nanoseconds, so 2_000_000_000 is 2 seconds.
          try await Task.sleep(nanoseconds: 2_000_000_000)
          FlowDiagram.logAsync(message: "AppDelegate.initAsyncLibrary -> End - (Async Native Example)")
      }
  }
  
  private func initSyncLibrary() {
      FlowDiagram.logSync(message: "AppDelegate.initSyncLibrary -> Start - (Sync Native Example)")
      // Blocks the current thread for 0.5 seconds.
      Thread.sleep(forTimeInterval: 0.5)
      FlowDiagram.logSync(message: "AppDelegate.initSyncLibrary -> End - (Sync Native Example)")
  }
    
}
