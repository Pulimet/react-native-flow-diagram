package net.alexandroid.flowdiagram

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import java.util.concurrent.Executors
import java.util.concurrent.TimeUnit

class RecorderTest {
    private class ListSink : Sink {
        val lines = ArrayList<String>()
        @Volatile var closed = false
        override fun write(line: String) { synchronized(lines) { lines.add(line) } }
        override fun flush() {}
        override fun close() { closed = true }
    }

    private var now = 0L
    private val executor = Executors.newSingleThreadScheduledExecutor()

    private fun recorder(maxPending: Int = 5000, maxTotal: Int = 200_000) =
        Recorder({ now }, 0L, executor, maxPending, maxTotal)

    private fun drain() {
        executor.submit {}.get(5, TimeUnit.SECONDS)
    }

    @Test
    fun buffersBeforeEnableThenWritesHeaderAndOrderedSeq() {
        val r = recorder()
        val sink = ListSink()
        now = 1_000_000; r.event("AD", "SYNC", "DEBUG", "a")
        now = 2_500_000; r.net("REQ", 1, "https://x")
        assertTrue(sink.lines.isEmpty())
        r.enable("HEADER") { sink }
        now = 3_000_000; r.event("RN", "ASYNC", "INFO", "b")
        drain()
        assertEquals(4, sink.lines.size)
        assertEquals("HEADER", sink.lines[0])
        assertEquals("{\"type\":\"event\",\"seq\":1,\"t_ms\":1.0,\"src\":\"AD\",\"mode\":\"SYNC\",\"level\":\"DEBUG\",\"msg\":\"a\",\"thread\":\"${Thread.currentThread().name}\"}", sink.lines[1])
        assertTrue(sink.lines[2].startsWith("{\"type\":\"net\",\"seq\":2,\"t_ms\":2.5,\"phase\":\"REQ\",\"req_id\":1,\"url\":\"https://x\"}"))
        assertTrue(sink.lines[3].contains("\"seq\":3"))
    }

    @Test
    fun disabledDropsBufferAndIsNoOp() {
        val r = recorder()
        r.event("AD", "SYNC", "DEBUG", "a")
        r.disable()
        r.event("AD", "SYNC", "DEBUG", "b")
        val sink = ListSink()
        r.enable("H") { sink }
        drain()
        assertEquals(Recorder.State.DISABLED, r.state)
        assertTrue(sink.lines.isEmpty())
    }

    @Test
    fun pendingOverflowWritesBufferLimitEnd() {
        val r = recorder(maxPending = 2)
        repeat(5) { r.event("AD", "SYNC", "DEBUG", "m$it") }
        val sink = ListSink()
        r.enable("H") { sink }
        drain()
        assertEquals(4, sink.lines.size)
        assertTrue(sink.lines[3].contains("\"type\":\"run_end\"") && sink.lines[3].contains("buffer_limit"))
        assertEquals(Recorder.State.ENDED, r.state)
        assertTrue(sink.closed)
    }

    @Test
    fun endStopsRecording() {
        val r = recorder()
        val sink = ListSink()
        r.enable("H") { sink }
        r.event("AD", "SYNC", "DEBUG", "a")
        r.end("flush")
        r.event("AD", "SYNC", "DEBUG", "late")
        drain()
        assertEquals(3, sink.lines.size)
        assertTrue(sink.lines[2].contains("\"reason\":\"flush\""))
    }

    @Test
    fun sinkOpenFailureDisables() {
        val r = recorder()
        r.enable("H") { null }
        drain()
        assertEquals(Recorder.State.DISABLED, r.state)
    }

    @Test
    fun escapesAndTimePrecision() {
        val line = JsonLines.encode(Record.Event(7, 1_234_560_000L, "AD", "SYNC", "DEBUG", "q\"\\\n\t\u0001é", "main"))
        assertTrue(line.contains("\"t_ms\":1234.6"))
        assertTrue(line.contains("\"msg\":\"q\\\"\\\\\\n\\t\\u0001é\""))
        assertEquals("0.0", JsonLines.millis(10_000))
        assertEquals("0.1", JsonLines.millis(60_000))
    }

