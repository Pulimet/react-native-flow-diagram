# Phase 4: Python platform fetchers and run loop

Status: done. v1 log scraping is removed; the script launches the app with the FlowDiagram flag and a fresh run id, pulls the JSONL run file, normalizes it and feeds the existing CSV, averages and PNG report.

## Layout (`py/src/flow/`)

- `platforms/`: `base.py` (interface, `run_command` subprocess seam), `android.py` (adb), `ios_simulator.py` (simctl), `ios_device.py` (devicectl), `completion.py` (settle, poll, stability), `__init__.py` (`create_platform`, `auto`).
- `run_loop.py`: N iterations, raw files kept in `<output>/<date>/raw/<run_id>.jsonl`, `--from-dir` loading.
- `report/`: moved `calc_average`, `csv_utils`, `visualize` (now accept run metadata).
- `events/keys.py`: constants kept from the old `parsing_utils.py`.
- Deleted: `device/*`, `measurements.py`, `parsing_utils.py`, `py/spike/` (history keeps it).

## CLI

```
python src/flow/main.py --platform android --serial <serial> --launch_times 10
python src/flow/main.py --platform ios_simulator --launch_times 10
python src/flow/main.py --platform ios_device --udid <udid> --launch_times 10 --t0 app_init
python src/flow/main.py --from-dir output/<date>/raw
```

Flags: `--platform {android,ios_device,ios_simulator,auto}`, `--output-dir`, `--launch_times`, `--package`, `--activity`, `--bundle_id`, `--serial`, `--udid`, `--compile-mode {speed-profile,speed,verify,none}`, `--t0 {process_start,app_init}`, `--sink {auto,downloads}`, `--allow-debuggable`, `--wait_time`, `--poll-interval`, `--stable-polls`, `--timeout`, `--from-dir`, `--open_csv`, `--open_png`. Old underscore flags keep hyphen aliases. `--extra` is a hidden no-op with a warning.

## Decisions and deviations

- Completion: wait `--wait_time` (default 10 s), then poll until the last line is `run_end` or the file is unchanged for `--stable-polls` polls; hard timeout 60 s returns a partial file with a warning (error if no file).
- Android: primary path `Android/data/<pkg>/files/flowdiagram/runs/`, fallback `Download/flowdiagram/<pkg>/` (also forced by `--sink downloads`). The console prints once per run which location the file was fetched from, plus a note when `auto` fell back to Download. Compile mode applied then force-stop. Screen timeout is read and restored, not hardcoded.
- iOS device cannot delete remote files or hold the screen awake; app retention (newest 20) bounds growth. Simulator screen-lock hack dropped.
- Debuggable or debug builds are fatal unless `--allow-debuggable`.
- Failed iterations are skipped; exit code 1 only if no run is usable. CSV REPEAT shows usable runs.
- Emulator and simulator reports are flagged "functional, not representative".
- Added: `--platform auto`, `AM_TOTAL_TIME_AVG_MS` (from `am start -W`), report footer metadata (device, OS, build, t0).
- Not added: multi-process file handling (only the main process records).
- Use `-destination 'id=<udid>'` for xcodebuild when several simulators share a name.

## Validation (3 runs each, real CLI; CSV, net CSV, PNG and raw JSONL produced)

| Target | Process start -> App init avg | Other |
|---|---|---|
| Android emulator Pixel_9 (API 35) | 82 ms | AM TotalTime 788 ms; network RSP missing (no emulator internet), expected warnings |
| Samsung SM-S928B | 60 ms | AM TotalTime 655 ms; RSP jsonplaceholder 166 ms, agify 809 ms |
| Samsung, `--sink downloads --t0 app_init --compile-mode none` (2 runs) | n/a | Downloads fallback fetch worked, remote dir cleaned |
| iPhone 16 Pro Max (installed over, not uninstalled) | 38 ms | RSP jsonplaceholder 53 ms, agify 707 ms |
| iOS simulator iPhone 16 Pro (Release) | 217 ms | network RSP missing, warnings expected |

Unit tests: 37 passed (`py/.venv-test/bin/python -m pytest -q` from `py/`), covering command construction per platform with mocked subprocess, fetch and poll logic, run loop on fixture JSONL, and CLI parsing.
