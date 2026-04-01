from __future__ import annotations

import logging
from collections import deque
from datetime import datetime
from time import perf_counter
from typing import Any

from app.common.datetime_utils import utc_now

logger = logging.getLogger(__name__)

_SNAPSHOT_RUNTIME_OBSERVATIONS: deque[dict[str, Any]] = deque(maxlen=20)


def build_observability_summary(
    *,
    snapshot_aggregates: dict[str, Any],
    warn_refresh_age_minutes: int,
) -> dict[str, Any]:
    known_order_count = snapshot_aggregates["known_order_count"]
    total_snapshots = snapshot_aggregates["total_snapshots"]
    latest_refreshed_at = snapshot_aggregates["latest_refreshed_at"]

    coverage_ratio = 1.0 if known_order_count == 0 else round(total_snapshots / known_order_count, 4)
    refresh_age_minutes = None
    if latest_refreshed_at:
        refresh_age_minutes = round(
            (utc_now() - latest_refreshed_at).total_seconds() / 60,
            2,
        )

    alerts: list[dict[str, str]] = []
    if known_order_count > 0 and total_snapshots == 0:
        alerts.append({
            "level": "critical",
            "code": "snapshot_empty",
            "message": "Known orders exist but snapshot table is empty.",
        })
    elif total_snapshots < known_order_count:
        alerts.append({
            "level": "warning",
            "code": "snapshot_coverage_gap",
            "message": f"Snapshot coverage is incomplete ({total_snapshots}/{known_order_count}).",
        })

    if refresh_age_minutes is not None and refresh_age_minutes > warn_refresh_age_minutes:
        alerts.append({
            "level": "warning",
            "code": "snapshot_refresh_age_high",
            "message": (
                f"Latest snapshot refresh age is {refresh_age_minutes} minutes, "
                f"above threshold {warn_refresh_age_minutes}."
            ),
        })

    health_status = "healthy"
    if any(alert["level"] == "critical" for alert in alerts):
        health_status = "critical"
    elif alerts:
        health_status = "warning"

    return {
        "health": {
            "status": health_status,
            "alerts": alerts,
            "warn_refresh_age_minutes": warn_refresh_age_minutes,
        },
        "summary": {
            "known_order_count": known_order_count,
            "total_snapshots": total_snapshots,
            "coverage_ratio": coverage_ratio,
            "status_counts": snapshot_aggregates["status_counts"],
            "refresh_source_counts": snapshot_aggregates["refresh_source_counts"],
            "oldest_refreshed_at": snapshot_aggregates["oldest_refreshed_at"],
            "latest_refreshed_at": latest_refreshed_at,
            "refresh_age_minutes": refresh_age_minutes,
        },
        "runtime_observations": list_runtime_observations(),
    }


def list_runtime_observations() -> list[dict[str, Any]]:
    return list(_SNAPSHOT_RUNTIME_OBSERVATIONS)


def reset_runtime_observations() -> None:
    _SNAPSHOT_RUNTIME_OBSERVATIONS.clear()


def record_runtime_observation(
    *,
    operation: str,
    source: str,
    reason: str,
    started_at: datetime,
    duration_ms: float,
    success: bool,
    summary: dict[str, Any] | None = None,
    error: str | None = None,
) -> None:
    finished_at = utc_now()
    _SNAPSHOT_RUNTIME_OBSERVATIONS.appendleft({
        "operation": operation,
        "source": source,
        "reason": reason,
        "started_at": started_at,
        "finished_at": finished_at,
        "duration_ms": duration_ms,
        "success": success,
        "summary": summary or {},
        "error": error,
    })

    log_level = logging.INFO if success else logging.ERROR
    logger.log(
        log_level,
        "Snapshot observation operation=%s source=%s reason=%s success=%s duration_ms=%s summary=%s error=%s",
        operation,
        source,
        reason,
        success,
        duration_ms,
        summary or {},
        error,
    )


def duration_ms(started_perf: float) -> float:
    return round((perf_counter() - started_perf) * 1000, 2)
