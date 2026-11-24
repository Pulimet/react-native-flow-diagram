# Phase 5: hardening

## Overhead (flag on vs flag off)

Android: `py/tools/measure_overhead.py`, release build with R8, `speed-profile`, `am start -W -S` TotalTime, 10 interleaved pairs (first pair dropped).

| Target | Off mean | On mean | Overhead |
|---|---|---|---|
| Samsung RFCXB13QAVF, before optimization | 618.3 ms | 633.6 ms | +2.47% |
| Samsung RFCXB13QAVF, final | 629.4 ms | 633.3 ms | +0.62% (+3.9 ms) |
| Emulator Pixel_9, final | 639.4 ms (sd 56, one outlier) | 613.4 ms | within noise (median -1.7%) |

Optimization: the JSON header (PackageManager lookup, device info) was built on the main thread in `onIntent`. It is now built on the writer thread (`Recorder.enable(header: () -> String, ...)`). That removed about 11 ms.

iOS: no stable startup timer for flag on vs off on the simulator, so the recorder was micro-benchmarked in isolation (release `swiftc -O`): init 162 us on the main thread, `event()` median 0.6 us, p99 2.6 us. File I/O runs on a background queue. Estimated cost far below 2%.

## R8

`minifyEnabled true` is now on for the sample release build. `consumer-rules.pro` (`-keep class net.alexandroid.flowdiagram.** { *; }`) is enough: the release APK on the emulator and Samsung produced run files that the CLI parsed (3/3 runs usable, `Application.onCreate` events present).

## Robustness matrix

| Case | Behavior | Test |
|---|---|---|
| Kill mid-write (truncated last line, cut UTF-8 char) | Reader drops the partial line, decodes with replacement | `test_hardening.py` |
| File cut inside header | Clear `RunFileError` | `test_hardening.py` |
| Stale file from an earlier run | Rejected by `run_id` check | `test_hardening.py` |
| Unwritable dir, disk full, failing flush/close, sink opener throws | Recorder goes DISABLED, nothing reaches the writer thread's uncaught handler | `RecorderTest` |
| Long messages and URLs | Capped at 4096 chars with a `...[+N chars]` marker, no split surrogate pairs (Android and iOS) | `RecorderTest` |
| Quotes, newlines, control chars | Escaped, one record per line | `RecorderTest`, `test_hardening.py` |
| Concurrent threads | Unique, ordered `seq` | `RecorderTest` |
| Buffer and total limits | `buffer_limit` end, no growth | `RecorderTest` |
| Retention | Newest 20 run files in the primary dir | Phase 2 |
| Locked device (Android) | Swipe lock dismissed; secure lock raises a clear error | `test_hardening.py` |
| Wrong activity, missing tool, command timeout | Clear errors | `test_hardening.py` |
| No file before timeout, partial file after timeout | Explains causes; partial run is returned with a warning | `test_hardening.py` |

Known and kept: a request that fails with no response (offline) stays an unmatched REQ, and the CLI prints a warning. This is the documented v2 behavior on both platforms.

iOS has no test target in the project, so there are no iOS unit tests. The Swift `Recorder` is covered by the microbenchmark above and by the simulator end-to-end run. Adding a test target means changing the sample app's Xcode project, left for later.

## Store safety

- Without the launch flag the recorder drops its buffer and every later call is a cheap no-op. Nothing is written.
- `alwaysOn` defaults to false on both platforms.
- To strip it for store builds: guard the `FlowDiagram.init` call and the interceptor with `BuildConfig.DEBUG`/a build flavor (Android) or `#if !APPSTORE` (iOS), or ship `FlowDiagram` calls as they are, since they are inert without the flag.

## Validation

pytest: 47 passed. Android JVM tests (`testReleaseUnitTest`): 13 passed. End-to-end, 3 runs each: Pixel_9 emulator (R8 build), Samsung (overhead runs), iPhone 16 Pro simulator. The iPhone device was not re-run in this phase.
