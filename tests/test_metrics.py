from ratelimmq.metrics import summarize_latencies

def test_latency_summary_basic():
    lat = [0.10, 0.20, 0.30, 0.40, 0.50]  # seconds
    s = summarize_latencies(lat, total_time_s=1.0)
    assert s.count == 5
    assert 100.0 <= s.p50_ms <= 300.0
    assert s.p95_ms >= s.p50_ms
    assert s.p99_ms >= s.p95_ms
    assert s.rps == 5.0
