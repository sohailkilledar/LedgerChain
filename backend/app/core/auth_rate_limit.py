from collections import deque
from threading import Lock
from time import monotonic

from fastapi import HTTPException, Request


class AuthRateLimiter:
    """Bounded per-process limiter; production deployments should also limit at the edge."""

    max_buckets = 4096

    def __init__(self) -> None:
        self._attempts: dict[tuple[str, str], deque[float]] = {}
        self._lock = Lock()

    def check(self, request: Request, action: str, *, limit: int, window_seconds: int) -> None:
        client = request.client.host if request.client else "unknown"
        key = (action, client)
        now = monotonic()
        with self._lock:
            attempts = self._attempts.setdefault(key, deque())
            while attempts and now - attempts[0] >= window_seconds:
                attempts.popleft()
            if len(attempts) >= limit:
                retry_after = max(1, int(window_seconds - (now - attempts[0])))
                raise HTTPException(
                    status_code=429,
                    detail="Too many authentication requests. Try again later.",
                    headers={"Retry-After": str(retry_after)},
                )
            attempts.append(now)
            if len(self._attempts) > self.max_buckets:
                oldest_key = min(
                    self._attempts,
                    key=lambda bucket: self._attempts[bucket][0] if self._attempts[bucket] else now,
                )
                if oldest_key != key:
                    del self._attempts[oldest_key]


def enforce_auth_rate_limit(
    request: Request,
    action: str,
    *,
    limit: int,
    window_seconds: int,
) -> None:
    limiter: AuthRateLimiter = request.app.state.auth_rate_limiter
    limiter.check(request, action, limit=limit, window_seconds=window_seconds)
