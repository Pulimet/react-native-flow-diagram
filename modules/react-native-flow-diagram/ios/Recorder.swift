import Foundation

enum RecordKind {
    case event(src: String, mode: String, level: String, msg: String, thread: String)
    case net(phase: String, reqId: Int, url: String, status: Int, durMs: Int64)
    case end(reason: String)
}

struct Record {
    let seq: Int
    let tNanos: Int64
    let kind: RecordKind
}

/// Encodes run file records (docs/v2/schema.md) as single JSON lines without a trailing newline.
enum JsonLines {
    static func header(
        runId: String, appId: String, appVersion: String, build: String, debuggable: Bool,
        os: String, device: String, t0: String, appInitNanos: Int64, prewarmed: Bool
    ) -> String {
        var s = "{\"type\":\"run_start\",\"schema\":2"
        field(&s, "run_id", runId)
        field(&s, "platform", "ios")
        field(&s, "app_id", appId)
        field(&s, "app_version", appVersion)
        field(&s, "build", build)
        s += ",\"debuggable\":\(debuggable)"
        field(&s, "os", os)
        field(&s, "device", device)
        field(&s, "t0", t0)
        s += ",\"app_init_ms\":\(millis(appInitNanos)),\"prewarmed\":\(prewarmed)}"
        return s
    }

    static func encode(_ r: Record) -> String {
        var s = ""
        switch r.kind {
        case let .event(src, mode, level, msg, thread):
            s = "{\"type\":\"event\""
            head(&s, r)
            field(&s, "src", src)
            field(&s, "mode", mode)
            field(&s, "level", level)
            field(&s, "msg", msg)
            field(&s, "thread", thread)
        case let .net(phase, reqId, url, status, durMs):
            s = "{\"type\":\"net\""
            head(&s, r)
            field(&s, "phase", phase)
            s += ",\"req_id\":\(reqId)"
            field(&s, "url", url)
            if phase == "RSP" { s += ",\"status\":\(status),\"dur_ms\":\(durMs)" }
        case let .end(reason):
            s = "{\"type\":\"run_end\""
            head(&s, r)
            field(&s, "reason", reason)
        }
        s += "}"
        return s
    }

    /// Nanoseconds to milliseconds with 0.1 ms precision, e.g. 1_234_560_000 -> "1234.6".
    static func millis(_ nanos: Int64) -> String {
        let tenths = nanos >= 0 ? (nanos + 50_000) / 100_000 : 0
        return "\(tenths / 10).\(tenths % 10)"
    }

    private static func head(_ s: inout String, _ r: Record) {
        s += ",\"seq\":\(r.seq),\"t_ms\":\(millis(r.tNanos))"
    }

    private static func field(_ s: inout String, _ name: String, _ value: String) {
        s += ",\"\(name)\":"
        quote(&s, value)
    }

    static func quote(_ out: inout String, _ value: String) {
        out += "\""
        for u in value.unicodeScalars {
            switch u {
            case "\"": out += "\\\""
            case "\\": out += "\\\\"
            case "\n": out += "\\n"
            case "\r": out += "\\r"
            case "\t": out += "\\t"
            default:
                if u.value < 0x20 || u.value == 0x2028 || u.value == 0x2029 {
                    out += String(format: "\\u%04x", u.value)
                } else {
                    out.unicodeScalars.append(u)
                }
            }
        }
        out += "\""
    }
}

/// Thread safe record collector. Each record gets its seq and is queued under one lock, so write
/// order equals seq order. Encoding and file I/O happen on a serial background queue.
final class Recorder {
    enum State { case enabled, ended, disabled }

    private let clock: () -> Int64
    private let t0Nanos: Int64
    private let maxTotal: Int
    private let flushDelay: DispatchTimeInterval
    private let queue = DispatchQueue(label: "net.alexandroid.flowdiagram.writer", qos: .utility)
    private let lock = NSLock()
    private var _state = State.enabled
    private var seq = 0
    private var nextReq = 0

    // Writer queue only
    private var fd: Int32 = -1
    private var buffer = [UInt8]()
    private var flushScheduled = false

    var state: State {
        lock.lock(); defer { lock.unlock() }
        return _state
    }

