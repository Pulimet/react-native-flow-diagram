from events.keys import (
    TIME_PARAM, DURATION_PARAM, TYPE_PARAM, MSG_PARAM, REQ_RSP_PARAM, LEVEL_PARAM, SYNC_ASYNC_PARAM,
    TYPE_NET, TYPE_AD, TYPE_IOS, TYPE_RN, SYNC, REQ, RSP,
)

from .model import Event, NetEvent, NormalizedRun, Run

T0_PROCESS_START = "process_start"
T0_APP_INIT = "app_init"
SRC_TO_TYPE = {"AD": TYPE_AD, "IOS": TYPE_IOS, "RN": TYPE_RN}
PROCESS_START_LABEL = "Process start -> App init"


def normalize(run: Run, t0: str = T0_PROCESS_START, strip_query=()) -> NormalizedRun:
    """Convert a Run into v1-shaped dict entries (ints in ms since t0).

    t_ms in the file is relative to the header t0. With t0="app_init" every time is shifted back by
    header.app_init_ms (events before app init are dropped), which gives v1 comparable numbers.
    URLs whose part before "?" contains any strip_query pattern lose their query string and fragment,
    so requests that differ only by query params (cache busters, beacons) are averaged together.
    """
    if t0 not in (T0_PROCESS_START, T0_APP_INIT):
        raise ValueError(f"unknown t0 {t0!r}")
    header = run.header
    warnings = list(run.warnings)

    # Header t0 == app_init (prewarm fallback) means t_ms is already relative to app init.
    if header.t0 == T0_APP_INIT:
        shift = 0.0
        if t0 == T0_PROCESS_START:
            warnings.append("run was recorded with t0=app_init (iOS prewarm guard); process start is unavailable")
        effective = T0_APP_INIT
    elif t0 == T0_APP_INIT:
        shift = header.app_init_ms
        effective = T0_APP_INIT
    else:
        shift = 0.0
        effective = T0_PROCESS_START

    entries = []
    if effective == T0_PROCESS_START and header.app_init_ms > 0:
        entries.append({
            TIME_PARAM: _ms(header.app_init_ms),
            DURATION_PARAM: _ms(header.app_init_ms),
            TYPE_PARAM: TYPE_IOS if header.platform.lower().startswith("ios") else TYPE_AD,
            MSG_PARAM: PROCESS_START_LABEL,
            LEVEL_PARAM: "DEBUG",
            SYNC_ASYNC_PARAM: SYNC,
        })

    counters = {}
    prev_sync_ms = 0
    open_reqs = {}  # req_id -> (entry, time)
    for ev in run.events:
        t = _ms(ev.t_ms - shift)
        if t < 0:
            continue
        if isinstance(ev, Event):
            entry = {
                TIME_PARAM: t,
                DURATION_PARAM: 0,
                TYPE_PARAM: SRC_TO_TYPE.get(ev.src, ev.src),
                MSG_PARAM: _suffix(counters, ("EVENT", ev.src, ev.msg), ev.msg),
                LEVEL_PARAM: ev.level,
                SYNC_ASYNC_PARAM: ev.mode,
            }
            if ev.mode == SYNC:
                entry[DURATION_PARAM] = t - prev_sync_ms
                prev_sync_ms = t
            entries.append(entry)
        elif isinstance(ev, NetEvent):
            url = strip_query_params(ev.url, strip_query)
            if ev.phase == REQ:
                entry = {
                    TIME_PARAM: t, DURATION_PARAM: 0, TYPE_PARAM: TYPE_NET, REQ_RSP_PARAM: REQ,
                    MSG_PARAM: _suffix(counters, (REQ, url), url),
                }
                open_reqs[ev.req_id] = t
                entries.append(entry)
            else:
                req_t = open_reqs.pop(ev.req_id, None)
                if req_t is not None:
                    duration = max(t - req_t, 0)
                else:
                    warnings.append(f"response for req_id {ev.req_id} has no request, using dur_ms")
                    duration = _ms(ev.dur_ms or 0)
                message = f"[{ev.status}] {url}" if ev.status is not None else url
                entries.append({
                    TIME_PARAM: t, DURATION_PARAM: duration, TYPE_PARAM: TYPE_NET, REQ_RSP_PARAM: RSP,
                    MSG_PARAM: _suffix(counters, (RSP, message), message),
                })

    for req_id in open_reqs:
        warnings.append(f"request req_id {req_id} has no response")
    return NormalizedRun(entries=entries, effective_t0=effective, warnings=warnings)


def strip_query_params(url, patterns=()):
    base = url.split("#", 1)[0].split("?", 1)[0]
    if base != url and any(p in base for p in patterns):
        return base
    return url


def _suffix(counters, key, msg):
    # v1 rule: first occurrence unchanged, then "msg(1)", "msg(2)", ...
    n = counters.get(key, 0)
    counters[key] = n + 1
    return msg if n == 0 else f"{msg}({n})"


def _ms(value):
    return int(round(value))
