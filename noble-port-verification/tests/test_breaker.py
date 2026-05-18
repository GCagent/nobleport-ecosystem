import time

from app.security.breaker import CircuitBreaker


def test_opens_after_threshold():
    cb = CircuitBreaker(fail_threshold=3, reset_after_s=60)
    for _ in range(3):
        cb.record_failure()
    assert not cb.allow()


def test_resets_after_window(monkeypatch):
    cb = CircuitBreaker(fail_threshold=2, reset_after_s=1)
    cb.record_failure(); cb.record_failure()
    assert not cb.allow()
    time.sleep(1.05)
    assert cb.allow()


def test_success_clears():
    cb = CircuitBreaker(fail_threshold=2, reset_after_s=60)
    cb.record_failure()
    cb.record_success()
    cb.record_failure()
    assert cb.allow()
