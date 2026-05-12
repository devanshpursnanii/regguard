from __future__ import annotations

import hashlib
import time
from typing import Callable, Iterable, List, Optional, TypeVar

from diskcache import Cache
from ratelimit import limits, sleep_and_retry

from config import LLM_CACHE_DIR, LLM_MAX_RPM

T = TypeVar("T")

_CACHE = Cache(LLM_CACHE_DIR)


def _hash_text(text: str) -> str:
    """Return a stable hash for an input string."""

    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _cache_key(prefix: str, text: str) -> str:
    """Build a cache key for a text payload."""

    return f"{prefix}:{_hash_text(text)}"


@sleep_and_retry
@limits(calls=LLM_MAX_RPM, period=60)
def _rate_limited_call(call_fn: Callable[[], T]) -> T:
    """Invoke the LLM call with a strict rate limit."""

    return call_fn()


def _should_retry(exc: Exception) -> bool:
    """Return True if the exception looks like a quota/rate limit error."""

    message = str(exc)
    return "429" in message or "RESOURCE_EXHAUSTED" in message


def call_with_retry(call_fn: Callable[[], T], max_retries: int = 5) -> T:
    """Call with rate limiting and retry on 429-like errors."""

    for attempt in range(max_retries + 1):
        try:
            return _rate_limited_call(call_fn)
        except Exception as exc:  # noqa: BLE001
            if attempt >= max_retries or not _should_retry(exc):
                raise
            time.sleep(60)
    raise RuntimeError("Exceeded retry attempts")


def cached_text_call(prefix: str, text: str, call_fn: Callable[[], str]) -> str:
    """Return cached LLM text output or execute and store it."""

    key = _cache_key(prefix, text)
    cached = _CACHE.get(key)
    if cached is not None:
        return cached
    result = call_with_retry(call_fn)
    _CACHE.set(key, result)
    return result


def cached_batch_call(
    prefix: str,
    texts: List[str],
    call_fn: Callable[[List[str]], List[T]],
) -> List[Optional[T]]:
    """Return cached results for a batch, calling the LLM for missing items."""

    results: List[Optional[T]] = [None] * len(texts)
    missing_texts: List[str] = []
    missing_indexes: List[int] = []

    for idx, text in enumerate(texts):
        key = _cache_key(prefix, text)
        cached = _CACHE.get(key)
        if cached is not None:
            results[idx] = cached
        else:
            missing_texts.append(text)
            missing_indexes.append(idx)

    if missing_texts:
        fetched = call_with_retry(lambda: call_fn(missing_texts))
        for idx, text, value in zip(missing_indexes, missing_texts, fetched):
            key = _cache_key(prefix, text)
            _CACHE.set(key, value)
            results[idx] = value

    return results
