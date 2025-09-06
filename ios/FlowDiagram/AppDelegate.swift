import UIKit
import React
import React_RCTAppDelegate
import ReactAppDependencyProvider
import FlowDiagramModule

@main
class AppDelegate: RCTAppDelegate {
  override func application(_ application: UIApplication, didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey : Any]? = nil) -> Bool {
    print("AppDelegate -> didFinishLaunchingWithOptions")
    FlowDiagramUtil.onAppLaunched(true)
  
    self.moduleName = "FlowDiagram"
    self.dependencyProvider = RCTAppDependencyProvider()

    // You can add your custom initial props in the dictionary below.
    // They will be passed down to the ViewController used by React Native.
    self.initialProps = [:]
    
    makeNetworkRequest()

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
            FlowDiagramUtil.logSync(message: "AppDelegate -> makeNetworkRequest -> Network call successful: \(httpResponse.statusCode)")
          }
          // No need to manually close response body in Swift
      }
      task.resume()
  }
}