    @Test
    fun responseRecordCarriesStatusAndDuration() {
        val line = JsonLines.encode(Record.Net(9, 5_000_000L, "RSP", 3, "https://x", 200, 292))
        assertEquals("{\"type\":\"net\",\"seq\":9,\"t_ms\":5.0,\"phase\":\"RSP\",\"req_id\":3,\"url\":\"https://x\",\"status\":200,\"dur_ms\":292}", line)
    }

    @Test
    fun longMessageIsCappedWithoutSplittingSurrogatePair() {
        val r = Recorder({ now }, 0L, executor, maxFieldChars = 10)
        val sink = ListSink()
        r.enable("H") { sink }
        r.event("AD", "SYNC", "DEBUG", "a".repeat(9) + "\uD83D\uDE00" + "b".repeat(100))
        r.event("AD", "SYNC", "DEBUG", "short")
        drain()
        assertTrue(sink.lines[1].contains("\"msg\":\"aaaaaaaaa...[+102 chars]\""))
        assertTrue(sink.lines[2].contains("\"msg\":\"short\""))
    }

    @Test
    fun hostileCharactersNeverBreakTheLine() {
        val nasty = "a\u0000b\u001f\u2028\u2029\r\n\u007f\uD800 end"
        val line = JsonLines.encode(Record.Event(1, 0, "AD", "SYNC", "DEBUG", nasty, "t\nx"))
        assertTrue(line.none { it == '\n' || it == '\r' || it == '\u2028' || it == '\u2029' })
        assertTrue(line.contains("\\u0000") && line.contains("\\u2028"))
    }

    @Test
    fun failingFlushAndWriteNeverEscapeTheWriterThread() {
        val uncaught = java.util.concurrent.atomic.AtomicReference<Throwable?>()
        val ex = Executors.newSingleThreadScheduledExecutor { run ->
            Thread(run).apply { setUncaughtExceptionHandler { _, e -> uncaught.set(e) } }
        }
        val failing = object : Sink {
            override fun write(line: String) { throw java.io.IOException("disk full") }
            override fun flush() { throw java.io.IOException("disk full") }
            override fun close() { throw java.io.IOException("disk full") }
        }
        val r = Recorder({ now }, 0L, ex)
        r.enable("H") { failing }
        r.event("AD", "SYNC", "DEBUG", "a")
        r.flush()
        r.end("flush")
        ex.submit {}.get(5, TimeUnit.SECONDS)
        r.event("AD", "SYNC", "DEBUG", "after")
        ex.shutdown()
        assertTrue(ex.awaitTermination(5, TimeUnit.SECONDS))
        assertEquals(null, uncaught.get())
    }

    @Test
    fun throwingSinkOpenerDisablesWithoutCrash() {
        val r = recorder()
        r.enable("H") { throw IllegalStateException("boom") }
        drain()
        assertEquals(Recorder.State.DISABLED, r.state)
    }

    @Test
    fun concurrentThreadsKeepSeqUniqueAndOrdered() {
        val r = recorder()
        val sink = ListSink()
        r.enable("H") { sink }
        val threads = (0 until 8).map { t ->
            Thread { repeat(500) { r.event("AD", "ASYNC", "DEBUG", "t$t-$it") } }
        }
        threads.forEach { it.start() }
        threads.forEach { it.join() }
        drain()
        assertEquals(4001, sink.lines.size)
        val seqs = sink.lines.drop(1).map { Regex("\"seq\":(\\d+)").find(it)!!.groupValues[1].toInt() }
        assertEquals((1..4000).toList(), seqs)
    }

    @Test
    fun totalLimitEndsRun() {
        val r = recorder(maxTotal = 3)
        val sink = ListSink()
        r.enable("H") { sink }
        repeat(10) { r.event("AD", "SYNC", "DEBUG", "m$it") }
        drain()
        assertEquals(5, sink.lines.size)
        assertTrue(sink.lines.last().contains("buffer_limit"))
        assertEquals(Recorder.State.ENDED, r.state)
    }
}
