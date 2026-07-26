"""Dependency-free WSGI entrypoint used by Vercel's Python runtime."""

from __future__ import annotations

import json
import sys
from datetime import date
from html import escape
from pathlib import Path
from typing import Callable, Iterable

# Vercel invokes this file directly rather than installing the src-layout package.
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from football_world.engine import build_early_world  # noqa: E402


def _snapshot() -> dict[str, object]:
    world = build_early_world()
    return {
        "service": "football-world",
        "status": "ok",
        "saveVersion": world.save_version,
        "worldDate": world.current_date.isoformat(),
        "teams": len(world.teams),
        "competitionEditions": len(world.editions),
    }


def _html(snapshot: dict[str, object]) -> bytes:
    cards = "".join(
        f'<div class="card"><strong>{escape(label)}</strong><span>{escape(str(value))}</span></div>'
        for label, value in (
            ("세계 시작일", snapshot["worldDate"]),
            ("세이브 버전", snapshot["saveVersion"]),
            ("등록 대표팀", snapshot["teams"]),
            ("대회 회차", snapshot["competitionEditions"]),
        )
    )
    return f"""<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>축구 세계 시뮬레이터</title><style>
:root {{ color-scheme: dark; font-family: system-ui,sans-serif; background:#07150f; color:#f4f7f5 }}
body {{ margin:0; min-height:100vh; display:grid; place-items:center; background:radial-gradient(circle at top,#174a32,#07150f 55%) }}
main {{ width:min(760px,calc(100% - 40px)); padding:48px 0 }}
.eyebrow {{ color:#75e6aa; font-weight:700; letter-spacing:.15em }} h1 {{ font-size:clamp(2rem,6vw,4rem); margin:.25em 0 }}
p {{ color:#b8c9c0; font-size:1.1rem; line-height:1.7 }} .grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(150px,1fr)); gap:14px; margin-top:32px }}
.card {{ display:flex; flex-direction:column; gap:10px; padding:20px; border:1px solid #347456; border-radius:14px; background:#0b2118cc }}
.card strong {{ color:#9cb5a7; font-size:.85rem }} .card span {{ font-size:1.35rem;font-weight:800 }} .status {{ display:inline-flex;align-items:center;gap:8px }}
.dot {{ width:9px;height:9px;border-radius:50%;background:#5ff29e;box-shadow:0 0 12px #5ff29e }}
</style></head><body><main><div class="eyebrow">HISTORY CONTINUES</div><h1>축구 세계는<br>과거를 기억합니다.</h1>
<p>1908년부터 이어지는 결정론적 국가대표 축구 역사 시뮬레이션 코어가 실행 중입니다.</p>
<p class="status"><span class="dot"></span> API 정상 · <code>/api/health</code></p><div class="grid">{cards}</div></main></body></html>""".encode()


def app(environ: dict[str, object], start_response: Callable[..., object]) -> Iterable[bytes]:
    """Serve the project landing page and a deployment health endpoint."""
    path = str(environ.get("PATH_INFO", "/")).rstrip("/") or "/"
    snapshot = _snapshot()
    if path in {"/api/health", "/health"}:
        body = json.dumps(snapshot, ensure_ascii=False, sort_keys=True).encode()
        start_response("200 OK", [("Content-Type", "application/json; charset=utf-8"), ("Content-Length", str(len(body)))])
        return [body]
    if path == "/":
        body = _html(snapshot)
        start_response("200 OK", [("Content-Type", "text/html; charset=utf-8"), ("Content-Length", str(len(body)))])
        return [body]
    body = json.dumps({"error": "not_found", "path": path}).encode()
    start_response("404 Not Found", [("Content-Type", "application/json; charset=utf-8"), ("Content-Length", str(len(body)))])
    return [body]


# Some Python deployment adapters look for either `app` or `application`.
application = app


if __name__ == "__main__":
    from wsgiref.simple_server import make_server

    with make_server("127.0.0.1", 8000, app) as server:
        print("Football World listening on http://127.0.0.1:8000")
        server.serve_forever()
