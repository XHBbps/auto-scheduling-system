from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.background_task_dispatch_service import BackgroundTaskDispatchService


class ManualSyncTaskRunner:
    """Legacy compatibility shim kept to avoid broad import churn."""

    async def shutdown(self) -> None:  # pragma: no cover - compatibility shim
        return None


class ManualSyncTaskService:
    def __init__(self):
        pass

    async def enqueue_sales_plan(
        self,
        session: AsyncSession,
        *,
        operator_name: str | None,
        message: str,
        filter_payload: dict[str, Any] | None,
    ) -> tuple[int | None, str, bool]:
        _, job, created = await BackgroundTaskDispatchService(session).enqueue(
            task_type="sales_plan_sync",
            source="manual_api",
            reason="manual_sales_plan_sync",
            payload={"filter_payload": filter_payload},
            dedupe_key="sync_job:sales_plan:guandata",
            sync_job_kwargs={
                "job_type": "sales_plan",
                "source_system": "guandata",
                "message": message,
                "operator_name": operator_name,
            },
        )
        await session.commit()
        return (job.id if job is not None else None), (job.status if job is not None else "queued"), created

    async def enqueue_bom(
        self,
        session: AsyncSession,
        *,
        operator_name: str | None,
        message: str,
        items: list[tuple[str, str]],
    ) -> tuple[int | None, str, bool]:
        _, job, created = await BackgroundTaskDispatchService(session).enqueue(
            task_type="bom_sync",
            source="manual_api",
            reason="manual_bom_sync",
            payload={"items": items},
            dedupe_key="sync_job:bom:sap",
            sync_job_kwargs={
                "job_type": "bom",
                "source_system": "sap",
                "message": message,
                "operator_name": operator_name,
            },
        )
        await session.commit()
        return (job.id if job is not None else None), (job.status if job is not None else "queued"), created

    async def enqueue_production_orders(
        self,
        session: AsyncSession,
        *,
        operator_name: str | None,
        message: str,
    ) -> tuple[int | None, str, bool]:
        _, job, created = await BackgroundTaskDispatchService(session).enqueue(
            task_type="production_order_sync",
            source="manual_api",
            reason="manual_production_order_sync",
            dedupe_key="sync_job:production_order:feishu",
            sync_job_kwargs={
                "job_type": "production_order",
                "source_system": "feishu",
                "message": message,
                "operator_name": operator_name,
            },
        )
        await session.commit()
        return (job.id if job is not None else None), (job.status if job is not None else "queued"), created

    async def enqueue_part_cycle_baseline_rebuild(
        self,
        session: AsyncSession,
        *,
        operator_name: str | None,
        message: str,
        source: str = "manual_api",
        reason: str = "manual_part_cycle_baseline_rebuild",
        payload: dict[str, Any] | None = None,
    ) -> tuple[int | None, str, bool]:
        task, job, created = await BackgroundTaskDispatchService(session).enqueue(
            task_type="part_cycle_baseline_rebuild",
            source=source,
            reason=reason,
            payload=payload,
            dedupe_key="baseline_rebuild:part_cycle",
            sync_job_kwargs={
                "job_type": "part_cycle_baseline",
                "source_system": "system",
                "message": message,
                "operator_name": operator_name,
            } if source == "manual_api" else None,
        )
        await session.commit()
        identifier = job.id if job is not None else task.id
        status = job.status if job is not None else task.status
        return identifier, status, created

    async def enqueue_research(
        self,
        session: AsyncSession,
        *,
        operator_name: str | None,
        message: str,
        order_no_filter: str | None,
    ) -> tuple[int | None, str, bool]:
        _, job, created = await BackgroundTaskDispatchService(session).enqueue(
            task_type="research_sync",
            source="manual_api",
            reason="manual_research_sync",
            payload={"order_no_filter": order_no_filter},
            dedupe_key="sync_job:research:feishu",
            sync_job_kwargs={
                "job_type": "research",
                "source_system": "feishu",
                "message": message,
                "operator_name": operator_name,
            },
        )
        await session.commit()
        return (job.id if job is not None else None), (job.status if job is not None else "queued"), created
