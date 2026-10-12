"""Tiny in-memory sliding-window rate limiter.

Good for one server process (our case now). When we add Redis later, only this
file needs to change. Behind a reverse proxy, request.client.host is the proxy's
address - configure the proxy headers then.
"""
import threading
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request, status

_hits: dict[str, deque[float]] = defaultdict(deque)
_lock = threading.Lock()
_calls = 0


def _purge(now: float) -> None:
    """Forget keys that were not used for an hour (keeps memory small)."""
    stale = [k for k, q in _hits.items() if not q or q[-1] <= now - 3600]
    for k in stale:
        del _hits[k]


def check(key: str, limit: int, window_sec: int, now: float | None = None) -> None:
    """Allow at most `limit` calls per `window_sec` for this key, else raise 429."""
    global _calls
    now = time.monotonic() if now is None else now
    with _lock:
        _calls += 1
        if _calls % 1000 == 0:
            _purge(now)
        hits = _hits[key]
        while hits and hits[0] <= now - window_sec:
            hits.popleft()
        if len(hits) >= limit:
            retry_after = max(1, int(window_sec - (now - hits[0])) + 1)
            raise HTTPException(
                status.HTTP_429_TOO_MANY_REQUESTS,
                "Too many requests. Please try again later.",
                headers={"Retry-After": str(retry_after)},
            )
        hits.append(now)


def reset() -> None:
    """Clear all counters (used by tests)."""
    with _lock:
        _hits.clear()


def ip_limiter(name: str, limit: int, window_sec: int):
    """FastAPI dependency: limit calls per client IP."""

    def dependency(request: Request) -> None:
        ip = request.client.host if request.client else "unknown"
        check(f"{name}:{ip}", limit, window_sec)

    return dependency
