import Foundation
import React
import UIKit

/// FlowDiagram v2 recorder. Call `FlowDiagram.onAppLaunched()` first in
/// `application(_:didFinishLaunchingWithOptions:)`. When the app is launched with `--flowDiagramFlag`
/// (and optionally `--flowDiagramRunId <id>`) one JSON Lines file per launch is written to
/// `Documents/flowdiagram/runs/<runId>.jsonl`, see docs/v2/schema.md. Without the flag every call is a
/// cheap no-op. The ObjC name differs because the TurboModule class is already called FlowDiagram.
@objc(FlowDiagramRecorder)
@objcMembers
public final class FlowDiagram: NSObject {
    public static let launchFlag = "--flowDiagramFlag"
    public static let runIdArgument = "--flowDiagramRunId"
    private static let keepRuns = 20
    private static let maxPlausibleSinceStart: Int64 = 30_000_000_000

    private static var recorder: Recorder?
    private static var launched = false
    private static let launchLock = NSLock()

    public static var isRecording: Bool { recorder?.state == .enabled }

    /// Starts recording when the launch flag is present (or `alwaysOn`). Call once, as early as possible.
    public static func onAppLaunched(alwaysOn: Bool = false) {
        launchLock.lock(); defer { launchLock.unlock() }
        if launched { return }
        launched = true

        let args = ProcessInfo.processInfo.arguments
        guard args.contains(launchFlag) || alwaysOn else { return }

        let nowMono = monotonicNanos()
        let sinceStart = sinceProcessStartNanos()
        let prewarmEnv = ProcessInfo.processInfo.environment["ActivePrewarm"] == "1"
        var t0Name = "process_start"
        var t0 = nowMono - (sinceStart ?? 0)
        var appInit = sinceStart ?? 0
        var prewarmed = prewarmEnv
        if prewarmEnv {
            // Process started long before the user launched the app, so it is no usable t0
            t0Name = "app_init"; t0 = nowMono; appInit = 0
        } else if sinceStart == nil || sinceStart! < 0 {
            t0Name = "app_init"; t0 = nowMono; appInit = 0
        } else if sinceStart! > maxPlausibleSinceStart {
            // Large gap without the env var: treated as a prewarmed process as well
            t0Name = "app_init"; t0 = nowMono; appInit = 0; prewarmed = true
        }

        var runId = ""
        if let i = args.firstIndex(of: runIdArgument), i + 1 < args.count, isSafeRunId(args[i + 1]) {
            runId = args[i + 1]
        } else {
            runId = timestampRunId()
        }

        let header = JsonLines.header(
            runId: runId,
            appId: Bundle.main.bundleIdentifier ?? "",
            appVersion: Bundle.main.object(forInfoDictionaryKey: "CFBundleShortVersionString") as? String ?? "",
            build: isDebugBuild ? "debug" : "release",
            debuggable: isDebugBuild,
            os: UIDevice.current.systemVersion,
            device: deviceModel(),
            t0: t0Name,
            appInitNanos: appInit,
            prewarmed: prewarmed
        )
        recorder = Recorder(clock: monotonicNanos, t0Nanos: t0, header: header) { openRunFile(runId) }

        registerNetworkCapture()
        let nc = NotificationCenter.default
        nc.addObserver(forName: UIApplication.didEnterBackgroundNotification, object: nil, queue: nil) { _ in
            recorder?.flush()
        }
        nc.addObserver(forName: UIApplication.willTerminateNotification, object: nil, queue: nil) { _ in
            recorder?.flush(wait: true)
        }
    }

    public static func logSync(message: String, logType: LogType = .IOS, logLevel: LogLevel = .DEBUG) {
        recorder?.event(src: logType.src, mode: "SYNC", level: logLevel.description, msg: message)
    }

    public static func logAsync(message: String, logType: LogType = .IOS, logLevel: LogLevel = .DEBUG) {
        recorder?.event(src: logType.src, mode: "ASYNC", level: logLevel.description, msg: message)
    }

    /// Writes run_end and stops recording. Optional: the script pulls the file without it.
    public static func end() {
        recorder?.end("flush")
    }

    // For Objective-C use (React Native module)
    public static func logSyncObjC(message: String, logType: Int, logLevel: Double) {
        logSync(message: message, logType: LogType(rawValue: logType) ?? .RN, logLevel: logLevel == 0 ? .DEBUG : .INFO)
    }

