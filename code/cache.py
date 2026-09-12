"""Disk-backed response cache keyed by SHA-256 of the input string."""
import hashlib
import json
from pathlib import Path

_CACHE_DIR = Path(__file__).parent.parent / "cache"


def _path(key: str) -> Path:
    digest = hashlib.sha256(key.encode()).hexdigest()
    return _CACHE_DIR / f"{digest}.json"


def get(key: str) -> dict | None:
    p = _path(key)
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def put(key: str, value: dict) -> None:
    _CACHE_DIR.mkdir(exist_ok=True)
    _path(key).write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    put("test-key", {"answer": 42})
    result = get("test-key")
    assert result == {"answer": 42}, f"expected {{'answer': 42}}, got {result}"
    miss = get("no-such-key")
    assert miss is None, f"expected None, got {miss}"
    print("cache: put/get/miss all pass")
    # cleanup
    _path("test-key").unlink()
    print("cache: test file removed")
