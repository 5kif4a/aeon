"""DB-free tests for the in-process sliding-window limiter."""

from app.core.ratelimit import SlidingWindowLimiter


def test_window_fills_then_frees_with_time():
    limiter = SlidingWindowLimiter(limit=3, window_seconds=60)
    assert all(limiter.hit("a", now=100 + i) for i in range(3))
    assert limiter.hit("a", now=103) is False
    # Another key has its own window.
    assert limiter.hit("b", now=103) is True
    # The first hit (t=100) leaves the window once it is a full 60 s old.
    assert limiter.hit("a", now=159) is False
    assert limiter.hit("a", now=160) is True


def test_sweep_drops_idle_keys():
    limiter = SlidingWindowLimiter(limit=1, window_seconds=10)
    assert limiter.hit("idle", now=0)
    # A hit much later triggers the sweep; the idle key is gone, the fresh one stays.
    assert limiter.hit("fresh", now=1_000)
    assert set(limiter._hits) == {"fresh"}
