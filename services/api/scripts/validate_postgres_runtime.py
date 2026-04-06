from __future__ import annotations

import asyncio
from uuid import uuid4

from sqlalchemy import delete, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.common.datetime_utils import utc_now
from app.config import settings
from app.models.background_task import BackgroundTask
from app.models.order_schedule_snapshot import OrderScheduleSnapshot
from app.models.sales_plan import SalesPlanOrderLineSrc
from app.repository.background_task_repo import BackgroundTaskRepo

ADVISORY_LOCK_KEY = 20260326_14
VALIDATION_SOURCE = "pg_runtime_validation"
REQUIRED_TRIGRAM_INDEXES = {
    "idx_oss_contract_no_trgm",
    "idx_oss_customer_name_trgm",
    "idx_oss_product_model_trgm",
    "idx_oss_order_no_trgm",
    "idx_psr_part_material_no_trgm",
    "idx_psr_key_part_name_trgm",
    "idx_psr_key_part_material_no_trgm",
    "idx_splo_contract_no_trgm",
    "idx_splo_customer_name_trgm",
    "idx_splo_product_series_trgm",
    "idx_splo_product_model_trgm",
    "idx_splo_material_no_trgm",
    "idx_splo_business_group_trgm",
    "idx_splo_sales_branch_company_trgm",
    "idx_splo_sales_sub_branch_trgm",
    "idx_bom_machine_material_no_trgm",
    "idx_bom_material_no_trgm",
    "idx_bom_component_no_trgm",
    "idx_bom_part_type_trgm",
    "idx_prod_order_no_trgm",
    "idx_prod_material_no_trgm",
    "idx_prod_machine_model_trgm",
    "idx_mch_machine_model_trgm",
    "idx_mch_product_series_trgm",
    "idx_mch_contract_no_trgm",
    "idx_mch_order_no_trgm",
}


async def _assert_pg_trgm_installed(session: AsyncSession) -> None:
    installed = await session.execute(text("SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'pg_trgm')"))
    assert installed.scalar_one() is True, "pg_trgm extension is not installed"


async def _assert_trigram_indexes(session: AsyncSession) -> None:
    rows = await session.execute(
        text(
            """
            SELECT indexname
            FROM pg_indexes
            WHERE schemaname = current_schema()
              AND indexname = ANY(:index_names)
            """
        ),
        {"index_names": list(REQUIRED_TRIGRAM_INDEXES)},
    )
    existing = {row[0] for row in rows.all()}
    missing = REQUIRED_TRIGRAM_INDEXES - existing
    assert not missing, f"missing trigram indexes: {sorted(missing)}"


async def _validate_jsonb_roundtrip(session_factory: async_sessionmaker[AsyncSession]) -> None:
    async with session_factory() as session:
        task = BackgroundTask(
            task_type="pg_jsonb_validation",
            status="pending",
            source=VALIDATION_SOURCE,
            reason="jsonb_roundtrip",
            payload={"nested": {"plant": "1000"}, "rows": [1, 2, 3]},
            available_at=utc_now(),
            max_attempts=1,
        )
        session.add(task)
        await session.commit()
        task_id = task.id

    try:
        async with session_factory() as session:
            stored = await session.get(BackgroundTask, task_id)
            assert stored is not None
            assert stored.payload == {"nested": {"plant": "1000"}, "rows": [1, 2, 3]}
    finally:
        async with session_factory() as session:
            await session.execute(delete(BackgroundTask).where(BackgroundTask.source == VALIDATION_SOURCE))
            await session.commit()


async def _validate_skip_locked(session_factory: async_sessionmaker[AsyncSession]) -> None:
    async with session_factory() as session:
        now = utc_now()
        session.add_all(
            [
                BackgroundTask(
                    task_type="pg_lock_validation",
                    status="pending",
                    source=VALIDATION_SOURCE,
                    reason="skip_locked_a",
                    available_at=now,
                    max_attempts=1,
                ),
                BackgroundTask(
                    task_type="pg_lock_validation",
                    status="pending",
                    source=VALIDATION_SOURCE,
                    reason="skip_locked_b",
                    available_at=now,
                    max_attempts=1,
                ),
            ]
        )
        await session.commit()

    try:
        async with session_factory() as session_1, session_factory() as session_2:
            repo_1 = BackgroundTaskRepo(session_1)
            repo_2 = BackgroundTaskRepo(session_2)

            async with session_1.begin():
                claimed_first = await repo_1.claim_available(worker_id="validator-1", limit=1)
                assert len(claimed_first) == 1
                first_id = claimed_first[0].id

                async with session_2.begin():
                    claimed_second = await repo_2.claim_available(worker_id="validator-2", limit=2)
                    second_ids = {task.id for task in claimed_second}
                    assert first_id not in second_ids, "skip locked did not exclude locked task"
                    assert len(claimed_second) == 1, "expected second session to claim only remaining task"
    finally:
        async with session_factory() as session:
            await session.execute(delete(BackgroundTask).where(BackgroundTask.source == VALIDATION_SOURCE))
            await session.commit()


