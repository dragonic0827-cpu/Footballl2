import json
from io import BytesIO
from pathlib import Path

import pytest

import api.index as web_api
from football_world.persistence import dumps_world
from football_world.store import FileWorldStore
from index import app


def test_vercel_entrypoint_exists_and_exports_wsgi_app() -> None:
    assert Path("index.py").is_file()


def test_vercel_routes_every_request_to_python_entrypoint() -> None:
    config = json.loads(Path("vercel.json").read_text(encoding="utf-8"))
    assert config["builds"] == [{"src": "index.py", "use": "@vercel/python", "config": {"includeFiles": ["web/**", "src/**"]}}]
    assert config["routes"] == [{"src": "/(.*)", "dest": "/index.py"}]


def test_no_python_project_config_can_break_vercel_parser() -> None:
    # This dependency-free app needs no package build metadata. Keeping pytest's
    # settings in pytest.ini prevents a damaged pyproject merge from blocking
    # Vercel before it can build the explicitly configured Python function.
    assert not Path("pyproject.toml").exists()


@pytest.fixture(autouse=True)
def isolated_store(tmp_path) -> None:
    web_api.service.store = FileWorldStore(tmp_path)


def request(path: str, method: str = "GET", payload: object | None = None) -> tuple[str, dict[str, str], bytes]:
    response: dict[str, object] = {}

    def start_response(status: str, headers: list[tuple[str, str]]) -> None:
        response["status"] = status
        response["headers"] = dict(headers)

    raw = json.dumps(payload).encode() if payload is not None else b""
    body = b"".join(app({"PATH_INFO": path, "REQUEST_METHOD": method, "CONTENT_LENGTH": str(len(raw)), "wsgi.input": BytesIO(raw)}, start_response))
    return str(response["status"]), response["headers"], body


def test_root_is_a_runnable_korean_landing_page() -> None:
    status, headers, body = request("/")
    assert status == "200 OK"
    assert headers["Content-Type"].startswith("text/html")
    page = body.decode()
    assert "개발용 수직 슬라이스" in page
    assert "/assets/app.js" in page
    assert "대표팀" in page and "대회" in page and "설정" in page


def test_health_exposes_world_boot_status() -> None:
    status, headers, body = request("/api/health")
    payload = json.loads(body)
    assert status == "200 OK"
    assert headers["Content-Type"].startswith("application/json")
    assert payload == {"ok": True, "data": {"status": "ok", "storage": "LOCAL_FILE_EPHEMERAL"}}


def test_unknown_route_is_404() -> None:
    status, _, body = request("/missing")
    assert status == "404 Not Found"
    assert json.loads(body)["error"] == "NOT_FOUND"


def data(path: str, method: str = "GET", payload: object | None = None):
    status, _, body = request(path, method, payload)
    parsed = json.loads(body)
    assert status.startswith("200"), parsed
    return parsed["data"]


def test_playable_api_flow_persists_advances_and_restores_save() -> None:
    created = data("/api/world/new", "POST", {"seed": 4242, "scenario": "EGYPT_1934"})
    assert created["date"] == "1934-01-01" and created["seed"] == 4242
    first = data("/api/world/advance", "POST", {"mode": "NEXT_EVENT", "amount": 1})
    assert first["date"] == "1934-05-01"
    data("/api/save", "POST")
    data("/api/world/advance", "POST", {"mode": "NEXT_EVENT", "amount": 1})
    assert data("/api/matches")[0]["winner"] == "EGY"
    restored = data("/api/load", "POST")
    assert restored["date"] == "1934-05-01" and restored["matchCount"] == 0


def test_full_egypt_scenario_reaches_1938_with_champion_memory() -> None:
    data("/api/world/new", "POST", {"seed": 17})
    for _ in range(6): data("/api/world/advance", "POST", {"mode": "NEXT_EVENT", "amount": 1})
    wc34 = data("/api/competitions/WC1934")
    wc38 = data("/api/competitions/WC1938")
    assert wc34["championId"] == "EGY"
    assert wc38["applications"]["EGY"] == "AUTO_DEFENDING_CHAMPION"
    assert wc38["finalists"] == ["EGY", "ITA"]


def test_invalid_advance_and_consistency_violation_are_structured() -> None:
    status, _, body = request("/api/world/advance", "POST", {"mode": "CENTURY", "amount": 1})
    assert status == "400 Bad Request" and json.loads(body)["error"] == "INVALID_REQUEST"
    world = web_api.service._load()
    world.entities["EGY"].existed_until = world.current_date
    web_api.service.store.put("current", dumps_world(world))
    data("/api/world/advance", "POST", {"mode": "NEXT_EVENT", "amount": 1})
    status, _, body = request("/api/world/advance", "POST", {"mode": "NEXT_EVENT", "amount": 1})
    payload = json.loads(body)
    assert status == "409 Conflict"
    assert payload["error"] == "CONSISTENCY_VIOLATION"
    assert payload["violation"]["automaticRepairAllowed"] is False


def test_collection_apis_and_javascript_button_connections() -> None:
    assert len(data("/api/teams")) == 2
    assert len(data("/api/competitions")) == 2
    assert data("/api/matches") == []
    assert data("/api/audit") == []
    script = Path("web/app.js").read_text(encoding="utf-8")
    for endpoint in ("/api/world/advance", "/api/world/new", "/api/save", "/api/load"):
        assert endpoint in script
    for label in ("하루 진행", "일주일 진행", "한 달 진행", "다음 이벤트", "1년 진행"):
        assert label in script
