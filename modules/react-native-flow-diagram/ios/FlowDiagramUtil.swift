import Foundation

public struct FlowDiagramUtil {
    public static var isLogEnabled: Bool = false
    public static var appLaunchTime: Date?
    public static var recentLogTime: Date?

    public static func onAppLaunched(_ logsEnabled: Bool = false) {
        appLaunchTime = Date()
        recentLogTime = appLaunchTime
        isLogEnabled = logsEnabled
        print("App has launched - onAppLaunched called in Swift. \(launchTime)")
    }
}
