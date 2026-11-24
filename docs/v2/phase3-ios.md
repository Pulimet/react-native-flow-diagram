# Phase 3: iOS recorder

Status: done. Validated with Release builds on the iPhone 16 Pro simulator (iOS 18.3) and a physical iPhone 16 Pro Max (iOS 26.6, Development signing). Files parse with the Phase 1 reader and normalizer with no errors (only the expected "run_end is missing" warning). Pytest: 12 passed.

## API (2.0.0)
- `FlowDiagram.onAppLaunched(alwaysOn: Bool = false)`: first line of `application(_:didFinishLaunchingWithOptions:)`. Reads `--flowDiagramFlag` and `--flowDiagramRunId <id>` from `ProcessInfo.arguments`. Run id rules match Android (`[A-Za-z0-9._-]`, max 128, no leading dot, otherwise a timestamp id). No flag and not `alwaysOn`: nothing is allocated and every later call is a no-op.
- `FlowDiagram.logSync / logAsync(message:logType:logLevel:)`, `FlowDiagram.end()`, `FlowDiagram.isRecording`.
- Network capture is automatic: `LoggingURLProtocol` is registered for native `URLSession` and via `RCTSetCustomNSURLSessionConfigurationProvider` for React Native. REQ and RSP share a `req_id`.
- `FlowDiagramUtil` is kept as `@available(*, deprecated)` aliases (`onAppLaunched(_:)`, `logSync`, `logAsync`, `*ObjC`); `logNetwork` is a deprecated no-op. The os_log output is removed. The spike `RunFileWriter.swift` is removed.
- ObjC name of the Swift class is `FlowDiagramRecorder` (`@objc(FlowDiagramRecorder)`), because the TurboModule class in `FlowDiagram.mm` is already called `FlowDiagram`. `FlowDiagram.mm` calls it.

## Files
`ios/FlowDiagram.swift` (API, t0, prewarm guard, header, file open, retention), `ios/Recorder.swift` (JSON encoding, state, serial writer queue), `LoggingURLProtocol.swift`, `FlowDiagramUtil.swift` (enums and deprecated aliases), `FlowDiagram.mm`. The podspec glob already covers the new files.

## Decisions and deviations
- t0 is process start from `sysctl` `kp_proc.p_starttime` (wall clock), converted onto the `CLOCK_UPTIME_RAW` timeline at init. Header `t0:"process_start"`, `app_init_ms` is the offset.
- Prewarm guard: env `ActivePrewarm == "1"`, or a gap above 30 s between process start and app init (deviation: extra heuristic), gives `prewarmed:true`, `t0:"app_init"`, `app_init_ms:0`. A negative or unreadable gap falls back to `app_init` without the prewarmed flag.
- Because the launch arguments are known synchronously, there is no pre-flag buffer (unlike Android). Each record gets `seq` and is queued under one lock, so file order equals seq order. Encoding and I/O run on a serial utility queue; buffer flushes at 16 KB, after 200 ms, on `didEnterBackground`, and synchronously on `willTerminate`.
- Cap of 200,000 records, then `run_end` with reason `buffer_limit`. `run_end` `flush` only from `end()`; no automatic `background` (parity with Android).
- File: `Documents/flowdiagram/runs/<runId>.jsonl`, newest 20 kept.
- Event `thread` is `main` or the pthread name, else `thread-<mach id>` (React Native threads are unnamed).
- Network filter now matches Android (`symbolicate`, `autoproxy`, `localhost`, `10.0.`, `192.168.`). A failed call writes a REQ without RSP. The per-request `URLSession` is invalidated after completion.
- No iOS unit test target exists in the repo, so validation is on device and simulator. `Podfile.lock` unchanged.
- The simulator on this Mac has no direct internet (proxy), so RSP records were verified on the device only.

## Evidence
Simulator: `xcrun simctl launch --terminate-running-process booted org.reactjs.native.example.FlowDiagram --flowDiagramFlag --flowDiagramRunId p3-sim-01`; launching without the flag creates no `Documents/flowdiagram`. Device: `devicectl device process launch --terminate-existing ... -- --flowDiagramFlag --flowDiagramRunId p3-dev-01`, then `devicectl device copy from`. Device sample:
```
{"type":"run_start","schema":2,"run_id":"p3-dev-01","platform":"ios","app_id":"org.reactjs.native.example.FlowDiagram","app_version":"1.0","build":"release","debuggable":false,"os":"26.6.1","device":"iPhone17,2","t0":"process_start","app_init_ms":72.4,"prewarmed":false}
{"type":"event","seq":1,"t_ms":72.7,"src":"IOS","mode":"SYNC","level":"DEBUG","msg":"AppDelegate.didFinishLaunchingWithOptions -> Start (Sync Native Example)","thread":"main"}
{"type":"net","seq":11,"t_ms":638.2,"phase":"REQ","req_id":2,"url":"https://jsonplaceholder.typicode.com/todos/1"}
{"type":"net","seq":12,"t_ms":785.6,"phase":"RSP","req_id":2,"url":"https://jsonplaceholder.typicode.com/todos/1","status":200,"dur_ms":147}
```
