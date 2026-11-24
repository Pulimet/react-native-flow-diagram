package net.alexandroid.flowdiagram

import java.util.concurrent.Executor
import java.util.concurrent.ScheduledExecutorService
import java.util.concurrent.TimeUnit

internal interface Sink {
    fun write(line: String)
    fun flush()
    fun close()
}

/**
 * Thread safe record collector. Records are buffered in memory until [enable] or [disable] is called
 * (the launch intent decides). When enabled, each record is encoded and written on [executor],
 * which must be single threaded so write order equals seq order.
 */
internal class Recorder(
    private val clockNanos: () -> Long,
    private val t0Nanos: Long,
    private val executor: ScheduledExecutorService,
    private val maxPending: Int = 5_000,
    private val maxTotal: Int = 200_000,
    private val flushDelayMs: Long = 200,
    private val maxFieldChars: Int = MAX_FIELD_CHARS
) {
    companion object {
        const val MAX_FIELD_CHARS = 4_096

        /** Caps a field so one huge message cannot blow up memory or the file. Never splits a surrogate pair. */
        fun cap(s: String, max: Int): String {
            if (s.length <= max) return s
            var end = max
            if (Character.isHighSurrogate(s[end - 1])) end--
            return s.substring(0, end) + "...[+${s.length - end} chars]"
        }
    }

    enum class State { PENDING, ENABLED, DISABLED, ENDED }

    @Volatile
    var state = State.PENDING
        private set

    private val lock = Any()
    private var seq = 0
    private var pending: ArrayList<Record>? = ArrayList()
    private var pendingOverflow = false

    // Writer thread only
    private var sink: Sink? = null
    private var flushScheduled = false

    fun event(src: String, mode: String, level: String, msg: String) {
        if (state.ordinal > State.ENABLED.ordinal) return
        val t = clockNanos() - t0Nanos
        val thread = Thread.currentThread().name
        val capped = cap(msg, maxFieldChars)
        add { Record.Event(it, t, src, mode, level, capped, thread) }
    }

    fun net(phase: String, reqId: Int, url: String, status: Int = 0, durMs: Long = 0) {
        if (state.ordinal > State.ENABLED.ordinal) return
        val t = clockNanos() - t0Nanos
        val capped = cap(url, maxFieldChars)
        add { Record.Net(it, t, phase, reqId, capped, status, durMs) }
    }

    private inline fun add(create: (Int) -> Record) {
        synchronized(lock) {
            when (state) {
                State.PENDING -> {
                    val list = pending ?: return
                    if (list.size >= maxPending) {
                        pendingOverflow = true
                    } else {
                        list.add(create(++seq))
                    }
                }
                State.ENABLED -> {
                    if (seq >= maxTotal) {
                        endLocked("buffer_limit")
                    } else {
                        enqueue(create(++seq))
                    }
                }
                else -> {}
            }
        }
    }

    /** Starts writing: opens the sink on the writer thread, writes [header], then the buffered records. */
    fun enable(header: String, openSink: () -> Sink?) = enable({ header }, openSink)

    /** [header] runs on the writer thread so the app's main thread does not pay for it. */
    fun enable(header: () -> String, openSink: () -> Sink?) {
        synchronized(lock) {
            if (state != State.PENDING) return
            state = State.ENABLED
            submit {
                sink = try {
                    openSink()
                } catch (e: Throwable) {
                    null
                }
                val s = sink
                if (s == null) {
                    state = State.DISABLED
                } else {
                    writeLine(s, header())
                }
            }
            val buffered = pending ?: emptyList<Record>()
            pending = null
            buffered.forEach { enqueue(it) }
            if (pendingOverflow) endLocked("buffer_limit")
        }
    }

    /** Drops the buffer; every later call is a cheap no-op. */
    fun disable() {
        synchronized(lock) {
            if (state != State.PENDING) return
            state = State.DISABLED
            pending = null
        }
    }

    /** Writes run_end and stops recording. */
    fun end(reason: String) {
        synchronized(lock) {
            if (state == State.ENABLED) endLocked(reason)
        }
    }

    fun flush() {
        if (state == State.ENABLED || state == State.ENDED) {
            submit { sink?.flush() }
        }
    }

    private fun endLocked(reason: String) {
        enqueue(Record.End(++seq, clockNanos() - t0Nanos, reason))
        state = State.ENDED
        submit {
            try {
                sink?.flush()
            } catch (_: Throwable) {
            }
            closeSink()
        }
    }

    private fun enqueue(record: Record) {
        submit {
            val s = sink ?: return@submit
            writeLine(s, JsonLines.encode(record))
        }
    }

    /** Runs on the writer thread. Nothing thrown here may reach the thread's uncaught handler, that kills the app. */
    private fun submit(task: () -> Unit) {
        try {
            executor.execute {
                try {
                    task()
                } catch (_: Throwable) {
                    closeSink()
                    state = State.DISABLED
                }
            }
        } catch (_: Throwable) {
            // rejected: executor was shut down
        }
    }

    private fun closeSink() {
        val s = sink ?: return
        sink = null
        try {
            s.close()
        } catch (_: Throwable) {
        }
    }

    private fun writeLine(s: Sink, line: String) {
        try {
            s.write(line)
        } catch (e: Throwable) {
            closeSink()
            state = State.DISABLED
            return
        }
        if (!flushScheduled) {
            flushScheduled = true
            try {
                executor.schedule({
                    flushScheduled = false
                    try {
                        sink?.flush()
                    } catch (_: Throwable) {
                        closeSink()
                        state = State.DISABLED
                    }
                }, flushDelayMs, TimeUnit.MILLISECONDS)
            } catch (_: Throwable) {
            }
        }
    }
}