async def _validate_advisory_lock(engine) -> None:
    async with engine.connect() as conn_1, engine.connect() as conn_2, conn_1.begin():
        await conn_1.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": ADVISORY_LOCK_KEY})
        async with conn_2.begin():
            acquired = await conn_2.execute(
                text("SELECT pg_try_advisory_xact_lock(:key)"),
                {"key": ADVISORY_LOCK_KEY},
            )
            assert acquired.scalar_one() is False, "advisory lock should be held by first transaction"


async def _validate_search_plan(session_factory: async_sessionmaker[AsyncSession]) -> None:
    marker = f"PG-TRGM-{uuid4().hex[:8].upper()}"
    order_line_ids = [9900001, 9900002]
    sales_keys = [(f"SAP-{marker}-1", "10"), (f"SAP-{marker}-2", "20")]

    async with session_factory() as session:
        session.add_all(
            [
                OrderScheduleSnapshot(
                    order_line_id=order_line_ids[0],
                    contract_no=f"HT-{marker}-A",
                    customer_name="PG Validation Customer",
                    product_model="MC-PG-1",
                    plant="1000",
                    order_no=f"SO-{marker}-A",
                    schedule_status="scheduled",
                ),
                OrderScheduleSnapshot(
                    order_line_id=order_line_ids[1],
                    contract_no=f"HT-{marker}-B",
                    customer_name="PG Validation Customer",
                    product_model="MC-PG-2",
                    plant="1000",
                    order_no=f"SO-{marker}-B",
                    schedule_status="scheduled",
                ),
                SalesPlanOrderLineSrc(
                    sap_code=sales_keys[0][0],
                    sap_line_no=sales_keys[0][1],
                    contract_no=f"HT-{marker}-A",
                    customer_name="PG Validation Customer",
                    product_model="MC-PG-1",
                    product_series="MC",
                    material_no=f"MAT-{marker}-A",
                ),
                SalesPlanOrderLineSrc(
                    sap_code=sales_keys[1][0],
                    sap_line_no=sales_keys[1][1],
                    contract_no=f"HT-{marker}-B",
                    customer_name="PG Validation Customer",
                    product_model="MC-PG-2",
                    product_series="MC",
                    material_no=f"MAT-{marker}-B",
                ),
            ]
        )
        await session.commit()

    try:
        async with session_factory() as session:
            await session.execute(text("SET enable_seqscan = off"))
            explain_rows = await session.execute(
                text(
                    """
                    EXPLAIN
                    SELECT order_line_id
                    FROM order_schedule_snapshot
                    WHERE contract_no ILIKE :keyword
                    ORDER BY confirmed_delivery_date ASC NULLS LAST, order_line_id DESC
                    LIMIT 20
                    """
                ),
                {"keyword": f"%{marker}%"},
            )
            plan_text = "\n".join(row[0] for row in explain_rows.all())
            assert "idx_oss_contract_no_trgm" in plan_text or "Bitmap Index Scan" in plan_text, plan_text
    finally:
        async with session_factory() as session:
            await session.execute(
                delete(OrderScheduleSnapshot).where(OrderScheduleSnapshot.order_line_id.in_(order_line_ids))
            )
            await session.execute(
                delete(SalesPlanOrderLineSrc).where(
                    SalesPlanOrderLineSrc.sap_code.in_([item[0] for item in sales_keys])
                )
            )
            await session.commit()


async def main() -> None:
    engine = create_async_engine(settings.database_url, future=True)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    try:
        if engine.url.get_backend_name() != "postgresql":
            raise RuntimeError(f"Current DATABASE_URL is not PostgreSQL: {settings.database_url}")

        async with session_factory() as session:
            await _assert_pg_trgm_installed(session)
            await _assert_trigram_indexes(session)

        await _validate_jsonb_roundtrip(session_factory)
        await _validate_skip_locked(session_factory)
        await _validate_advisory_lock(engine)
        await _validate_search_plan(session_factory)
        print("PostgreSQL runtime validation passed.")
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
