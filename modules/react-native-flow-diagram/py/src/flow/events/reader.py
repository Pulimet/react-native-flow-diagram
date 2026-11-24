import json
from pathlib import Path
from typing import Optional

from .model import SCHEMA_VERSION, Event, NetEvent, Run, RunEnd, RunHeader


class RunFileError(Exception):
    pass


def read_run(path, expected_run_id: Optional[str] = None) -> Run:
    path = Path(path)
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as e:
        raise RunFileError(f"{path}: cannot read run file: {e}") from e
    return parse_run(text, expected_run_id, source=str(path))


def parse_run(text: str, expected_run_id: Optional[str] = None, source: str = "<string>") -> Run:
    lines = [(i + 1, l) for i, l in enumerate(text.splitlines()) if l.strip()]
    if not lines:
        raise RunFileError(f"{source}: run file is empty")

    run: Optional[Run] = None
    last_seq = 0
    for idx, (lineno, line) in enumerate(lines):
        is_last = idx == len(lines) - 1
        try:
            obj = json.loads(line)
            if not isinstance(obj, dict):
                raise ValueError("line is not a JSON object")
        except ValueError as e:
            # The app can be killed mid-write, so only the last line may be cut off.
            if is_last and run is not None:
                run.truncated = True
                run.warnings.append(f"last line {lineno} is truncated and was ignored")
                break
            raise RunFileError(f"{source}:{lineno}: invalid JSON: {e}") from e

        kind = obj.get("type")
        if run is None:
            if kind != "run_start":
                raise RunFileError(f"{source}:{lineno}: first line must be run_start, got {kind!r}")
            run = Run(header=_header(obj, expected_run_id, source, lineno))
            continue

        try:
            if kind == "event":
                item = Event(seq=int(obj["seq"]), t_ms=float(obj["t_ms"]), src=obj["src"], mode=obj["mode"],
                             msg=obj["msg"], level=obj.get("level", "DEBUG"), thread=obj.get("thread", ""))
            elif kind == "net":
                if obj["phase"] not in ("REQ", "RSP"):
                    raise ValueError(f"bad phase {obj['phase']!r}")
                item = NetEvent(seq=int(obj["seq"]), t_ms=float(obj["t_ms"]), phase=obj["phase"],
                                req_id=int(obj["req_id"]), url=obj["url"], status=obj.get("status"),
                                dur_ms=obj.get("dur_ms"))
            elif kind == "run_end":
                run.end = RunEnd(seq=int(obj["seq"]), t_ms=float(obj["t_ms"]), reason=obj.get("reason", ""))
                continue
            elif kind == "run_start":
                raise ValueError("duplicate run_start")
            else:
                run.warnings.append(f"line {lineno}: unknown type {kind!r} ignored")
                continue
        except (KeyError, ValueError, TypeError) as e:
            if is_last:
                run.truncated = True
                run.warnings.append(f"last line {lineno} is incomplete and was ignored")
                break
            raise RunFileError(f"{source}:{lineno}: invalid {kind} record: {e!r}") from e

        if item.seq <= last_seq:
            run.warnings.append(f"line {lineno}: seq {item.seq} is not increasing")
        last_seq = max(last_seq, item.seq)
        run.events.append(item)

    if run.end is None:
        run.warnings.append("run_end is missing (app was killed or file was pulled early)")
    return run


def _header(obj, expected_run_id, source, lineno) -> RunHeader:
    schema = obj.get("schema")
    if schema != SCHEMA_VERSION:
        raise RunFileError(f"{source}:{lineno}: unsupported schema {schema!r}, expected {SCHEMA_VERSION}")
    for key in ("run_id", "platform"):
        if not obj.get(key):
            raise RunFileError(f"{source}:{lineno}: run_start is missing {key!r}")
    if expected_run_id is not None and obj["run_id"] != expected_run_id:
        raise RunFileError(
            f"{source}: run_id mismatch, expected {expected_run_id!r}, file has {obj['run_id']!r}")
    t0 = obj.get("t0", "process_start")
    if t0 not in ("process_start", "app_init"):
        raise RunFileError(f"{source}:{lineno}: unknown t0 {t0!r}")
    return RunHeader(
        run_id=obj["run_id"], schema=schema, platform=obj["platform"], app_id=obj.get("app_id", ""),
        app_version=obj.get("app_version", ""), build=obj.get("build", ""), debuggable=obj.get("debuggable"),
        os=str(obj.get("os", "")), device=obj.get("device", ""), t0=t0,
        app_init_ms=float(obj.get("app_init_ms", 0.0)), prewarmed=bool(obj.get("prewarmed", False)))
