from prometheus_client import Counter, Gauge, Histogram, start_http_server

# Metrics definitions (using recommended names and units)
REQUESTS_TOTAL = Counter(
    "ratelimmq_requests_total", 
    "Total number of URL fetch requests processed"
)
REQUEST_FAILURES_TOTAL = Counter(
    "ratelimmq_request_failures_total", 
    "Total number of URL fetch requests that failed"
)
REQUESTS_IN_PROGRESS = Gauge(
    "ratelimmq_requests_in_progress", 
    "Number of URL fetch requests currently in progress"
)
QUEUE_SIZE = Gauge(
    "ratelimmq_queue_size", 
    "Number of URL fetch requests waiting in the queue"
)
REQUEST_LATENCY_SECONDS = Histogram(
    "ratelimmq_request_latency_seconds", 
    "Latency of URL fetch requests in seconds"
    # (Optional: you can define custom buckets if needed, e.g. buckets=[0.1, 0.5, 1, 2, 5, 10])
)

# Start the Prometheus metrics server on a background thread (non-blocking for main loop)
METRICS_PORT = 8000  # Port for the metrics HTTP endpoint (adjust as needed or make configurable)
start_http_server(METRICS_PORT)
