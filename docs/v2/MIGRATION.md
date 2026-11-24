# Migration guide: 1.x to 2.0.0

2.0.0 replaces log scraping (Logcat, iOS system log) with an in-app recorder that writes one JSON Lines (JSONL) run file
per launch. The CLI pulls that file. Only release builds are measured.

## What changed

| Area | 1.x | 2.0.0 |
|---|---|---|
| Collection | `adb logcat`, `simctl log stream`, `idevicesyslog` | Run file in app storage, pulled with `adb`, `simctl`, `devicectl` |
| Log mode | Text lines in Logcat or os_log | **Removed.** No log output at all. |
| t0 | `Application.onCreate` / `didFinishLaunching` | Process start (use `--t0 app_init` for 1.x like numbers) |
| Dependencies | libimobiledevice for iOS devices | None extra (Xcode `devicectl`) |
| Builds | any | Release builds. Debug builds are rejected unless `--allow-debuggable`. |
| Durations | computed in the app | computed by the CLI (same SYNC rule) |

## Android
| 1.x | 2.0.0 |
|---|---|
| `LogTime.onApplicationOnCreate(true)` before `super.onCreate()` | `FlowDiagram.init(this)` as the first line of `Application.onCreate`. Pass `alwaysOn = true` only for local development. |
| `LogTime.onIntent(intent)` in `onCreate` (optional) | `FlowDiagram.onIntent(intent)` in `onCreate` **and** `onNewIntent`. Now required, since it reads the flag. |
| `LogTime.loggingInterceptor` | `FlowDiagram.interceptor` |
| `LogTime.logSync/logAsync` | `FlowDiagram.logSync/logAsync` (same parameters) |

The intent extra `FlowDiagramFlag` is unchanged and the CLI also passes `FlowDiagramRunId`. Events from
`Application.onCreate` are no longer lost in flag mode, because the recorder buffers until `onIntent` runs.
R8: no action, the library ships `consumer-rules.pro`.

## iOS
| 1.x | 2.0.0 |
|---|---|
| `FlowDiagramUtil.onAppLaunched(true)` | `FlowDiagram.onAppLaunched()` (`alwaysOn: Bool = false`) |
| `FlowDiagramUtil.logSync/logAsync` | `FlowDiagram.logSync/logAsync` |

The launch argument `--flowDiagramFlag` is unchanged, plus `--flowDiagramRunId <id>`. Network capture is automatic.
`FlowDiagramUtil.logNetwork` is a no-op.

## React Native
`logSync` and `logAsync` are unchanged.

## Deprecated aliases (removed in 2.1)
`LogTime` (Android) and `FlowDiagramUtil` (iOS) still compile and forward to the new recorder, with deprecation
warnings. Their log output is gone. The no-argument `LogTime.onApplicationOnCreate()` finds the `Application` by
reflection; prefer `FlowDiagram.init(context)`. Replace them before 2.1.

## Python CLI
| 1.x | 2.0.0 |
|---|---|
| `--extra True` (pass the flag) | Removed. The flag is always passed. `--extra` is accepted, ignored, and prints a warning. |
| Forced `compile -m speed` | `--compile-mode {speed-profile,speed,verify,none}`, default `speed-profile` |
| (none) | `--t0 {process_start,app_init}`, default `process_start` |
| (none) | `--serial`, `--udid` (multiple devices) |
| (none) | `--sink {auto,downloads}` (Android Download fallback) |
| (none) | `--allow-debuggable` |
| (none) | `--from-dir <dir>` rebuild reports from saved raw files |
| (none) | `--poll-interval`, `--stable-polls`, `--timeout` (run completion) |
| `--platform` | adds `auto` |
| `--wait_time`, `--launch_times`, `--bundle_id`, `--output_dir`, `--open_csv`, `--open_png` | kept, hyphen aliases added |

Defaults of `--package`, `--activity`, `--bundle_id` and `--wait_time` (10) are unchanged. Raw run files are now
saved under `output/<date>/raw/`. Reports gain a "Process start to App init" row and a footer with device, OS, build and
t0. Emulator and simulator reports are labeled "functional, not representative".

## Steps
1. Update the package: `npm i react-native-flow-diagram@2.0.0`, then `cd ios && pod install`.
2. Replace the native API calls as in the tables above. Add `onIntent` to `onNewIntent`.
3. Build a **release** variant (iOS: Release configuration with Development signing) and install it.
4. Remove libimobiledevice from your setup if you installed it only for this tool.
5. Run `npm run flow:<target> -- --launch_times 10`. Add `--t0 app_init` to compare with 1.x numbers.
