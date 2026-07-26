"""WSGI API and static web adapter for the playable vertical-slice MVP."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Callable, Iterable
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from football_world.model import ConsistencyViolation  # noqa: E402
from football_world.service import WorldService  # noqa: E402
from football_world.store import configured_store  # noqa: E402

ASSETS = ROOT / "web"
service = WorldService(configured_store())


def _json(start: Callable[..., object], status: str, payload: object) -> list[bytes]:
    body = json.dumps(payload, ensure_ascii=False, default=str).encode()
    start(status, [("Content-Type", "application/json; charset=utf-8"), ("Cache-Control", "no-store"), ("Content-Length", str(len(body)))])
    return [body]


def _body(environ: dict[str, object]) -> dict[str, object]:
    length = int(environ.get("CONTENT_LENGTH") or 0)
    raw = environ["wsgi.input"].read(length) if length else b"{}"  # type: ignore[union-attr]
    return json.loads(raw or b"{}")


def _api(method: str, path: str, environ: dict[str, object]) -> object:
    if method == "GET" and path in {"/api/health", "/health"}: return {"status": "ok", "storage": service.store.description}
    if method == "GET" and path == "/api/world": return service.summary()
    if method == "POST" and path == "/api/world/new":
        data = _body(environ); return service.new_world(int(data.get("seed", 1908)), str(data.get("scenario", "EGYPT_1934")))
    if method == "POST" and path == "/api/world/advance":
        data = _body(environ); return service.advance(str(data.get("mode", "")), int(data.get("amount", 1)))
    if method == "GET" and path == "/api/teams": return service.teams()
    if method == "GET" and path.startswith("/api/teams/"): return service.team(unquote(path.removeprefix("/api/teams/")))
    if method == "GET" and path == "/api/competitions": return service.competitions()
    if method == "GET" and path.startswith("/api/competitions/"): return service.competition(unquote(path.removeprefix("/api/competitions/")))
    if method == "GET" and path == "/api/matches": return service.matches()
    if method == "GET" and path == "/api/timeline": return service.timeline()
    if method == "GET" and path == "/api/audit": return service.audit()
    if method == "POST" and path == "/api/save": return service.save()
    if method == "GET" and path == "/api/save": return service.saved()
    if method == "POST" and path == "/api/load": return service.load_save()
    raise KeyError(path)


def app(environ: dict[str, object], start_response: Callable[..., object]) -> Iterable[bytes]:
    path = str(environ.get("PATH_INFO", "/")).rstrip("/") or "/"
    method = str(environ.get("REQUEST_METHOD", "GET")).upper()
    try:
        if path.startswith("/api/") or path == "/health":
            return _json(start_response, "200 OK", {"ok": True, "data": _api(method, path, environ)})
        if path == "/assets/app.css": return _file(start_response, ASSETS / "app.css", "text/css; charset=utf-8")
        if path == "/assets/app.js": return _file(start_response, ASSETS / "app.js", "text/javascript; charset=utf-8")
        if path == "/" or path in {"/teams", "/competitions", "/matches", "/timeline", "/audit", "/settings"} or path.startswith(("/teams/", "/competitions/")):
            return _file(start_response, ASSETS / "index.html", "text/html; charset=utf-8")
        raise KeyError(path)
    except ConsistencyViolation as error:
        return _json(start_response, "409 Conflict", {"ok": False, "error": "CONSISTENCY_VIOLATION", "violation": error.record})
    except (ValueError, json.JSONDecodeError) as error:
        return _json(start_response, "400 Bad Request", {"ok": False, "error": "INVALID_REQUEST", "message": str(error)})
    except KeyError as error:
        return _json(start_response, "404 Not Found", {"ok": False, "error": "NOT_FOUND", "message": str(error)})
    except Exception as error:
        return _json(start_response, "500 Internal Server Error", {"ok": False, "error": "INTERNAL_ERROR", "message": str(error)})


def _file(start: Callable[..., object], path: Path, content_type: str) -> list[bytes]:
    body = path.read_bytes()
    start("200 OK", [("Content-Type", content_type), ("Content-Length", str(len(body)))])
    return [body]


application = app

if __name__ == "__main__":
    from wsgiref.simple_server import make_server
    with make_server("127.0.0.1", 8000, app) as server:
        print("Football World MVP: http://127.0.0.1:8000")
        server.serve_forever()
