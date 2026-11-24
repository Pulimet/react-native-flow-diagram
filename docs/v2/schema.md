# FlowDiagram v2 run file schema (version 2)

One JSON Lines file per app launch: `<run_id>.jsonl`, UTF-8, one JSON object per line, `\n` terminated.
Reader: `py/src/flow/events/reader.py`. Normalizer: `py/src/flow/events/normalize.py`.

## Records

Line 1 must be `run_start`. After that, `event`, `net` and `run_end` records follow in write order.

### `run_start` (required, first line)
| Field | Type | Notes |
|---|---|---|
| `type` | string | `"run_start"` |
| `schema` | int | must be `2`, otherwise the reader rejects the file |
| `run_id` | string | required, matches the id the script passed at launch |
| `platform` | string | required, `android` or `ios` |
| `app_id` | string | package or bundle id |
| `app_version`, `build`, `os`, `device` | string | informational; `build` is `release` or `debug` |
| `debuggable` | bool | script warns when true |
| `t0` | string | `process_start` (default) or `app_init`. Defines what `t_ms` is relative to |
| `app_init_ms` | number | offset of `Application.onCreate` / `didFinishLaunching` from process start. `0` when `t0` is `app_init` |
| `prewarmed` | bool | iOS only, true when `ActivePrewarm == "1"` |

### `event`
| Field | Type | Notes |
|---|---|---|
| `seq` | int | increasing across all record kinds, starts at 1 |
| `t_ms` | number | ms since the header `t0`, 0.1 ms precision, monotonic clock |
| `src` | string | `AD`, `IOS`, `RN` |
| `mode` | string | `SYNC` or `ASYNC` |
| `level` | string | optional, default `DEBUG` |
| `msg` | string | raw message, no `(n)` suffix |
| `thread` | string | optional |

### `net`
| Field | Type | Notes |
|---|---|---|
| `seq`, `t_ms` | | as above |
| `phase` | string | `REQ` or `RSP` |
| `req_id` | int | pairs a request with its response |
| `url` | string | |
| `status` | int | RSP only |
| `dur_ms` | number | RSP only, measured by the interceptor. Used only if the request is missing |

### `run_end` (optional)
`seq`, `t_ms`, `reason` (`flush`, `background`, `buffer_limit`). Missing when the app was killed first; the reader warns.

## Reader rules
- Empty file, first line not `run_start`, `schema != 2`, missing `run_id` or `platform`, unknown `t0`: error.
- `run_id` differing from the expected one: error.
- Invalid JSON or an invalid record on the **last** line: ignored, run marked `truncated` (app killed mid-write). Anywhere else: error with file and line number.
- Unknown `type`: ignored with a warning (forward compatibility). Non-increasing `seq`: warning.

## Gaps decided beyond PLAN.md 4.2
- `t_ms` is relative to the header `t0`. The prewarm fallback therefore writes `t0:"app_init"`, `app_init_ms:0`.
- Duplicate `(n)` suffix follows the v1 iOS rule: first occurrence unchanged, then `msg(1)`, `msg(2)`. Counters are keyed per source and message for events, and per phase and URL (or `[status] url` for responses) for network.
- Normalized network entries match v1: REQ is `msg = url`, duration 0; RSP is `msg = "[status] url"`, duration = response `t_ms` minus paired request `t_ms`. An unmatched request stays as a marker and a warning is emitted.
- t0 handling in `normalize(run, t0=...)`:
  - `process_start` (default): times as stored, plus a synthetic first row `Process start -> App init` (time and duration = `app_init_ms`) when `app_init_ms > 0`. The first SYNC event duration is still measured from t0, not from the synthetic row.
  - `app_init`: all times shifted by `-app_init_ms` (v1 comparable), no synthetic row, events before app init are dropped.
  - Runs recorded with `t0:"app_init"` (prewarm) always normalize as `app_init`, with a warning if `process_start` was requested. `NormalizedRun.effective_t0` reports what was used.
- Times and durations are rounded to int ms (v1 used ints).

## Sample
See `py/tests/fixtures/happy.jsonl`:
```json
{"type":"run_start","schema":2,"run_id":"20261124-083600-it01","platform":"android","app_id":"com.flowdiagram","app_version":"1.0","build":"release","debuggable":false,"os":"14","device":"Pixel 8","t0":"process_start","app_init_ms":180.0,"prewarmed":false}
{"type":"event","seq":1,"t_ms":200.0,"src":"AD","mode":"SYNC","level":"DEBUG","msg":"MainApplication.onCreate -> Start","thread":"main"}
{"type":"event","seq":2,"t_ms":250.4,"src":"AD","mode":"ASYNC","level":"DEBUG","msg":"Worker -> Queued","thread":"pool-1"}
{"type":"event","seq":3,"t_ms":300.0,"src":"AD","mode":"SYNC","level":"DEBUG","msg":"MainActivity.onCreate -> Start","thread":"main"}
{"type":"net","seq":4,"t_ms":410.2,"phase":"REQ","req_id":3,"url":"https://example.com/api"}
{"type":"net","seq":5,"t_ms":702.9,"phase":"RSP","req_id":3,"url":"https://example.com/api","status":200,"dur_ms":292}
{"type":"event","seq":6,"t_ms":800.0,"src":"RN","mode":"SYNC","level":"DEBUG","msg":"App.tsx -> Render","thread":"js"}
{"type":"run_end","seq":7,"t_ms":10012.0,"reason":"flush"}
```
