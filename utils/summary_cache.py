from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Iterable, Optional

from config import RAPTOR_CACHE_DIR


def _cache_path(key: str) -> Path:
    """Return the cache file path for a given key."""

    cache_dir = Path(RAPTOR_CACHE_DIR)
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir / f"{key}.json"


def _hash_payload(parts: Iterable[str]) -> str:
    """Hash summary inputs to produce a stable cache key."""

    hasher = hashlib.sha256()
    for part in parts:
        hasher.update(part.encode("utf-8"))
        hasher.update(b"\n")
    return hasher.hexdigest()


def get_cached_summary(parts: Iterable[str]) -> Optional[str]:
    """Return cached summary text for the given parts, if present."""

    key = _hash_payload(parts)
    path = _cache_path(key)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return data.get("summary")


def store_cached_summary(parts: Iterable[str], summary: str) -> None:
    """Persist a summary to the cache."""

    key = _hash_payload(parts)
    path = _cache_path(key)
    payload = {"summary": summary}
    path.write_text(json.dumps(payload, ensure_ascii=True), encoding="utf-8")
