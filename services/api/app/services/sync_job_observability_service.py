import re
from typing import Any

from sqlalchemy import case, desc, func, literal, select, true, union_all
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.datetime_utils import utc_now
from app.models.bom_relation import BomRelationSrc
from app.models.data_issue import DataIssueRecord
from app.models.order_schedule_snapshot import OrderScheduleSnapshot
from app.models.sync_job_log import SyncJobLog
from app.repository.bom_backfill_queue_repo import BomBackfillQueueRepo

_NUMBER_PATTERNS: dict[str, re.Pattern[str]] = {
    "candidate_orders": re.compile(r"候选订单\s*(\d+)"),
    "candidate_items": re.compile(r"候选物料\s*(\d+)"),
    "enqueued_items": re.compile(r"入队\s*(\d+)"),
    "reactivated_items": re.compile(r"重激活\s*(\d+)"),
    "already_tracked_items": re.compile(r"已跟踪\s*(\d+)"),
    "processed_items": re.compile(r"本轮处理\s*(\d+)"),
    "deferred_items": re.compile(r"(?:待重试|待后续继续)\s*(\d+)"),
    "success_count": re.compile(r"成功\s*(\d+)"),
    "fail_count": re.compile(r"失败\s*(\d+)"),
    "retry_wait_items": re.compile(r"待重试\s*(\d+)"),
    "failed_items": re.compile(r"永久失败\s*(\d+)"),
    "drawing_updated_count": re.compile(r"发图状态回填\s*(\d+)"),
    "baseline_groups_processed": re.compile(r"整机周期基准重建\s*(\d+)"),
    "baseline_rebuild_enqueued": re.compile(r"零件周期基准重建任务已入队\s*(\d+)"),
    "eligible_groups": re.compile(r"符合条件\s*(\d+)"),
    "promoted_groups": re.compile(r"提升\s*(\d+)"),
    "persisted_groups": re.compile(r"落库\s*(\d+)"),
    "manual_protected_groups": re.compile(r"手工保护\s*(\d+)"),
    "deactivated_groups": re.compile(r"停用\s*(\d+)"),
    "snapshot_refreshed": re.compile(r"刷新快照\s*(\d+)"),
    "refreshed_order_count": re.compile(r"刷新快照\s*(\d+)"),
    "closed_issue_count": re.compile(r"收口缺 BOM 异常\s*(\d+)"),
}
_BATCH_PATTERN = re.compile(r"(?:批次|第)\s*(\d+)\s*/\s*(\d+)(?:\s*批)?")
_FAILURE_KIND_PATTERN = re.compile(r"failure_kind=([^;]+)")
_FAILURE_STAGE_PATTERN = re.compile(r"stage=([^;]+)")
_TASK_ID_PATTERN = re.compile(r"task_id=(\d+)")
_TASK_TYPE_PATTERN = re.compile(r"task_type=([^;]+)")


def _extract_int(pattern: re.Pattern[str], message: str) -> int | None:
    match = pattern.search(message)
    if not match:
        return None
    return int(match.group(1))


def parse_sync_job_progress(message: str | None) -> dict[str, Any] | None:
    if not message:
        return None

    progress: dict[str, Any] = {}
    if "自动补齐 BOM" in message:
        progress["kind"] = "auto_bom_backfill"
    elif "BOM 补数队列" in message:
        progress["kind"] = "bom_backfill_queue"
    elif "销售计划同步" in message:
        progress["kind"] = "sales_plan"
    elif "研究所数据同步" in message:
        progress["kind"] = "research"
    elif "生产订单同步" in message:
        progress["kind"] = "production_order"
    elif "快照对账" in message:
        progress["kind"] = "schedule_snapshot_reconcile"
    elif "零件周期基准重建完成" in message:
        progress["kind"] = "part_cycle_baseline_rebuild"
    elif "BOM 同步" in message:
        progress["kind"] = "bom"
    else:
        progress["kind"] = "generic"

    batch_match = _BATCH_PATTERN.search(message)
    if batch_match:
        progress["batch_current"] = int(batch_match.group(1))
        progress["batch_total"] = int(batch_match.group(2))

    for key, pattern in _NUMBER_PATTERNS.items():
        value = _extract_int(pattern, message)
        if value is not None:
            progress[key] = value

    failure_kind_match = _FAILURE_KIND_PATTERN.search(message)
    if failure_kind_match:
        progress["failure_kind"] = failure_kind_match.group(1).strip()

    failure_stage_match = _FAILURE_STAGE_PATTERN.search(message)
    if failure_stage_match:
        progress["failure_stage"] = failure_stage_match.group(1).strip()

    task_id = _extract_int(_TASK_ID_PATTERN, message)
    if task_id is not None:
        progress["task_id"] = task_id

    task_type_match = _TASK_TYPE_PATTERN.search(message)
    if task_type_match:
        progress["task_type"] = task_type_match.group(1).strip()

    progress["summary"] = message
    return progress if len(progress) > 1 else None


