import Foundation
import React

@objc public enum LogType: Int, CustomStringConvertible {
    case IOS, RN, NE_REQUEST, NE_RESPONSE

    public var description: String {
        switch self {
        case .IOS: return "IOS"
        case .RN: return "RN"
        case .NE_REQUEST: return "NE_REQUEST"
        case .NE_RESPONSE: return "NE_RESPONSE"
        }
    }
}

@objc public enum LogLevel: Int, CustomStringConvertible {
    case DEBUG, INFO

    public var description: String {
        switch self {
        case .DEBUG: return "DEBUG"
        case .INFO: return "INFO"
        }
    }
}

/// Deprecated v1 entry points, forwarding to `FlowDiagram`. Removed in 2.1.
@objcMembers
public class FlowDiagramUtil: NSObject {
    public static var isLogEnabled: Bool { FlowDiagram.isRecording }

    @available(*, deprecated, message: "Use FlowDiagram.onAppLaunched(alwaysOn:)")
    public static func onAppLaunched(_ logsEnabled: Bool = false) {
        FlowDiagram.onAppLaunched(alwaysOn: logsEnabled)
    }

    @available(*, deprecated, message: "Network calls are captured automatically")
    public static func logNetwork(
        _ requestUrl: String,
        logType: LogType,
        responseCode: Int32 = 0,
        elapsedTime: Int64 = 0
    ) {}

    @available(*, deprecated, message: "Use FlowDiagram.logSync")
    public static func logSync(message: String, logType: LogType = .IOS, logLevel: LogLevel = .DEBUG) {
        FlowDiagram.logSync(message: message, logType: logType, logLevel: logLevel)
    }

    @available(*, deprecated, message: "Use FlowDiagram.logAsync")
    public static func logAsync(message: String, logType: LogType = .IOS, logLevel: LogLevel = .DEBUG) {
        FlowDiagram.logAsync(message: message, logType: logType, logLevel: logLevel)
    }

    @available(*, deprecated, message: "Use FlowDiagram.logSyncObjC")
    public static func logSyncObjC(message: String, logType: Int, logLevel: Double) {
        FlowDiagram.logSyncObjC(message: message, logType: logType, logLevel: logLevel)
    }

    @available(*, deprecated, message: "Use FlowDiagram.logAsyncObjC")
    public static func logAsyncObjC(message: String, logType: Int, logLevel: Double) {
        FlowDiagram.logAsyncObjC(message: message, logType: logType, logLevel: logLevel)
    }
}
