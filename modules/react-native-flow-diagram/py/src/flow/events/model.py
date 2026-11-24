from dataclasses import dataclass, field
from typing import Optional

SCHEMA_VERSION = 2


@dataclass
class RunHeader:
    run_id: str
    schema: int
    platform: str
    app_id: str = ""
    app_version: str = ""
    build: str = ""
    debuggable: Optional[bool] = None
    os: str = ""
    device: str = ""
    t0: str = "process_start"  # "process_start" or "app_init"
    app_init_ms: float = 0.0
    prewarmed: bool = False


@dataclass
class Event:
    seq: int
    t_ms: float
    src: str  # AD, IOS, RN
    mode: str  # SYNC, ASYNC
    msg: str
    level: str = "DEBUG"
    thread: str = ""


@dataclass
class NetEvent:
    seq: int
    t_ms: float
    phase: str  # REQ, RSP
    req_id: int
    url: str
    status: Optional[int] = None
    dur_ms: Optional[float] = None


@dataclass
class RunEnd:
    seq: int
    t_ms: float
    reason: str = ""


@dataclass
class Run:
    header: RunHeader
    events: list = field(default_factory=list)  # Event and NetEvent, file order
    end: Optional[RunEnd] = None
    truncated: bool = False  # last line was cut off
    warnings: list = field(default_factory=list)


@dataclass
class NormalizedRun:
    """entries use the v1 dict shape (see keys.py) so calc_average, CSV and PNG code work unchanged."""
    entries: list
    effective_t0: str
    warnings: list = field(default_factory=list)
