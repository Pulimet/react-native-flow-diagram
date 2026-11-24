import Foundation
import UIKit

/// Phase 0 spike: writes <Documents>/flowdiagram/runs/<runId>.jsonl when launched with
/// --flowDiagramFlag --flowDiagramRunId <id>.
@objcMembers
public class RunFileWriter: NSObject {
    public static func start() {
        let args = ProcessInfo.processInfo.arguments
        guard args.contains("--flowDiagramFlag"),
              let i = args.firstIndex(of: "--flowDiagramRunId"), i + 1 < args.count else { return }
        let runId = args[i + 1]
        let startMs = Date().timeIntervalSince1970 * 1000
        func line(_ type: String, _ extra: [String: Any] = [:]) -> String {
            var o: [String: Any] = extra
            o["type"] = type
            o["runId"] = runId
            o["t"] = Int(Date().timeIntervalSince1970 * 1000 - startMs)
            let d = try? JSONSerialization.data(withJSONObject: o, options: [.sortedKeys])
            return String(data: d ?? Data(), encoding: .utf8) ?? "{}"
        }
        #if DEBUG
        let debug = true
        #else
        let debug = false
        #endif
        let lines = [
            line("run_start", ["platform": "ios", "debug": debug]),
            line("event", ["name": "spike.event.1"]),
            line("event", ["name": "spike.event.2"]),
            line("run_end"),
        ]
        guard let docs = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask).first else { return }
        let dir = docs.appendingPathComponent("flowdiagram/runs", isDirectory: true)
        try? FileManager.default.createDirectory(at: dir, withIntermediateDirectories: true)
        let file = dir.appendingPathComponent("\(runId).jsonl")
        try? (lines.joined(separator: "\n") + "\n").write(to: file, atomically: true, encoding: .utf8)
    }
}
