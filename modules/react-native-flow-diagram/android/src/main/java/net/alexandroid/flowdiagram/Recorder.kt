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
    private val flushDelayMs: Long = 200
) {
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
        add { Record.Event(it, t, src, mode, level, msg, thread) }
    }

    fun net(phase: String, reqId: Int, url: String, status: Int = 0, durMs: Long = 0) {
        if (state.ordinal > State.ENABLED.ordinal) return
        val t = clockNanos() - t0Nanos
        add { Record.Net(it, t, phase, reqId, url, status, durMs) }
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
    fun enable(header: String, openSink: () -> Sink?) {
        synchronized(lock) {
            if (state != State.PENDING) return
            state = State.ENABLED
            executor.execute {
                sink = try {
                    openSink()
                } catch (e: Exception) {
                    null
                }
                val s = sink
                if (s == null) {
                    state = State.DISABLED
                } else {
                    writeLine(s, header)
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
            try {
                executor.execute { sink?.flush() }
            } catch (_: java.util.concurrent.RejectedExecutionException) {
            }
        }
    }

    private fun endLocked(reason: String) {
        enqueue(Record.End(++seq, clockNanos() - t0Nanos, reason))
        state = State.ENDED
        executor.execute {
            sink?.flush()
            sink?.close()
            sink = null
        }
    }

    private fun enqueue(record: Record) {
        executor.execute {
            val s = sink ?: return@execute
            writeLine(s, JsonLines.encode(record))
        }
    }

    private fun writeLine(s: Sink, line: String) {
        try {
            s.write(line)
        } catch (e: Exception) {
            sink = null
            state = State.DISABLED
            return
        }
        if (!flushScheduled) {
            flushScheduled = true
            executor.schedule({
                flushScheduled = false
                try {
                    sink?.flush()
                } catch (_: Exception) {
                }
            }, flushDelayMs, TimeUnit.MILLISECONDS)
        }
    }
}
