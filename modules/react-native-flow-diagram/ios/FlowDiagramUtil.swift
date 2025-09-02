import Foundation

public struct FlowDiagramUtil {
    // Static variable to hold the launch time in memory
    public static var appLaunchTime: Date?

    public static func onAppLaunched() {
        appLaunchTime = Date()
        print("App has launched - onAppLaunched called in Swift. \(appLaunchTime!)")
    }
}
