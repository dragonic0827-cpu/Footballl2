from __future__ import annotations

import json
import os
from abc import ABC, abstractmethod
from pathlib import Path
from urllib.request import Request, urlopen


class WorldStore(ABC):
    @abstractmethod
    def get(self, key: str) -> str | None: ...

    @abstractmethod
    def put(self, key: str, value: str) -> None: ...

    @property
    @abstractmethod
    def description(self) -> str: ...


class FileWorldStore(WorldStore):
    def __init__(self, directory: Path | None = None) -> None:
        self.directory = directory or Path(os.environ.get("FOOTBALL_WORLD_DATA_DIR", "/tmp/football-world"))
        self.directory.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        return self.directory / f"{key.replace('/', '_')}.json"

    def get(self, key: str) -> str | None:
        path = self._path(key)
        return path.read_text(encoding="utf-8") if path.exists() else None

    def put(self, key: str, value: str) -> None:
        target = self._path(key)
        temporary = target.with_suffix(".tmp")
        temporary.write_text(value, encoding="utf-8")
        temporary.replace(target)

    @property
    def description(self) -> str:
        return "LOCAL_FILE_EPHEMERAL"


class RedisRestWorldStore(WorldStore):
    """Minimal Upstash/Vercel-KV REST adapter without runtime dependencies."""

    def __init__(self, url: str, token: str) -> None:
        self.url, self.token = url.rstrip("/"), token

    def _call(self, command: list[str]) -> object:
        request = Request(self.url, data=json.dumps(command).encode(), headers={"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"}, method="POST")
        with urlopen(request, timeout=8) as response:
            payload = json.load(response)
        if "error" in payload:
            raise RuntimeError(f"persistent store error: {payload['error']}")
        return payload.get("result")

    def get(self, key: str) -> str | None:
        result = self._call(["GET", key])
        return None if result is None else str(result)

    def put(self, key: str, value: str) -> None:
        self._call(["SET", key, value])

    @property
    def description(self) -> str:
        return "REDIS_REST_PERSISTENT"


def configured_store() -> WorldStore:
    url = os.environ.get("KV_REST_API_URL") or os.environ.get("UPSTASH_REDIS_REST_URL")
    token = os.environ.get("KV_REST_API_TOKEN") or os.environ.get("UPSTASH_REDIS_REST_TOKEN")
    return RedisRestWorldStore(url, token) if url and token else FileWorldStore()
