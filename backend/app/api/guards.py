import hashlib
import time
from collections import defaultdict, deque

from starlette.requests import Request

WINDOW_SECONDS = 60.0


def fingerprint(request: Request, salt: str) -> str:
    """Anonymous, salted identity of a visitor; the raw IP never leaves this function."""
    forwarded = request.headers.get("x-forwarded-for", "")
    ip = forwarded.split(",")[0].strip() or (request.client.host if request.client else "")
    agent = request.headers.get("user-agent", "")
    return hashlib.sha256(f"{salt}|{ip}|{agent}".encode()).hexdigest()[:16]


class RateLimiter:
    """In-memory sliding window; correct only while the service runs a single instance."""

    def __init__(self, per_minute: int):
        self._per_minute = per_minute
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        hits = self._hits[key]
        while hits and now - hits[0] > WINDOW_SECONDS:
            hits.popleft()
        if len(hits) >= self._per_minute:
            return False
        hits.append(now)
        return True
