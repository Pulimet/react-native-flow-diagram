# Changelog

## Unreleased

### Added
- CLI `--strip-query PATTERN` drops the query string of matching network URLs, so requests that differ only by query
  params are averaged as one request.

## 2.0.0

Breaking release. See the [migration guide](docs/v2/MIGRATION.md).

### Added
- In-app recorder on Android and iOS writing one JSON Lines run file per launch (schema 2).
- t0 at process start, with the process start to app init gap shown in reports (`--t0 app_init` for 1.x numbers).
- Android: `FlowDiagram.init(context, alwaysOn)`, `FlowDiagram.onIntent`, `FlowDiagram.interceptor`,
  `FlowDiagram.end()`, early event buffering from `Application.onCreate`, Download fallback sink, R8 consumer rules.
- iOS: `FlowDiagram.onAppLaunched(alwaysOn:)`, automatic network capture, iOS prewarm guard.
- CLI: `--compile-mode`, `--t0`, `--serial`, `--udid`, `--sink`, `--allow-debuggable`, `--from-dir`, `--platform auto`,
  `--poll-interval`, `--stable-polls`, `--timeout`; raw run files saved; report metadata footer; pytest suite.
- Request and response pairing by `req_id`.

### Changed
- Only release builds are measured (debuggable builds are rejected unless `--allow-debuggable`).
- Android launch uses `am start -W -S`; iOS device launch uses `devicectl` without a debugger.
- `LogTime` (Android) and `FlowDiagramUtil` (iOS) are deprecated aliases, removed in 2.1.

### Removed
- Log mode: Logcat and os_log output, `adb logcat`, `simctl log stream`, `idevicesyslog` and libimobiledevice.
- CLI flag `--extra` (accepted and ignored with a warning).

## 1.0.4
Last 1.x release (log scraping based).
