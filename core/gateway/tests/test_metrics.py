import pytest

from core.gateway import metrics


def test_percentile_empty():
    assert metrics.percentile([], 95) is None


def test_percentile_p95():
    data = list(range(1, 101))  # 1..100
    assert metrics.percentile(data, 95) == 95
    assert metrics.percentile(data, 50) == 50
    assert metrics.percentile(data, 100) == 100


def test_percentile_single():
    assert metrics.percentile([42], 95) == 42


def test_percentile_bad_pct():
    with pytest.raises(ValueError):
        metrics.percentile([1, 2, 3], 150)


def test_summarize():
    s = metrics.summarize([10, 20, 30, 40, 50])
    assert s["count"] == 5
    assert s["max_ms"] == 50
    assert s["p50_ms"] == 30