def serialize_sync_log(log: SyncJobLog) -> dict[str, Any]:
    return {
        "id": log.id,
        "job_type": log.job_type,
        "source_system": log.source_system,
        "start_time": log.start_time.isoformat() if log.start_time else None,
        "end_time": log.end_time.isoformat() if log.end_time else None,
        "status": log.status,
        "success_count": log.success_count,
        "fail_count": log.fail_count,
        "message": log.message,
        "created_at": log.created_at.isoformat() if log.created_at else None,
        "progress": parse_sync_job_progress(log.message),
    }


class SyncJobObservabilityService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_summary(self) -> dict[str, Any]:
        queue_repo = BomBackfillQueueRepo(self.session)
        queue_summary = await queue_repo.get_observability_summary(limit=5)
        summary_counts = await self._load_summary_counts()
        latest_jobs = await self._load_latest_jobs()
        oldest_pending_at = queue_summary.get("oldest_pending_at")

        return {
            "snapshot_total": summary_counts["snapshot_total"],
            "missing_bom_snapshot_count": summary_counts["missing_bom_snapshot_count"],
            "open_missing_bom_issue_count": summary_counts["open_missing_bom_issue_count"],
            "distinct_machine_bom_count": summary_counts["distinct_machine_bom_count"],
            "running_job_count": summary_counts["running_job_count"],
            "bom_backfill_queue": {
                "pending": queue_summary["status_counts"].get("pending", 0),
                "processing": queue_summary["status_counts"].get("processing", 0),
                "retry_wait": queue_summary["status_counts"].get("retry_wait", 0),
                "success": queue_summary["status_counts"].get("success", 0),
                "failed": queue_summary["status_counts"].get("failed", 0),
                "paused": queue_summary["status_counts"].get("paused", 0),
                "retry_wait_due": queue_summary["retry_wait_due"],
                "failure_kind_counts": queue_summary["failure_kind_counts"],
                "oldest_pending_age_minutes": (
                    int((utc_now() - oldest_pending_at).total_seconds() // 60) if oldest_pending_at else None
                ),
                "latest_failed_items": list(queue_summary["latest_failed_items"]),
            },
            "latest_sales_plan_job": latest_jobs["latest_sales_plan_job"],
            "latest_research_job": latest_jobs["latest_research_job"],
            "latest_auto_bom_job": latest_jobs["latest_auto_bom_job"],
        }

    async def _load_summary_counts(self) -> dict[str, int]:
        snapshot_counts = (
            select(
                func.count().label("snapshot_total"),
                func.sum(case((OrderScheduleSnapshot.schedule_status == "missing_bom", 1), else_=0)).label(
                    "missing_bom_snapshot_count"
                ),
            )
            .select_from(OrderScheduleSnapshot)
            .subquery()
        )
        issue_counts = (
            select(
                func.count().label("open_missing_bom_issue_count"),
            )
            .select_from(DataIssueRecord)
            .where(
                DataIssueRecord.issue_type == "BOM缺失",
                DataIssueRecord.status == "open",
            )
            .subquery()
        )
        bom_counts = (
            select(
                func.count(func.distinct(BomRelationSrc.machine_material_no)).label("distinct_machine_bom_count"),
            )
            .select_from(BomRelationSrc)
            .subquery()
        )
        job_counts = (
            select(
                func.count().label("running_job_count"),
            )
            .select_from(SyncJobLog)
            .where(SyncJobLog.status == "running")
            .subquery()
        )
        stmt = (
            select(
                snapshot_counts.c.snapshot_total,
                snapshot_counts.c.missing_bom_snapshot_count,
                issue_counts.c.open_missing_bom_issue_count,
                bom_counts.c.distinct_machine_bom_count,
                job_counts.c.running_job_count,
            )
            .select_from(snapshot_counts)
            .join(issue_counts, true())
            .join(bom_counts, true())
            .join(job_counts, true())
        )
        row = (await self.session.execute(stmt)).one()
        return {
            "snapshot_total": int(row.snapshot_total or 0),
            "missing_bom_snapshot_count": int(row.missing_bom_snapshot_count or 0),
            "open_missing_bom_issue_count": int(row.open_missing_bom_issue_count or 0),
            "distinct_machine_bom_count": int(row.distinct_machine_bom_count or 0),
            "running_job_count": int(row.running_job_count or 0),
        }

    async def _get_latest_job(self, *, job_type: str) -> dict[str, Any] | None:
        stmt = select(SyncJobLog).where(SyncJobLog.job_type == job_type).order_by(desc(SyncJobLog.id)).limit(1)
        entity = (await self.session.execute(stmt)).scalar_one_or_none()
        return serialize_sync_log(entity) if entity else None

    async def _get_latest_auto_bom_job(self) -> dict[str, Any] | None:
        stmt = (
            select(SyncJobLog)
            .where(
                SyncJobLog.job_type == "bom",
                SyncJobLog.message.is_not(None),
                (SyncJobLog.message.contains("自动补齐 BOM") | SyncJobLog.message.contains("BOM 补数队列")),
            )
            .order_by(desc(SyncJobLog.id))
            .limit(1)
        )
        entity = (await self.session.execute(stmt)).scalar_one_or_none()
        if entity is None:
            return await self._get_latest_job(job_type="bom")
        return serialize_sync_log(entity)

    async def _load_latest_jobs(self) -> dict[str, dict[str, Any] | None]:
        sales_plan_id = (
            select(SyncJobLog.id)
            .where(SyncJobLog.job_type == "sales_plan")
            .order_by(desc(SyncJobLog.id))
            .limit(1)
            .scalar_subquery()
        )
        research_id = (
            select(SyncJobLog.id)
            .where(SyncJobLog.job_type == "research")
            .order_by(desc(SyncJobLog.id))
            .limit(1)
            .scalar_subquery()
        )
        latest_bom_id = (
            select(SyncJobLog.id)
            .where(SyncJobLog.job_type == "bom")
            .order_by(desc(SyncJobLog.id))
            .limit(1)
            .scalar_subquery()
        )
        latest_auto_bom_id = (
            select(SyncJobLog.id)
            .where(
                SyncJobLog.job_type == "bom",
                SyncJobLog.message.is_not(None),
                (SyncJobLog.message.contains("自动补齐 BOM") | SyncJobLog.message.contains("BOM 补数队列")),
            )
            .order_by(desc(SyncJobLog.id))
            .limit(1)
            .scalar_subquery()
        )

        latest_job_ids = union_all(
            select(
                literal("latest_sales_plan_job").label("job_key"),
                sales_plan_id.label("log_id"),
            ),
            select(
                literal("latest_research_job").label("job_key"),
                research_id.label("log_id"),
            ),
            select(
                literal("latest_auto_bom_job").label("job_key"),
                func.coalesce(latest_auto_bom_id, latest_bom_id).label("log_id"),
            ),
        ).subquery()

        stmt = select(latest_job_ids.c.job_key, SyncJobLog).join(
            SyncJobLog, SyncJobLog.id == latest_job_ids.c.log_id, isouter=True
        )
        rows = (await self.session.execute(stmt)).all()
        jobs: dict[str, dict[str, Any] | None] = {
            "latest_sales_plan_job": None,
            "latest_research_job": None,
            "latest_auto_bom_job": None,
        }
        for job_key, entity in rows:
            jobs[str(job_key)] = serialize_sync_log(entity) if entity else None
        return jobs
