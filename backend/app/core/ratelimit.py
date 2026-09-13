"""In-process rate limiting for the few endpoints that are cheap to call and costly to serve.

Sliding window per key (an IP for unauthenticated admin logins, a user id for Mini App calls
that reach Gemini or Telegram). The backend runs as a single instance, like the JobQueue, so
process memory is the right place; a restart simply forgets the counters.
"""

import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field

from fastapi import HTTPException, Request

# Empty keys collect quickly under churn; sweep them every so often instead of on every hit.
_SWEEP_EVERY_SECONDS = 60.0


@dataclass
class SlidingWindowLimiter:
    limit: int
    window_seconds: float
    _hits: dict[str, deque[float]] = field(default_factory=dict, repr=False)
    _last_sweep: float = field(default=0.0, repr=False)

    def hit(self, key: str, now: float | None = None) -> bool:
        """Record one call for `key`; False when the window is already full."""
        current = time.monotonic() if now is None else now
        cutoff = current - self.window_seconds
        bucket = self._hits.setdefault(key, deque())
        while bucket and bucket[0] <= cutoff:
            bucket.popleft()
        if len(bucket) >= self.limit:
            return False
        bucket.append(current)
        if current - self._last_sweep >= _SWEEP_EVERY_SECONDS:
            self._sweep(cutoff, current)
        return True

    def _sweep(self, cutoff: float, now: float) -> None:
        for key in [
            key for key, bucket in self._hits.items() if not bucket or bucket[-1] <= cutoff
        ]:
            del self._hits[key]
        self._last_sweep = now

    def reset(self) -> None:
        self._hits.clear()


# Browser logins into the admin panel: the widget/OIDC payloads are signed, but the endpoints
# are unauthenticated and `oauth/start` allocates server state.
ADMIN_LOGIN_LIMITER = SlidingWindowLimiter(limit=10, window_seconds=60)
# Mini App calls that end in a Gemini generation or a Telegram invoice for the caller.
DIALOG_LIMITER = SlidingWindowLimiter(limit=20, window_seconds=60)

TOO_MANY_LOGINS_DETAIL = "Too many login attempts, try again in a minute"


def client_ip(request: Request) -> str:
    """The caller's address as seen through the platform proxy (Railway sets X-Forwarded-For)."""
    forwarded = request.headers.get("X-Forwarded-For", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def rate_limited_by_ip(limiter: SlidingWindowLimiter) -> Callable[[Request], None]:
    """Route dependency: 429 once the caller's IP has used up the window."""

    def dependency(request: Request) -> None:
        if not limiter.hit(client_ip(request)):
            raise HTTPException(status_code=429, detail=TOO_MANY_LOGINS_DETAIL)

    return dependency
