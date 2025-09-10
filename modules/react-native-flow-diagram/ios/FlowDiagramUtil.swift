import Foundation
import React
import os.log

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

@objcMembers
public class FlowDiagramUtil: NSObject {
    public static var isLogEnabled: Bool = false
    public static var appLaunchTime: Date?
    public static var appLaunchTimeMs: Int64 {
        guard let appLaunchTime = appLaunchTime else {
            return 0
        }
        return Int64(appLaunchTime.timeIntervalSince1970 * 1000)
    }
    
    private static var messageCounter = [String: Int]() // Message and its counter
    private static let logMsChars = 9
    // private static let osLog = OSLog(subsystem: Bundle.main.bundleIdentifier ?? "com.flowdiagram", category: "FlowDiagram")
    private static let logger = Logger(subsystem: Bundle.main.bundleIdentifier!, category: "FlowDiagram")

    public static func onAppLaunched(_ logsEnabled: Bool = false) {
        appLaunchTime = Date()
        isLogEnabled = logsEnabled
        print("App has launched - onAppLaunched called in Swift")
        
        if(!isLogEnabled) {
            return
        }
        
        // Register our custom URLProtocol (Catch native)
        URLProtocol.registerClass(LoggingURLProtocol.self)
        
        // Catch RN network calls
        RCTSetCustomNSURLSessionConfigurationProvider {
            let config = URLSessionConfiguration.default
            var protocols = config.protocolClasses ?? []
            protocols.insert(LoggingURLProtocol.self, at: 0)
            config.protocolClasses = protocols
            return config
        }
    }
    
    public static func logNetwork(
        _ requestUrl: String,
        logType: LogType,
        responseCode: Int32 = 0,
        elapsedTime: Int64 = 0
    ) {
        if(!isLogEnabled) {
            return
        }
        switch logType {
        case .NE_REQUEST:
            logNeRequest(requestUrl)
            break
        case .NE_RESPONSE:
            logNeResponse(requestUrl, responseCode: responseCode, elapsedTime: elapsedTime)
            break
        case .IOS: break
        case .RN: break
        }
    }

    private static func logNeRequest(_ message: String) {
        let messageWithSuffix = addSuffixToMessage("[NET][REQ] \(message)")
        log(msg: "\(sinceCreated()) => \(messageWithSuffix)")
    }

    private static func logNeResponse(_ message: String, responseCode: Int32, elapsedTime: Int64) {
        let messageWithSuffix = addSuffixToMessage("[NET][RSP] \(message)")
        log(msg: "\(sinceCreated()) => \(messageWithSuffix), Status: \(responseCode), Elapsed time: \(elapsedTime)")
    }
    
    @objc
    public static func logSync(
        message: String,
        logType: LogType = .IOS,
        logLevel: LogLevel = .DEBUG
    ) {
        if isLogEnabled {
            let type = addSpaces(time: logType.description, spacesNum: 3)
            let messageWithSuffix = addSuffixToMessage(message)
            log(msg: "\(sinceCreated()) => [\(type)][\(logLevel.description)][SYNC] \(messageWithSuffix)")
        }
    }
    
    @objc
    public static func logAsync(
        message: String,
        logType: LogType = .IOS,
        logLevel: LogLevel = .DEBUG
    ) {
        if isLogEnabled {
            let type = addSpaces(time: logType.description, spacesNum: 3)
            let messageWithSuffix = addSuffixToMessage(message)
            log(msg: "\(sinceCreated()) => [\(type)][\(logLevel.description)][ASYNC] \(messageWithSuffix)")
        }
    }
    
    private static func log(msg: String) {
        //os_log("%{public}@", log: osLog, type: .error, msg)
        logger.warning("\(msg, privacy: .public)")
    }
    
    private static func currentMillis() -> Int64 {
        return Int64(Date().timeIntervalSince1970 * 1000)
    }
    
    private static func sinceCreated() -> String {
        let elapsed = currentMillis() - appLaunchTimeMs
        let formatted = formatChunksOfThree(elapsed)
        return addSpaces(time: formatted, spacesNum: logMsChars)
    }
    
    private static func formatChunksOfThree(_ input: Int64) -> String {
        let inputStr = String(input)
        if input < 1000 {
            return inputStr
        }

        // Reverse the string for easier chunking from the right
        let reversed = String(inputStr.reversed())
        var chunks: [String] = []

        for i in stride(from: 0, to: reversed.count, by: 3) {
            let start = reversed.index(reversed.startIndex, offsetBy: i)
            let end = reversed.index(start, offsetBy: min(3, reversed.count - i))
            chunks.append(String(reversed[start..<end]))
        }

        // Join with spaces and reverse back to normal
        let spaced = chunks.joined(separator: " ")
        return String(spaced.reversed())
    }
    
    private static func addSpaces(time: String, spacesNum: Int = logMsChars) -> String {
        var text = time
        let spaces = spacesNum - text.count
        if spaces > 0 {
            text.append(String(repeating: " ", count: spaces))
        }
        return text
    }
    
    private static func addSuffixToMessage(_ message: String) -> String {
        let counter = messageCounter[message] ?? 0
        if counter > 0 {
            messageCounter[message] = counter + 1
            return "\(message)(\(counter))"
        } else {
            messageCounter[message] = 1
            return message
        }
    }
    
    // For Objective-C use:
    @objc public static func logSyncObjC(message: String, logType: Int, logLevel: Double) {
        let level = logLevel == 0.0 ? 0 : 1
        logSync(
            message: message,
            logType: LogType(rawValue: logType) ?? .RN,
            logLevel: LogLevel(rawValue: level) ?? .DEBUG
        )
    }

    @objc public static func logAsyncObjC(message: String, logType: Int, logLevel: Double) {
        let level = logLevel == 0.0 ? 0 : 1
        logAsync(
            message: message,
            logType: LogType(rawValue: logType) ?? .RN,
            logLevel: LogLevel(rawValue: level) ?? .DEBUG
        )
    }
}
