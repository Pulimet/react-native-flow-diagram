package net.alexandroid.flowdiagram

/** Encodes run file records (docs/v2/schema.md) as single JSON lines without a trailing newline. */
internal object JsonLines {

    fun header(
        runId: String,
        appId: String,
        appVersion: String,
        build: String,
        debuggable: Boolean,
        os: String,
        device: String,
        t0: String,
        appInitMs: Double
    ): String {
        val sb = StringBuilder(256)
        sb.append("{\"type\":\"run_start\",\"schema\":2")
        field(sb, "run_id", runId)
        field(sb, "platform", "android")
        field(sb, "app_id", appId)
        field(sb, "app_version", appVersion)
        field(sb, "build", build)
        sb.append(",\"debuggable\":").append(debuggable)
        field(sb, "os", os)
        field(sb, "device", device)
        field(sb, "t0", t0)
        sb.append(",\"app_init_ms\":").append(millis(Math.round(appInitMs * 1_000_000.0)))
        sb.append(",\"prewarmed\":false}")
        return sb.toString()
    }

    fun encode(record: Record): String {
        val sb = StringBuilder(160)
        when (record) {
            is Record.Event -> {
                sb.append("{\"type\":\"event\"")
                head(sb, record.seq, record.tNanos)
                field(sb, "src", record.src)
                field(sb, "mode", record.mode)
                field(sb, "level", record.level)
                field(sb, "msg", record.msg)
                field(sb, "thread", record.thread)
            }
            is Record.Net -> {
                sb.append("{\"type\":\"net\"")
                head(sb, record.seq, record.tNanos)
                field(sb, "phase", record.phase)
                sb.append(",\"req_id\":").append(record.reqId)
                field(sb, "url", record.url)
                if (record.phase == "RSP") {
                    sb.append(",\"status\":").append(record.status)
                    sb.append(",\"dur_ms\":").append(record.durMs)
                }
            }
            is Record.End -> {
                sb.append("{\"type\":\"run_end\"")
                head(sb, record.seq, record.tNanos)
                field(sb, "reason", record.reason)
            }
        }
        sb.append('}')
        return sb.toString()
    }

    /** Nanoseconds to milliseconds with 0.1 ms precision, e.g. 1_234_560_000 -> "1234.6". */
    fun millis(nanos: Long): String {
        val tenths = if (nanos >= 0) (nanos + 50_000) / 100_000 else 0
        return "${tenths / 10}.${tenths % 10}"
    }

    private fun head(sb: StringBuilder, seq: Int, tNanos: Long) {
        sb.append(",\"seq\":").append(seq).append(",\"t_ms\":").append(millis(tNanos))
    }

    private fun field(sb: StringBuilder, name: String, value: String) {
        sb.append(",\"").append(name).append("\":")
        quote(sb, value)
    }

    fun quote(sb: StringBuilder, s: String) {
        sb.append('"')
        for (c in s) {
            when {
                c == '"' -> sb.append("\\\"")
                c == '\\' -> sb.append("\\\\")
                c == '\n' -> sb.append("\\n")
                c == '\r' -> sb.append("\\r")
                c == '\t' -> sb.append("\\t")
                c < ' ' || c == '\u2028' || c == '\u2029' -> sb.append(String.format("\\u%04x", c.code))
                else -> sb.append(c)
            }
        }
        sb.append('"')
    }
}

internal sealed class Record {
    abstract val seq: Int
    abstract val tNanos: Long

    class Event(
        override val seq: Int,
        override val tNanos: Long,
        val src: String,
        val mode: String,
        val level: String,
        val msg: String,
        val thread: String
    ) : Record()

    class Net(
        override val seq: Int,
        override val tNanos: Long,
        val phase: String,
        val reqId: Int,
        val url: String,
        val status: Int,
        val durMs: Long
    ) : Record()

    class End(
        override val seq: Int,
        override val tNanos: Long,
        val reason: String
    ) : Record()
}
