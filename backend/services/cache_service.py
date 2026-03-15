import hashlib
import json
import threading
import time
from typing import Any


_CACHE: dict[str, tuple[float, Any]] = {}
_LOCK = threading.Lock()


def _cleanup_expired(now: float) -> None:
    expired_keys = [key for key, (expires_at, _) in _CACHE.items() if expires_at <= now]
    for key in expired_keys:
        _CACHE.pop(key, None)


def make_cache_key(prefix: str, value: Any) -> str:
    if isinstance(value, (dict, list, tuple)):
        raw_value = json.dumps(value, ensure_ascii=False, sort_keys=True)
    else:
        raw_value = str(value)
    digest = hashlib.sha256(raw_value.encode("utf-8")).hexdigest()
    return f"{prefix}:{digest}"


def get_cache(key: str) -> Any | None:
    now = time.time()
    with _LOCK:
        item = _CACHE.get(key)
        if not item:
            return None
        expires_at, value = item
        if expires_at <= now:
            _CACHE.pop(key, None)
            return None
        return value


def set_cache(key: str, value: Any, ttl_seconds: int) -> Any:
    now = time.time()
    expires_at = now + max(ttl_seconds, 1)
    with _LOCK:
        if len(_CACHE) > 512:
            _cleanup_expired(now)
        _CACHE[key] = (expires_at, value)
    return value
