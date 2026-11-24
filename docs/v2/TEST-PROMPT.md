# FlowDiagram v2 full feature test prompt

Give this prompt to an AI coding agent (or follow it by hand) to test every v2 feature on all four targets. Replace the placeholders in the "Inputs" section first.

---

## Prompt

You are testing FlowDiagram v2 end to end. Run every test below on the targets listed, save all evidence into the results folder, and write a final report. Do not change source code. If a test fails, record the failure with evidence and continue; only fix the environment (for example, start an emulator), never the product.

### Inputs

| Name | Value |
|---|---|
| `REPO` | absolute path to the FlowDiagram checkout (branch `main`) |
| `RESULTS` | absolute path of a new results folder, outside the repo, for example `~/Projects/FlowDiagram-v2-test-results/<YYYY-MM-DD_HHMM>` |
| `ANDROID_EMU` | adb serial of the Android emulator, for example `emulator-5554` |
| `ANDROID_DEV` | adb serial of the Android device |
| `IOS_SIM` | UDID of a booted iOS simulator |
| `IOS_DEV` | UDID of the iOS device |
| `IOS_TEAM` | Apple development team id for device signing |
| `PROXY` | optional shell prefix for network commands (npm, Gradle, CocoaPods) |

Python: `PY=$REPO/modules/react-native-flow-diagram/py`, run the CLI as `python3 $PY/src/flow/main.py` (or the venv `$PY/.venv-test/bin/python`). Shorthand below: `fd` means that command.

### Rules

- Release builds only. Android: `cd $REPO/android && ./gradlew assembleRelease` (add `--offline` if the network is blocked), APK at `android/app/build/outputs/apk/release/app-release.apk`. iOS simulator: `xcodebuild -workspace ios/FlowDiagram.xcworkspace -scheme FlowDiagram -configuration Release -destination "id=$IOS_SIM" -derivedDataPath /tmp/fd-test-sim -quiet build`. iOS device: same with `-destination "id=$IOS_DEV" -derivedDataPath /tmp/fd-test-dev DEVELOPMENT_TEAM=$IOS_TEAM CODE_SIGN_STYLE=Automatic -allowProvisioningUpdates`. The line "error: the following command failed with exit code 0" is harmless.
- iOS device: NEVER uninstall the app. Uninstalling drops the developer certificate trust. Install over it with `xcrun devicectl device install app`. If launch is denied with "profile has not been explicitly trusted", stop and ask the user to trust the certificate (Settings > General > VPN & Device Management).
- Devices must be unlocked. If a device is locked or missing, mark its tests BLOCKED with the reason.
- Every CLI run uses `--output-dir $RESULTS/<target>/<test-id>` and its console output is saved with `2>&1 | tee $RESULTS/<target>/<test-id>/console.log`.
- Record per test: command, exit code, PASS / FAIL / BLOCKED, and the key evidence (file names, a few numbers, warnings).

### Results folder layout

```
$RESULTS/
  REPORT.md                  final report (summary table + details)
  environment.md             tool versions, devices, OS versions, git commit
  builds/                    build logs, APK and app paths, codesign info
  android_emulator/<test-id>/
  android_device/<test-id>/
  ios_simulator/<test-id>/
  ios_device/<test-id>/
  offline/<test-id>/
  unit_tests/                pytest and Android JVM test output
```

### 0. Environment and builds

1. Write `environment.md`: `git -C $REPO rev-parse HEAD`, `python3 --version`, `adb version`, `xcodebuild -version`, `adb -s <serial> shell getprop ro.build.version.release` and `ro.product.model` for both Android targets, `xcrun devicectl list devices`, `xcrun simctl list devices booted`.
2. Build the Android release APK and both iOS Release apps. Save the logs in `builds/`. Confirm that the APK is not debuggable (`aapt dump badging` or `adb shell dumpsys package com.flowdiagram | grep pkgFlags` after install has no `DEBUGGABLE`). Save `codesign -dvv` for the iOS device app.
3. Install: `adb -s <serial> install -r <apk>` on both Android targets, `xcrun simctl install $IOS_SIM <app>`, `xcrun devicectl device install app --device $IOS_DEV <app>`.

### 1. Unit tests (once)

- `cd $PY && python -m pytest -q` (all pass), saved to `unit_tests/pytest.txt`.
- `cd $REPO/android && ./gradlew :react-native-flow-diagram:testReleaseUnitTest` (use `--offline` if needed), saved to `unit_tests/android-jvm.txt`.

### 2. Tests per target

Platform flags: Android emulator `--platform android --serial $ANDROID_EMU`, Android device `--platform android --serial $ANDROID_DEV`, iOS simulator `--platform ios_simulator --udid $IOS_SIM`, iOS device `--platform ios_device --udid $IOS_DEV`.

