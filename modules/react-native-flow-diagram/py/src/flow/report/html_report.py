"""Interactive single-file HTML report: zoomable timeline, filterable table and network view.

The page loads D3 and Tabulator from a CDN, the measured data is embedded as JSON.
"""
import html
import json
import webbrowser
from dataclasses import asdict, is_dataclass
from datetime import datetime
from pathlib import Path

from events.keys import (
    MSG_PARAM, TIME_PARAM, DURATION_PARAM, TYPE_PARAM, TYPE_NET, TYPE_AD, TYPE_IOS, SYNC_ASYNC_PARAM, ASYNC,
    REQ_RSP_PARAM, LEVEL_PARAM, REQ, RSP,
)
from report.calc_average import COUNT_PARAM, MIN_TIME_PARAM, MAX_TIME_PARAM, ALL_TIME_PARAM

TEMPLATES = Path(__file__).resolve().parent / "templates"
CSS_PLACEHOLDER = "/*__FLOW_CSS__*/"
JS_PLACEHOLDER = "/*__FLOW_JS__*/"
DATA_PLACEHOLDER = "/*__FLOW_DATA__*/"
TITLE_PLACEHOLDER = "__FLOW_TITLE__"

KIND_NATIVE = "native"
KIND_RN = "rn"
KIND_NET_REQ = "net_req"
KIND_NET_RSP = "net_rsp"
KIND_ASYNC = "async"


def event_kind(item) -> str:
    """Same precedence as the PNG colors in visualize.py."""
    type_param = item[TYPE_PARAM]
    kind = KIND_NATIVE if type_param in (TYPE_AD, TYPE_IOS) else KIND_RN
    if item.get(SYNC_ASYNC_PARAM) == ASYNC:
        kind = KIND_ASYNC
    if type_param == TYPE_NET and item.get(REQ_RSP_PARAM) == REQ:
        kind = KIND_NET_REQ
    if type_param == TYPE_NET and item.get(REQ_RSP_PARAM) == RSP:
        kind = KIND_NET_RSP
    return kind


def build_payload(input_averages, params, meta=None, runs=(), failures=()) -> dict:
    events = []
    for index, item in enumerate(input_averages):
        kind = event_kind(item)
        is_marker = kind in (KIND_ASYNC, KIND_NET_REQ)
        all_times = [int(v) for v in str(item.get(ALL_TIME_PARAM, "")).split() if v.lstrip("-").isdigit()]
        events.append({
            "id": index,
            "time": item[TIME_PARAM],
            "duration": 0 if is_marker else item[DURATION_PARAM],
            "start": item[TIME_PARAM] if is_marker else item[TIME_PARAM] - item[DURATION_PARAM],
            "type": item[TYPE_PARAM],
            "kind": kind,
            "mode": item.get(SYNC_ASYNC_PARAM, "") or "",
            "reqRsp": item.get(REQ_RSP_PARAM, "") or "",
            "level": item.get(LEVEL_PARAM, "") or "",
            "msg": item[MSG_PARAM],
            "count": item.get(COUNT_PARAM, len(all_times)),
            "min": item.get(MIN_TIME_PARAM, item[TIME_PARAM]),
            "max": item.get(MAX_TIME_PARAM, item[TIME_PARAM]),
            "all": all_times,
        })

    run_headers = [asdict(r) if is_dataclass(r) else dict(r) for r in runs]
    first = run_headers[0] if run_headers else {}
    # Saved runs know their platform; the CLI value is only a default when reading --from-dir.
    platform = first.get("platform") or getattr(params, "platform", "")
    app_id = first.get("app_id") or (getattr(params, "package", "") if platform == "android"
                                     else getattr(params, "bundle_id", ""))
    return {
        "meta": {
            **(meta or {}),
            "platform": platform,
            "app_id": app_id,
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "launch_times": getattr(params, "launch_times", None),
            "strip_query": list(getattr(params, "strip_query", ()) or ()),
        },
        "events": events,
        "runs": run_headers,
        "failures": [str(f) for f in failures],
    }


def render_html(payload) -> str:
    template = (TEMPLATES / "report.html").read_text(encoding="utf-8")
    css = (TEMPLATES / "report.css").read_text(encoding="utf-8")
    js = (TEMPLATES / "report.js").read_text(encoding="utf-8")
    # "</" would end the <script> block early; "<\/" is the same string for JSON.parse.
    data = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/").replace("<!--", "<\\u0021--")
    meta = payload.get("meta", {})
    title = " · ".join(str(p) for p in ("Flow Diagram", meta.get("app_id"), meta.get("device")) if p)
    # Data goes in last, so text inside the measured messages is never treated as a placeholder.
    page = template.replace(TITLE_PLACEHOLDER, html.escape(title)).replace(CSS_PLACEHOLDER, css)
    return page.replace(JS_PLACEHOLDER, js).replace(DATA_PLACEHOLDER, data)


def save_html_report(input_averages, params, meta=None, runs=(), failures=()):
    print("Saving the interactive HTML report...")
    payload = build_payload(input_averages, params, meta, runs, failures)
    Path(params.html_path).write_text(render_html(payload), encoding="utf-8")
    if getattr(params, "open_html", False):
        webbrowser.open(Path(params.html_path).resolve().as_uri())
