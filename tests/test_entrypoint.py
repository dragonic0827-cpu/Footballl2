import json
from pathlib import Path

from index import app


def test_vercel_entrypoint_exists_and_exports_wsgi_app() -> None:
    assert Path("index.py").is_file()


def test_vercel_routes_every_request_to_python_entrypoint() -> None:
    config = json.loads(Path("vercel.json").read_text(encoding="utf-8"))
    assert config["builds"] == [{"src": "index.py", "use": "@vercel/python"}]
    assert config["routes"] == [{"src": "/(.*)", "dest": "/index.py"}]


def test_no_python_project_config_can_break_vercel_parser() -> None:
    # This dependency-free app needs no package build metadata. Keeping pytest's
    # settings in pytest.ini prevents a damaged pyproject merge from blocking
    # Vercel before it can build the explicitly configured Python function.
    assert not Path("pyproject.toml").exists()


def request(path: str) -> tuple[str, dict[str, str], bytes]:
    response: dict[str, object] = {}

    def start_response(status: str, headers: list[tuple[str, str]]) -> None:
        response["status"] = status
        response["headers"] = dict(headers)

    body = b"".join(app({"PATH_INFO": path, "REQUEST_METHOD": "GET"}, start_response))
    return str(response["status"]), response["headers"], body


def test_root_is_a_runnable_korean_landing_page() -> None:
    status, headers, body = request("/")
    assert status == "200 OK"
    assert headers["Content-Type"].startswith("text/html")
    assert "축구 세계는" in body.decode()


def test_health_exposes_world_boot_status() -> None:
    status, headers, body = request("/api/health")
    payload = json.loads(body)
    assert status == "200 OK"
    assert headers["Content-Type"].startswith("application/json")
    assert payload == {
        "competitionEditions": 2,
        "saveVersion": 1,
        "service": "football-world",
        "status": "ok",
        "teams": 2,
        "worldDate": "1908-01-01",
    }


def test_unknown_route_is_404() -> None:
    status, _, body = request("/missing")
    assert status == "404 Not Found"
    assert json.loads(body)["error"] == "not_found"
