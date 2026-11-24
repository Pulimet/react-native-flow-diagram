# Phase 2: Android recorder

Status: done. Validated on the Pixel_9 emulator (API 35) and a Samsung SM-S928B, release APK (R8 off in the sample, library ships `consumer-rules.pro`).

## API (2.0.0)
- `FlowDiagram.init(context, alwaysOn = false)`: first line of `Application.onCreate`. Starts buffering (max 5,000 records).
- `FlowDiagram.onIntent(intent)`: from `onCreate` and `onNewIntent`. Reads `FlowDiagramFlag` (boolean) and `FlowDiagramRunId` (string, `[A-Za-z0-9._-]`, max 128, otherwise replaced by a timestamp id). No flag: buffer dropped, recorder is a no-op for the process. `alwaysOn` records without the flag (run id from the intent or a timestamp); `onIntent` is still required.
- `FlowDiagram.logSync / logAsync(message, logType, logLevel)`, `FlowDiagram.interceptor`, `FlowDiagram.end()`.
- `LogTime` kept as `@Deprecated` aliases (`onApplicationOnCreate()` without context finds the Application via `ActivityThread.currentApplication()` by reflection). Logcat output is removed.

## Files
`FlowDiagram.kt` (API, t0, header), `Recorder.kt` (state machine, buffer, writer scheduling), `JsonLines.kt` (encoding), `Sinks.kt` (file and MediaStore sinks), `FlowDiagramInterceptor.kt`. The spike `RunFileWriter.kt` and `LoggingInterceptor.kt` are removed. Tests: `android/src/test/.../RecorderTest.kt` (`./gradlew :react-native-flow-diagram:testReleaseUnitTest`).

## Decisions and deviations
- t0 is process start: `Process.getStartRequestedElapsedRealtime()` (API 33+) or `getStartElapsedRealtime()`, on the `SystemClock.elapsedRealtimeNanos` timeline. If the result is implausible (negative or over 60 s), falls back to `t0:"app_init"`.
- Sink: primary `getExternalFilesDir("flowdiagram")/runs/<runId>.jsonl`; if that is unavailable the writer falls back to `MediaStore.Downloads` (`Download/flowdiagram/<pkg>/`, API 29+). Extra `FlowDiagramSink=downloads` forces the fallback (used by Phase 0 and by the fetcher tests). Newest 20 run files are kept in the primary dir.
- Writer: one daemon thread, buffered, flush after 200 ms of activity, on `onTrimMemory`, low memory and every `onActivityStopped`. Hot path only captures time, thread name and a small object; encoding is on the writer thread.
- `run_end`: written only by `FlowDiagram.end()` (`flush`) or when the buffer or the 200,000 record cap is exceeded (`buffer_limit`); recording then stops. The `background` reason is not written automatically, because activity recreation can look like background and the script pulls the file anyway.
- Only the main process records (other processes of the app are no-ops), instead of per-process files from the plan risk table.
- Not done: the optional `BuildConfig` store gate (`FLOW_DIAGRAM_ALLOWED`); the intent extra is the only gate.
- Network: same URL filter as v1 (symbolicate, localhost, 10.0, 192.168). A failed call writes a REQ without RSP (normalizer warns).

## Evidence
`am start -W -S -n com.flowdiagram/.MainActivity --ez FlowDiagramFlag true --es FlowDiagramRunId <id>`, then `adb pull`. Reader parsed all files with zero errors (only the expected "run_end is missing" warning); no flag: no file created; Downloads fallback pulled and parsed. Device sample:
```
{"type":"run_start","schema":2,"run_id":"p2-dev-01","platform":"android","app_id":"com.flowdiagram","app_version":"1.0","build":"release","debuggable":false,"os":"17","device":"SM-S928B","t0":"process_start","app_init_ms":102.2,"p
{"type":"event","seq":1,"t_ms":102.5,"src":"AD","mode":"SYNC","level":"DEBUG","msg":"MainApplication.onCreate -> Start - (Sync Native Example)","thread":"main"}
{"type":"event","seq":2,"t_ms":106.7,"src":"AD","mode":"SYNC","level":"DEBUG","msg":"MainApplication.setupOkHttpClient -> Done - (Sync Native Example)","thread":"main"}
{"type":"event","seq":3,"t_ms":123.2,"src":"AD","mode":"SYNC","level":"DEBUG","msg":"MainApplication.onCreate -> End - Sync NativeExample - (Sync Native Example)","thread":"main"}
{"type":"net","seq":13,"t_ms":397.3,"phase":"RSP","req_id":2,"url":"https://jsonplaceholder.typicode.com/todos/1","status":200,"dur_ms":200}
```
