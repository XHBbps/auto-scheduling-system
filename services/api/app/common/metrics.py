"""Prometheus metrics definitions for the auto-scheduling system."""

from prometheus_client import Counter, Gauge, Histogram, Info

# --- HTTP request metrics ---
http_requests_total = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status_code"],
)

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "endpoint"],
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0),
)

# --- Background task metrics ---
background_task_total = Counter(
    "background_task_total",
    "Total background tasks executed",
    ["task_type", "status"],
)

background_task_duration_seconds = Histogram(
    "background_task_duration_seconds",
    "Background task execution duration in seconds",
    ["task_type"],
    buckets=(0.1, 0.5, 1.0, 5.0, 10.0, 30.0, 60.0, 300.0, 600.0, 1800.0),
)

# --- Sync job metrics ---
sync_job_total = Counter(
    "sync_job_total",
    "Total sync jobs completed",
    ["job_type", "status"],
)

sync_records_processed = Counter(
    "sync_records_processed_total",
    "Total records processed during sync",
    ["job_type", "result"],
)

# --- System metrics ---
db_pool_size = Gauge(
    "db_pool_size",
    "Current database connection pool size",
)

db_pool_checked_out = Gauge(
    "db_pool_checked_out",
    "Database connections currently checked out",
)

app_info = Info(
    "app",
    "Application information",
)