    init(clock: @escaping () -> Int64, t0Nanos: Int64, maxTotal: Int = 200_000, flushDelayMs: Int = 200,
         header: String, openFile: @escaping () -> Int32) {
        self.clock = clock
        self.t0Nanos = t0Nanos
        self.maxTotal = maxTotal
        self.flushDelay = .milliseconds(flushDelayMs)
        buffer.reserveCapacity(32 * 1024)
        queue.async {
            self.fd = openFile()
            if self.fd < 0 {
                self.setState(.disabled)
            } else {
                self.append(header)
            }
        }
    }

    static let maxFieldChars = 4_096

    /// Caps a field so one huge message cannot blow up memory or the file.
    static func cap(_ s: String, _ max: Int = maxFieldChars) -> String {
        if s.utf8.count <= max { return s }  // O(1) fast path for native strings
        let total = s.count
        if total <= max { return s }
        return String(s.prefix(max)) + "...[+\(total - max) chars]"
    }

    func event(src: String, mode: String, level: String, msg: String) {
        let t = clock() - t0Nanos
        let thread = Recorder.threadName()
        let capped = Recorder.cap(msg)
        add(t) { .event(src: src, mode: mode, level: level, msg: capped, thread: thread) }
    }

    func net(phase: String, reqId: Int, url: String, status: Int = 0, durMs: Int64 = 0) {
        let t = clock() - t0Nanos
        let capped = Recorder.cap(url)
        add(t) { .net(phase: phase, reqId: reqId, url: capped, status: status, durMs: durMs) }
    }

    func newRequestId() -> Int {
        lock.lock(); defer { lock.unlock() }
        nextReq += 1
        return nextReq
    }

    func end(_ reason: String) {
        lock.lock(); defer { lock.unlock() }
        if _state == .enabled { endLocked(reason) }
    }

    func flush(wait: Bool = false) {
        if state == .disabled { return }
        if wait {
            queue.sync { self.flushBuffer() }
        } else {
            queue.async { self.flushBuffer() }
        }
    }

    private func add(_ t: Int64, _ create: () -> RecordKind) {
        lock.lock(); defer { lock.unlock() }
        guard _state == .enabled else { return }
        if seq >= maxTotal {
            endLocked("buffer_limit")
            return
        }
        seq += 1
        enqueue(Record(seq: seq, tNanos: t, kind: create()))
    }

    private func endLocked(_ reason: String) {
        seq += 1
        enqueue(Record(seq: seq, tNanos: clock() - t0Nanos, kind: .end(reason: reason)))
        _state = .ended
        queue.async {
            self.flushBuffer()
            if self.fd >= 0 { close(self.fd); self.fd = -1 }
        }
    }

    private func enqueue(_ r: Record) {
        queue.async { self.append(JsonLines.encode(r)) }
    }

    private func setState(_ s: State) {
        lock.lock(); _state = s; lock.unlock()
    }

    private func append(_ line: String) {
        guard fd >= 0 else { return }
        buffer.append(contentsOf: line.utf8)
        buffer.append(10)
        if buffer.count >= 16 * 1024 {
            flushBuffer()
        } else if !flushScheduled {
            flushScheduled = true
            queue.asyncAfter(deadline: .now() + flushDelay) {
                self.flushScheduled = false
                self.flushBuffer()
            }
        }
    }

    private func flushBuffer() {
        guard fd >= 0, !buffer.isEmpty else { return }
        let ok = buffer.withUnsafeBytes { raw -> Bool in
            var off = 0
            while off < raw.count {
                let n = write(fd, raw.baseAddress! + off, raw.count - off)
                if n < 0 {
                    if errno == EINTR { continue }
                    return false
                }
                off += n
            }
            return true
        }
        buffer.removeAll(keepingCapacity: true)
        if !ok {
            close(fd)
            fd = -1
            setState(.disabled)
        }
    }

    private static func threadName() -> String {
        if Thread.isMainThread { return "main" }
        var name = [CChar](repeating: 0, count: 64)
        if pthread_getname_np(pthread_self(), &name, name.count) == 0, name[0] != 0 {
            return String(cString: name)
        }
        return "thread-\(pthread_mach_thread_np(pthread_self()))"
    }
}