    public static func logAsyncObjC(message: String, logType: Int, logLevel: Double) {
        logAsync(message: message, logType: LogType(rawValue: logType) ?? .RN, logLevel: logLevel == 0 ? .DEBUG : .INFO)
    }

    // MARK: Network

    static func netRequest(url: String) -> Int {
        guard let rec = recorder, rec.state == .enabled else { return 0 }
        let id = rec.newRequestId()
        rec.net(phase: "REQ", reqId: id, url: url)
        return id
    }

    static func netResponse(reqId: Int, url: String, status: Int, durMs: Int64) {
        if reqId == 0 { return }
        recorder?.net(phase: "RSP", reqId: reqId, url: url, status: status, durMs: durMs)
    }

    private static func registerNetworkCapture() {
        // Native URLSession.shared / default configurations
        URLProtocol.registerClass(LoggingURLProtocol.self)
        // React Native networking
        RCTSetCustomNSURLSessionConfigurationProvider {
            let config = URLSessionConfiguration.default
            var protocols = config.protocolClasses ?? []
            protocols.insert(LoggingURLProtocol.self, at: 0)
            config.protocolClasses = protocols
            return config
        }
    }

    // MARK: Time

    private static func monotonicNanos() -> Int64 {
        Int64(clock_gettime_nsec_np(CLOCK_UPTIME_RAW))
    }

    /// Nanoseconds since this process was created, from sysctl kp_proc.p_starttime (wall clock).
    private static func sinceProcessStartNanos() -> Int64? {
        var info = kinfo_proc()
        var size = MemoryLayout<kinfo_proc>.stride
        var mib: [Int32] = [CTL_KERN, KERN_PROC, KERN_PROC_PID, getpid()]
        guard sysctl(&mib, UInt32(mib.count), &info, &size, nil, 0) == 0 else { return nil }
        let start = info.kp_proc.p_un.__p_starttime
        var now = timeval()
        gettimeofday(&now, nil)
        let micros = (Int64(now.tv_sec) - Int64(start.tv_sec)) * 1_000_000 + Int64(now.tv_usec) - Int64(start.tv_usec)
        return micros * 1000
    }

    // MARK: Files and metadata

    private static var isDebugBuild: Bool {
        #if DEBUG
        return true
        #else
        return false
        #endif
    }

    private static func openRunFile(_ runId: String) -> Int32 {
        guard let docs = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask).first else { return -1 }
        let dir = docs.appendingPathComponent("flowdiagram/runs", isDirectory: true)
        let fm = FileManager.default
        do { try fm.createDirectory(at: dir, withIntermediateDirectories: true) } catch { return -1 }
        pruneOldRuns(dir)
        return open(dir.appendingPathComponent("\(runId).jsonl").path, O_WRONLY | O_CREAT | O_TRUNC, 0o644)
    }

    private static func pruneOldRuns(_ dir: URL) {
        let keys: [URLResourceKey] = [.contentModificationDateKey]
        guard let files = try? FileManager.default.contentsOfDirectory(at: dir, includingPropertiesForKeys: keys) else { return }
        let runs = files.filter { $0.pathExtension == "jsonl" }.map { url -> (URL, Date) in
            (url, (try? url.resourceValues(forKeys: Set(keys)).contentModificationDate) ?? .distantPast)
        }.sorted { $0.1 > $1.1 }
        for (url, _) in runs.dropFirst(keepRuns - 1) { try? FileManager.default.removeItem(at: url) }
    }

    private static func deviceModel() -> String {
        if let sim = ProcessInfo.processInfo.environment["SIMULATOR_MODEL_IDENTIFIER"] { return sim }
        var info = utsname()
        uname(&info)
        return withUnsafeBytes(of: &info.machine) { raw in
            String(cString: raw.bindMemory(to: CChar.self).baseAddress!)
        }
    }

    // Run id becomes a file name
    private static func isSafeRunId(_ id: String) -> Bool {
        !id.isEmpty && id.count <= 128 && !id.hasPrefix(".")
            && id.unicodeScalars.allSatisfy { ($0.isASCII && ($0.properties.isAlphabetic || ("0"..."9").contains($0))) || "-_.".unicodeScalars.contains($0) }
    }

    private static func timestampRunId() -> String {
        let f = DateFormatter()
        f.locale = Locale(identifier: "en_US_POSIX")
        f.dateFormat = "yyyyMMdd-HHmmss"
        return f.string(from: Date())
    }
}

extension LogType {
    var src: String { self == .RN ? "RN" : "IOS" }
}