| Id | Targets | What | Command (append platform flags and output dir) | Pass criteria |
|---|---|---|---|---|
| T01 | all | Basic multi-run measurement | `fd --launch_times 5` | Exit 0; 5 raw `*.jsonl` files; CSV with averages; net CSV; PNG exists and opens; no reader errors |
| T02 | all | Event content | inspect T01 JSONL and CSV | `run_start` header with `schema:2`, matching `run_id`, `platform`, `t0`, `app_init_ms`; native init events, JS (React Native) SYNC and ASYNC events, increasing `seq`; SYNC durations equal time since previous SYNC event |
| T03 | all | Network capture | inspect T01 | REQ and RSP records paired by `req_id`; RSP has status and duration. On emulator or simulator without internet, "no response" warnings are acceptable: mark PASS with note if REQ records exist |
| T04 | all | t0 app_init mode | `fd --launch_times 3 --t0 app_init` | Exit 0; times start at app init; no "Process start -> App init" row; effective t0 reported as app_init |
| T05 | all | Default t0 process_start | compare T01 output | "Process start -> App init" row present (unless the run was prewarmed on iOS, then a warning) |
| T06 | android x2 | Compile modes | `fd --launch_times 2 --compile-mode speed` and `--compile-mode none` | Both exit 0; console shows the compile mode step (or skip for none) |
| T07 | android x2 | Downloads fallback sink | `fd --launch_times 2 --sink downloads` | Exit 0; console shows the Download path was used |
| T08 | all | No flag means no file | Android: `adb shell am start -W -S -n com.flowdiagram/.MainActivity` then list `Android/data/com.flowdiagram/files/flowdiagram/runs/` before and after. iOS sim: `xcrun simctl launch --terminate-running-process $IOS_SIM org.reactjs.native.example.FlowDiagram` and list the app container `Documents/flowdiagram/runs`. iOS device: `xcrun devicectl device process launch --terminate-existing --device $IOS_DEV org.reactjs.native.example.FlowDiagram` and `xcrun devicectl device info files --device $IOS_DEV --domain-type appDataContainer --domain-identifier org.reactjs.native.example.FlowDiagram` (or compare via copy) | No new run file |
| T09 | all | Manual flag launch and fetch | Android: `am start -W -S ... --ez FlowDiagramFlag true --es FlowDiagramRunId manual01`, then `adb pull` the file. iOS sim: `simctl launch ... --flowDiagramFlag --flowDiagramRunId manual01`. iOS device: `devicectl device process launch --terminate-existing ... -- --flowDiagramFlag --flowDiagramRunId manual01` then `devicectl device copy from --domain-type appDataContainer --source Documents/flowdiagram/runs/manual01.jsonl` | File exists with `run_id` `manual01`; save it |
| T10 | all | Unsafe run id is sanitized | as T09 with run id `../evil id` | No file outside `runs/`; a run file with a safe generated id exists |
| T11 | all | Completion detection options | `fd --launch_times 2 --wait_time 3 --poll-interval 0.5 --stable-polls 3 --timeout 30` | Exit 0; both runs usable |
| T12 | all | Timeout handling | `fd --launch_times 1 --wait_time 1 --timeout 2` | Clear timeout or partial-run message, no traceback; exit code documented |
| T13 | all | Auto platform | `fd --platform auto --launch_times 1` with only this target ready if practical; otherwise run with several targets ready and record the error | Either picks the target, or prints a clear "several targets" error |
| T14 | android x2 | Debuggable guard | install a debug APK only if one can be built quickly (`./gradlew assembleDebug`); run `fd --launch_times 1` then with `--allow-debuggable`; reinstall release afterwards | Without the flag: clear refusal. With it: runs with a "not representative" warning. If no debug build is possible, mark BLOCKED |
| T15 | all | Wrong app id | Android `--package com.does.not.exist`; iOS `--bundle_id com.does.not.exist` | Clear "not installed" style error, no traceback, non-zero exit |
| T16 | android_device, ios_device | Locked device (optional, ask the user to lock) | `fd --launch_times 1` while locked | Clear lock error; mark BLOCKED if the user is unavailable |
| T17 | android x2 | Recorder overhead | `python3 $PY/tools/measure_overhead.py --serial <serial> --runs 10` | Overhead under 2% on the device; emulator result recorded (may be noisy) |
| T18 | all | Retention | launch with flag 22 times via the CLI (`fd --launch_times 22`) or manually, then list `runs/` on the target | iOS keeps the newest 20 files; Android behavior recorded as observed |

### 3. Offline and cross-target tests

| Id | What | Command | Pass criteria |
|---|---|---|---|
| O01 | Rebuild reports from saved files | for each target: `fd --from-dir $RESULTS/<target>/T01 --output-dir $RESULTS/offline/O01-<target>` | Exit 0; CSV averages equal T01 averages |
| O02 | Truncated last line | copy a T01 JSONL, cut the last line in half, run `fd --from-dir` on it | Exit 0 with a truncation warning |
| O03 | Corrupt middle line | insert `{not json` in the middle of a copy | Clear error with file name and line number, no traceback |
| O04 | Wrong schema | change `"schema":2` to `"schema":99` in a copy | Clear schema error |
| O05 | Empty folder | `fd --from-dir <empty dir>` | Clear "no run files" message, non-zero exit |

### 4. Report

Write `$RESULTS/REPORT.md`:

1. Summary table: rows are test ids, columns are the 4 targets plus offline, cells are PASS / FAIL / BLOCKED / N/A.
2. Key numbers per target from T01: average "Process start -> App init", first JS event, total flow time, AM TotalTime (Android), network response times.
3. Overhead results from T17.
4. Every FAIL and BLOCKED with the command, the exit code, an excerpt of the console output, and a suggested cause.
5. Observations and suggested follow-ups.

Validate that the markdown tables render. Delete temporary files outside `$RESULTS` (for example `/tmp/fd-test-*`). Do not commit anything to the repo.
