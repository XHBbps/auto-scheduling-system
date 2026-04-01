import pytest
from datetime import datetime
from decimal import Decimal

from app.models.sales_plan import SalesPlanOrderLineSrc
from app.models.machine_cycle_history import MachineCycleHistorySrc
from app.sync.drawing_status_sync_service import DrawingStatusSyncService


@pytest.mark.asyncio
async def test_backfill_by_detail_id(db_session):
    # Create a sales order without drawing status
    order = SalesPlanOrderLineSrc(
        sap_code="SAP001", sap_line_no="10",
        contract_no="HT001", detail_id="DT001",
        material_no="MAT001", drawing_released=False,
    )
    db_session.add(order)

    # Create a research record with drawing date
    research = MachineCycleHistorySrc(
        detail_id="DT001", machine_model="MC1-80",
        order_qty=Decimal("1"),
        drawing_release_date=datetime(2026, 3, 15),
    )
    db_session.add(research)
    await db_session.commit()

    service = DrawingStatusSyncService(db_session)
    count = await service.refresh_all()
    await db_session.commit()

    await db_session.refresh(order)
    assert order.drawing_released is True
    assert order.drawing_release_date == datetime(2026, 3, 15)
    assert count == 1


@pytest.mark.asyncio
async def test_no_match_no_update(db_session):
    order = SalesPlanOrderLineSrc(
        sap_code="SAP001", sap_line_no="10",
        contract_no="HT001", detail_id="DT_NO_MATCH",
        material_no="MAT001", drawing_released=False,
    )
    db_session.add(order)
    await db_session.commit()

    service = DrawingStatusSyncService(db_session)
    count = await service.refresh_all()
    await db_session.commit()

    await db_session.refresh(order)
    assert order.drawing_released is False
    assert count == 0


@pytest.mark.asyncio
async def test_refresh_all_batches_detail_and_order_material_lookups(db_session, monkeypatch):
    db_session.add_all([
        SalesPlanOrderLineSrc(
            sap_code="SAP101",
            sap_line_no="10",
            contract_no="HT101",
            detail_id="DT101",
            material_no="MAT101",
            drawing_released=False,
        ),
        SalesPlanOrderLineSrc(
            sap_code="SAP102",
            sap_line_no="10",
            contract_no="HT102",
            detail_id=None,
            order_no="SO102",
            material_no="MAT102",
            drawing_released=False,
        ),
        SalesPlanOrderLineSrc(
            sap_code="SAP103",
            sap_line_no="10",
            contract_no="HT103",
            detail_id=None,
            order_no="SO103",
            material_no="MAT103",
            drawing_released=False,
        ),
        MachineCycleHistorySrc(
            detail_id="DT101",
            machine_model="MC1-80",
            order_qty=Decimal("1"),
            drawing_release_date=datetime(2026, 3, 15),
        ),
        MachineCycleHistorySrc(
            detail_id="DT102",
            machine_model="MC1-80",
            order_qty=Decimal("1"),
            order_no="SO102",
            machine_material_no="MAT102",
            drawing_release_date=datetime(2026, 3, 16),
        ),
        MachineCycleHistorySrc(
            detail_id="DT103",
            machine_model="MC1-80",
            order_qty=Decimal("1"),
            order_no="SO103",
            machine_material_no="MAT103",
            drawing_release_date=datetime(2026, 3, 17),
        ),
    ])
    await db_session.commit()

    original_load_detail = DrawingStatusSyncService._load_research_by_detail_ids
    original_load_pairs = DrawingStatusSyncService._load_research_by_order_material_pairs
    detail_calls: list[list[str]] = []
    pair_calls: list[list[tuple[str, str]]] = []

    async def tracking_load_detail(self, detail_ids):
        detail_calls.append(list(detail_ids))
        return await original_load_detail(self, detail_ids)

    async def tracking_load_pairs(self, pairs):
        pair_calls.append(list(pairs))
        return await original_load_pairs(self, pairs)

    monkeypatch.setattr(DrawingStatusSyncService, "_load_research_by_detail_ids", tracking_load_detail)
    monkeypatch.setattr(DrawingStatusSyncService, "_load_research_by_order_material_pairs", tracking_load_pairs)

    service = DrawingStatusSyncService(db_session)
    updated_ids = await service.refresh_all_with_ids()
    await db_session.commit()

    assert len(updated_ids) == 3
    assert detail_calls == [["DT101"]]
    assert pair_calls == [[("SO102", "MAT102"), ("SO103", "MAT103")]]


@pytest.mark.asyncio
async def test_refresh_all_prefers_latest_drawing_release_date_for_order_material_match(db_session):
    order = SalesPlanOrderLineSrc(
        sap_code="SAP201",
        sap_line_no="10",
        contract_no="HT201",
        detail_id=None,
        order_no="SO201",
        material_no="MAT201",
        drawing_released=False,
    )
    db_session.add(order)
    db_session.add_all([
        MachineCycleHistorySrc(
            detail_id="DT201A",
            machine_model="MC1-80",
            order_qty=Decimal("1"),
            order_no="SO201",
            machine_material_no="MAT201",
            drawing_release_date=datetime(2026, 3, 10),
        ),
        MachineCycleHistorySrc(
            detail_id="DT201B",
            machine_model="MC1-80",
            order_qty=Decimal("1"),
            order_no="SO201",
            machine_material_no="MAT201",
            drawing_release_date=datetime(2026, 3, 18),
        ),
    ])
    await db_session.commit()

    service = DrawingStatusSyncService(db_session)
    count = await service.refresh_all()
    await db_session.commit()

    await db_session.refresh(order)
    assert count == 1
    assert order.drawing_released is True
    assert order.drawing_release_date == datetime(2026, 3, 18)
