import pytest
from decimal import Decimal
from datetime import date, datetime, timedelta
from sqlalchemy import func, select

from app.models.bom_relation import BomRelationSrc
from app.models.data_issue import DataIssueRecord
from app.models.machine_cycle_baseline import MachineCycleBaseline
from app.models.machine_schedule_result import MachineScheduleResult
from app.models.order_schedule_snapshot import OrderScheduleSnapshot
from app.models.part_schedule_result import PartScheduleResult
from app.models.sales_plan import SalesPlanOrderLineSrc
from app.services.schedule_query_service import ScheduleQueryService
from app.services.schedule_snapshot_refresh_service import ScheduleSnapshotRefreshService


@pytest.mark.asyncio
async def test_list_schedules_empty(app_client):
    resp = await app_client.get("/api/schedules")
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 0
    assert body["data"]["total"] == 0


@pytest.mark.asyncio
async def test_list_schedules_with_data(app_client, db_session):
    db_session.add(MachineScheduleResult(
        order_line_id=1, contract_no="HT001", product_model="MC1-80",
        schedule_status="scheduled", planned_start_date=datetime(2026, 4, 1),
        planned_end_date=datetime(2026, 6, 30),
        machine_cycle_days=Decimal("60"), machine_assembly_days=Decimal("3"),
    ))
    await db_session.commit()

    resp = await app_client.get("/api/schedules")
    body = resp.json()
    assert body["data"]["total"] == 1
    assert body["data"]["items"][0]["contract_no"] == "HT001"


@pytest.mark.asyncio
async def test_list_schedules_and_detail_include_extended_sales_fields(app_client, db_session):
    db_session.add(OrderScheduleSnapshot(
        order_line_id=88,
        contract_no="HT088",
        customer_name="客户88",
        product_series="MC",
        product_model="MC-880",
        product_name="高性能冲床",
        material_no="MAT-088",
        quantity=Decimal("2"),
        order_type="3",
        line_total_amount=Decimal("880000"),
        order_date=datetime(2026, 3, 1, 0, 0, 0),
        business_group="装备事业群",
        custom_no="DZ-088",
        sales_person_name="张三",
        sales_branch_company="华东分公司",
        sales_sub_branch="苏州支公司",
        order_no="SO-088",
        sap_code="SAP-088",
        sap_line_no="000010",
        confirmed_delivery_date=datetime(2026, 4, 20, 0, 0, 0),
        drawing_released=True,
        drawing_release_date=datetime(2026, 3, 5, 0, 0, 0),
        custom_requirement="需要自动上料",
        review_comment="优先排产",
        schedule_status="scheduled",
        warning_level="normal",
        machine_cycle_days=Decimal("60"),
        machine_assembly_days=Decimal("3"),
    ))
    await db_session.commit()

    list_resp = await app_client.get("/api/schedules")
    list_body = list_resp.json()
    item = list_body["data"]["items"][0]
    assert item["product_name"] == "高性能冲床"
    assert item["order_type"] == "3"
    assert item["line_total_amount"] == "880000.0000"
    assert item["business_group"] == "装备事业群"
    assert item["custom_no"] == "DZ-088"
    assert item["sales_person_name"] == "张三"
    assert item["sales_branch_company"] == "华东分公司"
    assert item["sales_sub_branch"] == "苏州支公司"
    assert item["sap_code"] == "SAP-088"
    assert item["sap_line_no"] == "000010"
    assert item["custom_requirement"] == "需要自动上料"
    assert item["review_comment"] == "优先排产"

    detail_resp = await app_client.get("/api/schedules/88")
    detail_body = detail_resp.json()
    machine_schedule = detail_body["data"]["machine_schedule"]
    assert machine_schedule["line_total_amount"] == "880000.0000"
    assert machine_schedule["order_date"] == "2026-03-01T00:00:00"
    assert machine_schedule["custom_requirement"] == "需要自动上料"
    assert machine_schedule["review_comment"] == "优先排产"


@pytest.mark.asyncio
async def test_list_schedules_filter(app_client, db_session):
    db_session.add(MachineScheduleResult(
        order_line_id=10, contract_no="HT010", product_model="MC1-80",
        schedule_status="scheduled",
        machine_cycle_days=Decimal("60"), machine_assembly_days=Decimal("3"),
    ))
    db_session.add(MachineScheduleResult(
        order_line_id=11, contract_no="HT011", product_model="MC2-100",
        schedule_status="pending_drawing",
        machine_cycle_days=Decimal("90"), machine_assembly_days=Decimal("3"),
    ))
    await db_session.commit()

    resp = await app_client.get("/api/schedules?schedule_status=scheduled")
    body = resp.json()
    assert body["data"]["total"] == 1
    assert body["data"]["items"][0]["contract_no"] == "HT010"


@pytest.mark.asyncio
async def test_list_schedules_filter_by_confirmed_delivery_date_range(app_client, db_session):
    db_session.add(MachineScheduleResult(
        order_line_id=20, contract_no="HT020", product_model="MC1-80",
        schedule_status="scheduled",
        confirmed_delivery_date=datetime(2025, 3, 15, 0, 0, 0),
        machine_cycle_days=Decimal("60"), machine_assembly_days=Decimal("3"),
    ))
    db_session.add(MachineScheduleResult(
        order_line_id=21, contract_no="HT021", product_model="MC2-100",
        schedule_status="scheduled",
        confirmed_delivery_date=datetime(2025, 4, 2, 0, 0, 0),
        machine_cycle_days=Decimal("90"), machine_assembly_days=Decimal("3"),
    ))
    await db_session.commit()

    resp = await app_client.get("/api/schedules?date_from=2025-03-01&date_to=2025-03-31")
    body = resp.json()
    assert body["code"] == 0
    assert body["data"]["total"] == 1
    assert body["data"]["items"][0]["contract_no"] == "HT020"


@pytest.mark.asyncio
async def test_list_schedules_supports_sorting_snapshot_text_fields(app_client, db_session):
    db_session.add_all([
        OrderScheduleSnapshot(
            order_line_id=301,
            contract_no="HT301",
            product_model="MC-301",
            material_no="MAT-301",
            quantity=Decimal("1"),
            order_no="SO-301",
            confirmed_delivery_date=datetime(2026, 4, 10, 0, 0, 0),
            drawing_released=True,
            schedule_status="scheduled",
            warning_level="normal",
            custom_requirement="A类定制",
            review_comment="A评审",
        ),
        OrderScheduleSnapshot(
            order_line_id=302,
            contract_no="HT302",
            product_model="MC-302",
            material_no="MAT-302",
            quantity=Decimal("1"),
            order_no="SO-302",
            confirmed_delivery_date=datetime(2026, 4, 11, 0, 0, 0),
            drawing_released=True,
            schedule_status="scheduled",
            warning_level="normal",
            custom_requirement="B类定制",
            review_comment="B评审",
        ),
    ])
    await db_session.commit()

    resp = await app_client.get(
        "/api/schedules",
        params={"sort_field": "custom_requirement", "sort_order": "asc"},
    )
    body = resp.json()
    assert body["code"] == 0
    assert [item["contract_no"] for item in body["data"]["items"]] == ["HT301", "HT302"]

    resp = await app_client.get(
        "/api/schedules",
        params={"sort_field": "review_comment", "sort_order": "desc"},
    )
    body = resp.json()
    assert body["code"] == 0
    assert [item["contract_no"] for item in body["data"]["items"]] == ["HT302", "HT301"]


@pytest.mark.asyncio
async def test_schedule_detail(app_client, db_session):
    db_session.add(MachineScheduleResult(
        order_line_id=99, contract_no="HT002", product_model="MC1-80",
        schedule_status="scheduled",
        machine_cycle_days=Decimal("60"), machine_assembly_days=Decimal("3"),
    ))
    db_session.add(PartScheduleResult(
        order_line_id=99, assembly_name="机身", production_sequence=1,
        parent_material_no="ASM_BODY", parent_name="机身", node_level=1,
        bom_path="机身(ASM_BODY) / 机身体焊接件(P001)",
        bom_path_key="root:ASM_BODY>1",
        part_material_no="P001", part_name="机身体焊接件", is_key_part=True,
        part_cycle_days=Decimal("15"), part_cycle_is_default=False, part_cycle_match_rule="exact_material",
        key_part_material_no="P001", key_part_cycle_days=Decimal("15"),
    ))
    await db_session.commit()

    resp = await app_client.get("/api/schedules/99")
    body = resp.json()
    assert body["code"] == 0
    assert body["data"]["machine_schedule"]["contract_no"] == "HT002"
    assert len(body["data"]["part_schedules"]) == 1
    assert body["data"]["part_schedules"][0]["part_material_no"] == "P001"
    assert body["data"]["part_schedules"][0]["is_key_part"] is True
    assert body["data"]["part_schedules"][0]["part_cycle_days"] == "15.0000"
    assert body["data"]["part_schedules"][0]["parent_material_no"] == "ASM_BODY"
    assert body["data"]["part_schedules"][0]["bom_path"] == "机身(ASM_BODY) / 机身体焊接件(P001)"


@pytest.mark.asyncio
async def test_schedule_detail_normalizes_legacy_issue_text(app_client, db_session):
    db_session.add(MachineScheduleResult(
        order_line_id=199, contract_no="HT199", product_model="MC1-80",
        schedule_status="scheduled",
        machine_cycle_days=Decimal("60"), machine_assembly_days=Decimal("3"),
    ))
    db_session.add(DataIssueRecord(
        issue_type="零件周期基准缺失",
        issue_level="medium",
        source_system="scheduler",
        biz_key="199",
        order_line_id=199,
        issue_title="零件周期基准缺失，已按默认值排产",
        issue_detail="订单行 199 缺少零件周期基准?涉及物料?P001?P002?已按默认值排产?",
        status="open",
    ))
    await db_session.commit()

    resp = await app_client.get("/api/schedules/199")
    body = resp.json()

    assert body["code"] == 0
    assert body["data"]["issues"][0]["issue_detail"] == "订单行 199 缺少零件周期基准；涉及物料：P001、P002；已按默认值排产。"


@pytest.mark.asyncio
async def test_schedule_detail_not_found(app_client):
    resp = await app_client.get("/api/schedules/9999")
    body = resp.json()
    assert body["code"] == 4002


@pytest.mark.asyncio
async def test_list_schedules_includes_dynamic_unscheduled_statuses(app_client, db_session):
    pending_delivery = SalesPlanOrderLineSrc(
        contract_no="HT-DEL",
        customer_name="Pending Delivery",
        product_series="MCX",
        product_model="MCX-0",
        material_no="MAT-DEL",
        quantity=Decimal("1"),
        order_no="SO-DEL",
        confirmed_delivery_date=None,
        drawing_released=True,
    )
    pending_drawing = SalesPlanOrderLineSrc(
        contract_no="HT-PD",
        customer_name="Pending Drawing",
        product_series="MCX",
        product_model="MCX-1",
        material_no="MAT-PD",
        quantity=Decimal("1"),
        order_no="SO-PD",
        confirmed_delivery_date=datetime(2026, 6, 30),
        drawing_released=False,
    )
    missing_bom = SalesPlanOrderLineSrc(
        contract_no="HT-BOM",
        customer_name="Missing Bom",
        product_series="MCX",
        product_model="MCX-2",
        material_no="MAT-BOM",
        quantity=Decimal("1"),
        order_no="SO-BOM",
        confirmed_delivery_date=datetime(2026, 6, 30),
        drawing_released=True,
        drawing_release_date=datetime(2026, 3, 1),
    )
    schedulable = SalesPlanOrderLineSrc(
        contract_no="HT-SCH",
        customer_name="Schedulable",
        product_series="MCY",
        product_model="MCY-3",
        material_no="MAT-SCH",
        quantity=Decimal("1"),
        order_no="SO-SCH",
        confirmed_delivery_date=datetime(2025, 1, 15),
        drawing_released=True,
        drawing_release_date=datetime(2024, 12, 1),
    )
    db_session.add_all([pending_delivery, pending_drawing, missing_bom, schedulable])
    await db_session.flush()

    db_session.add(MachineCycleBaseline(
        machine_model="MCY-3", product_series="MCY",
        order_qty=Decimal("1"), cycle_days_median=Decimal("20"),
        sample_count=3, is_active=True,
    ))
    db_session.add(BomRelationSrc(
        machine_material_no="MAT-SCH", plant="1000",
        material_no="MAT-SCH", bom_component_no="ASM-SCH",
        bom_component_desc="机身MCY-3", bom_level=1,
        is_top_level=True, is_self_made=True, part_type="自产件",
    ))
    await db_session.commit()

    resp = await app_client.get("/api/schedules")
    body = resp.json()

    status_map = {item["contract_no"]: item["schedule_status"] for item in body["data"]["items"]}
    assert status_map["HT-DEL"] == "pending_delivery"
    assert status_map["HT-PD"] == "pending_drawing"
    assert status_map["HT-BOM"] == "missing_bom"
    assert status_map["HT-SCH"] == "schedulable"


@pytest.mark.asyncio
async def test_list_schedules_filter_by_dynamic_schedulable_status(app_client, db_session):
    schedulable = SalesPlanOrderLineSrc(
        contract_no="HT-DYN",
        customer_name="Dynamic Status",
        product_series="MCZ",
        product_model="MCZ-1",
        material_no="MAT-DYN",
        quantity=Decimal("1"),
        order_no="SO-DYN",
        confirmed_delivery_date=datetime(2025, 1, 15),
        drawing_released=True,
        drawing_release_date=datetime(2024, 12, 1),
    )
    db_session.add(schedulable)
    await db_session.flush()
    db_session.add(MachineCycleBaseline(
        machine_model="MCZ-1", product_series="MCZ",
        order_qty=Decimal("1"), cycle_days_median=Decimal("20"),
        sample_count=3, is_active=True,
    ))
    db_session.add(BomRelationSrc(
        machine_material_no="MAT-DYN", plant="1000",
        material_no="MAT-DYN", bom_component_no="ASM-DYN",
        bom_component_desc="机身MCZ-1", bom_level=1,
        is_top_level=True, is_self_made=True, part_type="自产件",
    ))
    await db_session.commit()

    resp = await app_client.get("/api/schedules?schedule_status=schedulable")
    body = resp.json()

    assert body["code"] == 0
    assert body["data"]["total"] == 1
    assert body["data"]["items"][0]["contract_no"] == "HT-DYN"


@pytest.mark.asyncio
async def test_list_schedules_persists_seeded_snapshots(app_client, db_session):
    db_session.add(SalesPlanOrderLineSrc(
        contract_no="HT-SEED",
        customer_name="Seed Persist",
        product_series="MCS",
        product_model="MCS-1",
        material_no="MAT-SEED",
        quantity=Decimal("1"),
        order_no="SO-SEED",
        confirmed_delivery_date=datetime(2025, 1, 15),
        drawing_released=True,
        drawing_release_date=datetime(2024, 12, 1),
    ))
    db_session.add(MachineCycleBaseline(
        machine_model="MCS-1", product_series="MCS",
        order_qty=Decimal("1"), cycle_days_median=Decimal("20"),
        sample_count=3, is_active=True,
    ))
    db_session.add(BomRelationSrc(
        machine_material_no="MAT-SEED", plant="1000",
        material_no="MAT-SEED", bom_component_no="ASM-SEED",
        bom_component_desc="机身MCS-1", bom_level=1,
        is_top_level=True, is_self_made=True, part_type="自产件",
    ))
    await db_session.commit()

    resp = await app_client.get("/api/schedules?page_no=1&page_size=10")
    body = resp.json()

    assert body["code"] == 0
    snapshot_count = await db_session.scalar(select(func.count()).select_from(OrderScheduleSnapshot))
    assert snapshot_count == 1


@pytest.mark.asyncio
async def test_second_schedule_query_reuses_existing_snapshot_seed(app_client, db_session, monkeypatch):
    db_session.add(SalesPlanOrderLineSrc(
        contract_no="HT-REUSE",
        customer_name="Seed Reuse",
        product_series="MCR",
        product_model="MCR-1",
        material_no="MAT-REUSE",
        quantity=Decimal("1"),
        order_no="SO-REUSE",
        confirmed_delivery_date=datetime(2025, 1, 15),
        drawing_released=True,
        drawing_release_date=datetime(2024, 12, 1),
    ))
    db_session.add(MachineCycleBaseline(
        machine_model="MCR-1", product_series="MCR",
        order_qty=Decimal("1"), cycle_days_median=Decimal("20"),
        sample_count=3, is_active=True,
    ))
    db_session.add(BomRelationSrc(
        machine_material_no="MAT-REUSE", plant="1000",
        material_no="MAT-REUSE", bom_component_no="ASM-REUSE",
        bom_component_desc="机身MCR-1", bom_level=1,
        is_top_level=True, is_self_made=True, part_type="自产件",
    ))
    await db_session.commit()

    first_resp = await app_client.get("/api/schedules?page_no=1&page_size=10")
    assert first_resp.json()["code"] == 0

    async def fail_fast_seed(self, source: str, reason: str):
        raise AssertionError("_fast_seed_all should not run when snapshot data already exists")

    monkeypatch.setattr(ScheduleSnapshotRefreshService, "_fast_seed_all", fail_fast_seed)

    second_resp = await app_client.get("/api/schedules?page_no=1&page_size=10")
    assert second_resp.json()["code"] == 0


@pytest.mark.asyncio
async def test_schedule_detail_returns_dynamic_status_for_unscheduled_order(app_client, db_session):
    order = SalesPlanOrderLineSrc(
        contract_no="HT-DETAIL",
        customer_name="Detail Pending",
        product_series="MCD",
        product_model="MCD-1",
        material_no="MAT-DETAIL",
        quantity=Decimal("1"),
        order_no="SO-DETAIL",
        confirmed_delivery_date=datetime(2026, 6, 30),
        drawing_released=False,
    )
    db_session.add(order)
    await db_session.commit()

    resp = await app_client.get(f"/api/schedules/{order.id}")
    body = resp.json()

    assert body["code"] == 0
    assert body["data"]["machine_schedule"]["contract_no"] == "HT-DETAIL"
    assert body["data"]["machine_schedule"]["schedule_status"] == "pending_drawing"
    assert body["data"]["part_schedules"] == []


@pytest.mark.asyncio
async def test_dashboard_overview_returns_real_aggregates(app_client, db_session):
    db_session.add_all([
        OrderScheduleSnapshot(
            order_line_id=300,
            contract_no="HT300",
            customer_name="A客户",
            product_model="MC1-80",
            order_no="SO300",
            confirmed_delivery_date=datetime(2026, 5, 10),
            schedule_status="scheduled",
            warning_level="normal",
            planned_end_date=datetime(2026, 5, 20),
            machine_cycle_days=Decimal("60"),
            machine_assembly_days=Decimal("3"),
            drawing_released=True,
        ),
        OrderScheduleSnapshot(
            order_line_id=301,
            contract_no="HT301",
            customer_name="B客户",
            product_model="MC2-100",
            order_no="SO301",
            confirmed_delivery_date=datetime(2026, 4, 15),
            schedule_status="pending_trigger",
            warning_level="abnormal",
            planned_end_date=datetime(2026, 6, 5),
            machine_cycle_days=Decimal("90"),
            machine_assembly_days=Decimal("3"),
            drawing_released=False,
        ),
        MachineScheduleResult(
            order_line_id=300,
            contract_no="HT300",
            customer_name="A客户",
            product_model="MC1-80",
            order_no="SO300",
            confirmed_delivery_date=datetime(2026, 5, 10),
            schedule_status="scheduled",
            warning_level="normal",
            planned_end_date=datetime(2026, 5, 20),
            machine_cycle_days=Decimal("60"),
            machine_assembly_days=Decimal("3"),
        ),
    ])
    db_session.add_all([
        PartScheduleResult(
            order_line_id=300,
            assembly_name="机身",
            production_sequence=1,
            part_material_no="P300",
            part_name="机身件",
            is_key_part=True,
            part_cycle_days=Decimal("10"),
            warning_level="normal",
        ),
        PartScheduleResult(
            order_line_id=301,
            assembly_name="机身",
            production_sequence=1,
            part_material_no="P301",
            part_name="机身件2",
            is_key_part=True,
            part_cycle_days=Decimal("12"),
            warning_level="abnormal",
        ),
        PartScheduleResult(
            order_line_id=301,
            assembly_name="电控",
            production_sequence=2,
            part_material_no="P302",
            part_name="电控件",
            is_key_part=False,
            part_cycle_days=Decimal("8"),
            warning_level="normal",
        ),
    ])
    await db_session.commit()

    resp = await app_client.get("/api/dashboard/overview")
    body = resp.json()

    assert body["code"] == 0
    assert body["data"]["machine_summary"]["total_orders"] == 2
    assert body["data"]["machine_summary"]["scheduled_orders"] == 1
    assert {item["key"]: item["count"] for item in body["data"]["machine_summary"]["status_counts"]} == {
        "pending_trigger": 1,
        "scheduled": 1,
    }
    assert body["data"]["machine_summary"]["unscheduled_orders"] == 1
    assert body["data"]["machine_summary"]["abnormal_orders"] == 1
    assert {item["key"]: item["count"] for item in body["data"]["machine_summary"]["planned_end_month_counts"]} == {
        "2026-05": 1,
        "2026-06": 1,
    }
    assert body["data"]["machine_summary"]["warning_orders"][0]["contract_no"] == "HT301"
    assert set(body["data"]["today_summary"].keys()) == {"delivery_count", "unscheduled_count", "abnormal_count"}
    assert set(body["data"]["week_summary"].keys()) == {"delivery_count", "unscheduled_count", "abnormal_count"}
    assert set(body["data"]["month_summary"].keys()) == {"delivery_count", "unscheduled_count", "abnormal_count"}
    assert isinstance(body["data"]["delivery_risk_orders"], list)
    assert body["data"]["part_summary"]["total_parts"] == 3
    assert body["data"]["part_summary"]["abnormal_parts"] == 1
    assert {item["key"]: item["count"] for item in body["data"]["part_summary"]["warning_counts"]} == {
        "abnormal": 1,
        "normal": 2,
    }
    assert body["data"]["part_summary"]["top_assemblies"][0] == {"assembly_name": "机身", "count": 2}


    assert set(body["data"]["delivery_trends"].keys()) == {"day", "week", "month"}
    assert len(body["data"]["delivery_trends"]["day"]) == 30
    assert len(body["data"]["delivery_trends"]["week"]) == 12
    assert len(body["data"]["delivery_trends"]["month"]) == 12
    assert body["data"]["business_group_summary"][0]["business_group"]
    assert body["data"]["business_group_summary"][0]["order_count"] == 2
    assert body["data"]["abnormal_machine_orders"][0]["contract_no"] == "HT301"

@pytest.mark.asyncio
async def test_dashboard_overview_uses_repo_aggregates(db_session, monkeypatch):
    service = ScheduleQueryService(db_session)

    async def fake_ensure_ready():
        return None

    async def fake_machine_dashboard_summary():
        return {
            "total_orders": 5,
            "scheduled_orders": 3,
            "abnormal_orders": 2,
            "status_counts": [("pending_trigger", 2), ("scheduled", 3)],
            "planned_end_month_counts": [("2026-05", 2), ("2026-06", 3)],
        }

    async def fake_time_summaries(field_name, windows):
        assert field_name == "confirmed_delivery_date"
        assert [bucket for bucket, _, _ in windows] == ["today", "week", "month"]
        return {
            "today": {"delivery_count": 1, "unscheduled_count": 1, "abnormal_count": 0},
            "week": {"delivery_count": 2, "unscheduled_count": 1, "abnormal_count": 1},
            "month": {"delivery_count": 4, "unscheduled_count": 2, "abnormal_count": 2},
        }

    async def fake_warning_orders(limit=10):
        assert limit == 10
        return [{"contract_no": "HT-WARN"}]

    async def fake_delivery_risk_orders(start_date, end_date, limit=20):
        assert limit == 20
        assert end_date > start_date
        return [{"contract_no": "HT-RISK"}]

    async def fake_part_dashboard_summary(top_assembly_limit=10):
        assert top_assembly_limit == 10
        return {
            "total_parts": 8,
            "abnormal_parts": 3,
            "warning_counts": [("abnormal", 3), ("normal", 5)],
            "top_assemblies": [("机身", 4), ("电控", 2)],
        }

    async def fake_business_group_summary(limit=None):
        assert limit == 8
        return [("Group-A", 2, Decimal("860000")), ("Ungrouped", 1, Decimal("120000"))]

    async def fake_abnormal_orders(limit=50):
        assert limit == 50
        return [{"contract_no": "HT-ABNORMAL"}]

    async def fake_aggregate_quantity_by_day(field_name, start_date, end_date):
        assert field_name in {"planned_end_date", "planned_start_date", "confirmed_delivery_date"}
        assert end_date > start_date
        return {start_date: {"order_count": 2, "quantity_sum": Decimal("2")}}

    async def fail_legacy(*args, **kwargs):
        raise AssertionError("legacy dashboard query should not be used")

    monkeypatch.setattr(service, "ensure_snapshots_ready", fake_ensure_ready)
    monkeypatch.setattr(service.snapshot_repo, "get_dashboard_summary", fake_machine_dashboard_summary)
    monkeypatch.setattr(service.snapshot_repo, "summarize_date_field_windows", fake_time_summaries)
    monkeypatch.setattr(service.snapshot_repo, "list_warning_orders", fake_warning_orders)
    monkeypatch.setattr(service.snapshot_repo, "list_delivery_risk_orders", fake_delivery_risk_orders)
    monkeypatch.setattr(service.snapshot_repo, "summarize_business_groups", fake_business_group_summary)
    monkeypatch.setattr(service.snapshot_repo, "list_abnormal_orders", fake_abnormal_orders)
    monkeypatch.setattr(service.snapshot_repo, "aggregate_quantity_by_day", fake_aggregate_quantity_by_day)
    monkeypatch.setattr(service.snapshot_repo, "count_all", fail_legacy)
    monkeypatch.setattr(service.snapshot_repo, "count_by_schedule_status", fail_legacy)
    monkeypatch.setattr(service.snapshot_repo, "count_by_warning_level", fail_legacy)
    monkeypatch.setattr(service.snapshot_repo, "count_by_planned_end_month", fail_legacy)
    monkeypatch.setattr(service.snapshot_repo, "summarize_date_field_window", fail_legacy)
    monkeypatch.setattr(service.psr_repo, "get_dashboard_summary", fake_part_dashboard_summary)
    monkeypatch.setattr(service.psr_repo, "count_all", fail_legacy)
    monkeypatch.setattr(service.psr_repo, "count_abnormal", fail_legacy)
    monkeypatch.setattr(service.psr_repo, "count_by_warning_level", fail_legacy)
    monkeypatch.setattr(service.psr_repo, "top_assembly_counts", fail_legacy)

    body = await service.get_dashboard_overview()

    assert body["machine_summary"]["total_orders"] == 5
    assert body["machine_summary"]["scheduled_orders"] == 3
    assert body["machine_summary"]["unscheduled_orders"] == 2
    assert body["machine_summary"]["abnormal_orders"] == 2
    assert body["machine_summary"]["warning_orders"] == [{"contract_no": "HT-WARN"}]
    assert len(body["machine_summary"]["planned_end_day_counts"]) == 1
    assert body["machine_summary"]["planned_end_day_counts"][0]["count"] == 2
    assert body["part_summary"]["total_parts"] == 8
    assert body["part_summary"]["abnormal_parts"] == 3
    assert body["part_summary"]["top_assemblies"] == [
        {"assembly_name": "机身", "count": 4},
        {"assembly_name": "电控", "count": 2},
    ]
    assert body["delivery_risk_orders"] == [{"contract_no": "HT-RISK"}]
    assert body["delivery_trends"]["day"][0]["scheduled_count"] == 2
    assert body["delivery_trends"]["day"][0]["delivery_count"] == 2
    assert body["business_group_summary"] == [
        {"business_group": "Group-A", "order_count": 2, "total_amount": Decimal("860000")},
        {"business_group": "Ungrouped", "order_count": 1, "total_amount": Decimal("120000")},
    ]
    assert body["abnormal_machine_orders"] == [{"contract_no": "HT-ABNORMAL"}]
    assert body["week_summary"]["abnormal_count"] == 1


@pytest.mark.asyncio
async def test_schedule_calendar_day_detail_uses_repo_aggregate(db_session, monkeypatch):
    service = ScheduleQueryService(db_session)

    async def fake_ensure_ready():
        return None

    async def fake_calendar_day_detail(target_date):
        assert target_date == date(2026, 4, 15)
        return {
            "summary": {
                "calendar_date": target_date,
                "delivery_order_count": 2,
                "delivery_quantity_sum": Decimal("3"),
                "trigger_order_count": 1,
                "trigger_quantity_sum": Decimal("1"),
                "planned_start_order_count": 2,
                "planned_start_quantity_sum": Decimal("3"),
            },
            "delivery_orders": [{"order_line_id": 1101}, {"order_line_id": 1102}],
            "trigger_orders": [{"order_line_id": 1101}],
            "planned_start_orders": [{"order_line_id": 1101}, {"order_line_id": 1102}],
        }

    async def fail_legacy(*args, **kwargs):
        raise AssertionError("legacy calendar detail query should not be used")

    monkeypatch.setattr(service, "ensure_snapshots_ready", fake_ensure_ready)
    monkeypatch.setattr(service.snapshot_repo, "get_calendar_day_detail", fake_calendar_day_detail)
    monkeypatch.setattr(service.snapshot_repo, "summarize_calendar_day", fail_legacy)
    monkeypatch.setattr(service.snapshot_repo, "list_by_date_field", fail_legacy)

    body = await service.get_schedule_calendar_day_detail(date(2026, 4, 15))

    assert body["summary"]["delivery_order_count"] == 2
    assert body["delivery_orders"] == [{"order_line_id": 1101}, {"order_line_id": 1102}]
    assert body["trigger_orders"] == [{"order_line_id": 1101}]
    assert body["planned_start_orders"] == [{"order_line_id": 1101}, {"order_line_id": 1102}]


@pytest.mark.asyncio
async def test_list_part_schedules_filter_by_frontend_params(app_client, db_session):
    db_session.add(MachineScheduleResult(
        order_line_id=200, contract_no="HT200", order_no="SO200", product_model="MC1-80",
        schedule_status="scheduled",
        machine_cycle_days=Decimal("60"), machine_assembly_days=Decimal("3"),
    ))
    db_session.add(MachineScheduleResult(
        order_line_id=201, contract_no="HT201", order_no="SO201", product_model="MC2-100",
        schedule_status="scheduled",
        machine_cycle_days=Decimal("90"), machine_assembly_days=Decimal("3"),
    ))
    db_session.add(PartScheduleResult(
        order_line_id=200, assembly_name="机身", production_sequence=1,
        part_material_no="P200", part_name="机身焊接件", is_key_part=True,
        part_cycle_days=Decimal("15"), part_cycle_is_default=False, part_cycle_match_rule="exact_material",
        key_part_material_no="P200", key_part_cycle_days=Decimal("15"),
        planned_end_date=datetime(2025, 3, 20, 0, 0, 0),
    ))
    db_session.add(PartScheduleResult(
        order_line_id=201, assembly_name="电控箱", production_sequence=1,
        part_material_no="P201", part_name="电控箱总成", is_key_part=True,
        part_cycle_days=Decimal("12"), part_cycle_is_default=False, part_cycle_match_rule="exact_material",
        key_part_material_no="P201", key_part_cycle_days=Decimal("12"),
        planned_end_date=datetime(2025, 4, 5, 0, 0, 0),
    ))
    await db_session.commit()

    resp = await app_client.get("/api/part-schedules?contract_no=HT200")
    body = resp.json()
    assert body["code"] == 0
    assert body["data"]["total"] == 1
    assert body["data"]["items"][0]["order_no"] == "SO200"

    resp = await app_client.get("/api/part-schedules?order_no=SO201")
    body = resp.json()
    assert body["data"]["total"] == 1
    assert body["data"]["items"][0]["contract_no"] == "HT201"

    resp = await app_client.get("/api/part-schedules?assembly_name=机身")
    body = resp.json()
    assert body["data"]["total"] == 1
    assert body["data"]["items"][0]["part_material_no"] == "P200"

    resp = await app_client.get("/api/part-schedules?part_material_no=P201")
    body = resp.json()
    assert body["data"]["total"] == 1
    assert body["data"]["items"][0]["assembly_name"] == "电控箱"

    resp = await app_client.get("/api/part-schedules?date_from=2025-03-01&date_to=2025-03-31")
    body = resp.json()
    assert body["code"] == 0
    assert body["data"]["total"] == 1
    assert body["data"]["items"][0]["part_material_no"] == "P200"


@pytest.mark.asyncio
async def test_get_part_schedule_assembly_name_options(app_client, db_session):
    db_session.add(PartScheduleResult(
        order_line_id=300, assembly_name="机身", production_sequence=1,
        part_material_no="P300", part_name="机身焊接件", is_key_part=True,
        part_cycle_days=Decimal("10"), part_cycle_is_default=False, part_cycle_match_rule="exact_material",
        key_part_material_no="P300", key_part_cycle_days=Decimal("10"),
    ))
    db_session.add(PartScheduleResult(
        order_line_id=301, assembly_name="电控箱", production_sequence=1,
        part_material_no="P301", part_name="电控箱总成", is_key_part=True,
        part_cycle_days=Decimal("8"), part_cycle_is_default=False, part_cycle_match_rule="exact_material",
        key_part_material_no="P301", key_part_cycle_days=Decimal("8"),
    ))
    db_session.add(PartScheduleResult(
        order_line_id=302, assembly_name="机身", production_sequence=2,
        part_material_no="P302", part_name="机身支架", is_key_part=False,
        part_cycle_days=Decimal("6"), part_cycle_is_default=False, part_cycle_match_rule="exact_material",
        key_part_material_no="P300", key_part_cycle_days=Decimal("10"),
    ))
    db_session.add(PartScheduleResult(
        order_line_id=303, assembly_name="总装", production_sequence=1,
    ))
    await db_session.commit()

    resp = await app_client.get("/api/part-schedules/options/assembly-names")
    body = resp.json()
    assert body["code"] == 0
    assert body["data"] == sorted(body["data"])
    assert set(body["data"]) == {"机身", "电控箱"}




@pytest.mark.asyncio
async def test_list_part_schedules_hides_placeholder_rows(app_client, db_session):
    db_session.add(MachineScheduleResult(
        order_line_id=260, contract_no="HT260", order_no="SO260", product_model="MC1-80",
        schedule_status="scheduled",
        machine_cycle_days=Decimal("60"), machine_assembly_days=Decimal("3"),
    ))
    db_session.add(PartScheduleResult(
        order_line_id=260, assembly_name="总装", production_sequence=1,
        planned_end_date=datetime(2025, 3, 20, 0, 0, 0),
    ))
    db_session.add(PartScheduleResult(
        order_line_id=260, assembly_name="机身", production_sequence=2,
        part_material_no="P260", part_name="机身焊接件", is_key_part=True,
        part_cycle_days=Decimal("15"), part_cycle_is_default=False, part_cycle_match_rule="exact_material",
        key_part_material_no="P260", key_part_cycle_days=Decimal("15"),
        planned_end_date=datetime(2025, 3, 22, 0, 0, 0),
    ))
    await db_session.commit()

    resp = await app_client.get("/api/part-schedules?contract_no=HT260")
    body = resp.json()
    assert body["code"] == 0
    assert body["data"]["total"] == 1
    assert len(body["data"]["items"]) == 1
    assert body["data"]["items"][0]["assembly_name"] == "机身"
    assert body["data"]["items"][0]["part_name"] == "机身焊接件"

@pytest.mark.asyncio
async def test_list_schedules_filter_by_frontend_params(app_client, db_session):
    db_session.add_all([
        MachineScheduleResult(
            order_line_id=400,
            contract_no="HT-400-A",
            customer_name="Alpha Robotics",
            product_series="MC2",
            product_model="MC2-200",
            order_no="SO-400-A",
            schedule_status="scheduled",
            warning_level="abnormal",
            confirmed_delivery_date=datetime(2025, 5, 10, 0, 0, 0),
            machine_cycle_days=Decimal("60"),
            machine_assembly_days=Decimal("3"),
        ),
        MachineScheduleResult(
            order_line_id=401,
            contract_no="HT-401-B",
            customer_name="Beta Factory",
            product_series="MC1",
            product_model="MC1-80",
            order_no="SO-401-B",
            schedule_status="pending_trigger",
            warning_level="normal",
            confirmed_delivery_date=datetime(2025, 6, 15, 0, 0, 0),
            machine_cycle_days=Decimal("45"),
            machine_assembly_days=Decimal("2"),
        ),
    ])
    await db_session.commit()

    resp = await app_client.get("/api/schedules?contract_no=400")
    body = resp.json()
    assert body["data"]["total"] == 1
    assert body["data"]["items"][0]["order_line_id"] == 400

    resp = await app_client.get("/api/schedules?customer_name=Alpha")
    body = resp.json()
    assert body["data"]["total"] == 1
    assert body["data"]["items"][0]["order_line_id"] == 400

    resp = await app_client.get("/api/schedules?product_series=MC2")
    body = resp.json()
    assert body["data"]["total"] == 1
    assert body["data"]["items"][0]["order_line_id"] == 400

    resp = await app_client.get("/api/schedules?product_model=MC2")
    body = resp.json()
    assert body["data"]["total"] == 1
    assert body["data"]["items"][0]["order_line_id"] == 400

    resp = await app_client.get("/api/schedules?order_no=400")
    body = resp.json()
    assert body["data"]["total"] == 1
    assert body["data"]["items"][0]["order_line_id"] == 400

    resp = await app_client.get("/api/schedules?schedule_status=scheduled")
    body = resp.json()
    assert body["data"]["total"] == 1
    assert body["data"]["items"][0]["order_line_id"] == 400

    resp = await app_client.get("/api/schedules?warning_level=abnormal")
    body = resp.json()
    assert body["data"]["total"] == 1
    assert body["data"]["items"][0]["order_line_id"] == 400

    resp = await app_client.get("/api/schedules?date_from=2025-05-01&date_to=2025-05-31")
    body = resp.json()
    assert body["data"]["total"] == 1
    assert body["data"]["items"][0]["order_line_id"] == 400


@pytest.mark.asyncio
async def test_list_part_schedules_filter_by_warning_level(app_client, db_session):
    db_session.add_all([
        MachineScheduleResult(
            order_line_id=500,
            contract_no="HT500",
            order_no="SO500",
            product_model="MC5-500",
            schedule_status="scheduled",
            machine_cycle_days=Decimal("60"),
            machine_assembly_days=Decimal("3"),
        ),
        MachineScheduleResult(
            order_line_id=501,
            contract_no="HT501",
            order_no="SO501",
            product_model="MC5-501",
            schedule_status="scheduled",
            machine_cycle_days=Decimal("60"),
            machine_assembly_days=Decimal("3"),
        ),
        PartScheduleResult(
            order_line_id=500,
            assembly_name="Assembly-A",
            production_sequence=1,
            part_material_no="P500",
            part_name="Part 500",
            is_key_part=True,
            part_cycle_days=Decimal("15"),
            part_cycle_is_default=False,
            part_cycle_match_rule="exact_material",
            key_part_material_no="P500",
            key_part_cycle_days=Decimal("15"),
            warning_level="abnormal",
        ),
        PartScheduleResult(
            order_line_id=501,
            assembly_name="Assembly-B",
            production_sequence=1,
            part_material_no="P501",
            part_name="Part 501",
            is_key_part=True,
            part_cycle_days=Decimal("12"),
            part_cycle_is_default=False,
            part_cycle_match_rule="exact_material",
            key_part_material_no="P501",
            key_part_cycle_days=Decimal("12"),
            warning_level="normal",
        ),
    ])
    await db_session.commit()

    resp = await app_client.get("/api/part-schedules?warning_level=abnormal")
    body = resp.json()
    assert body["code"] == 0
    assert body["data"]["total"] == 1
    assert body["data"]["items"][0]["order_line_id"] == 500


@pytest.mark.asyncio
async def test_list_part_schedules_enriches_contract_and_order_numbers_in_batch(app_client, db_session):
    db_session.add_all([
        OrderScheduleSnapshot(
            order_line_id=601,
            contract_no="HT601",
            order_no="SO601",
            product_model="MC6-601",
            schedule_status="scheduled",
            warning_level="normal",
            machine_cycle_days=Decimal("30"),
            machine_assembly_days=Decimal("3"),
        ),
        OrderScheduleSnapshot(
            order_line_id=602,
            contract_no="HT602",
            order_no="SO602",
            product_model="MC6-602",
            schedule_status="scheduled",
            warning_level="abnormal",
            machine_cycle_days=Decimal("35"),
            machine_assembly_days=Decimal("3"),
        ),
        PartScheduleResult(
            order_line_id=601,
            assembly_name="Assembly-601",
            production_sequence=1,
            part_material_no="P601",
            part_name="Part 601",
            is_key_part=True,
            part_cycle_days=Decimal("10"),
            part_cycle_is_default=False,
            part_cycle_match_rule="exact_material",
            key_part_material_no="P601",
            key_part_cycle_days=Decimal("10"),
        ),
        PartScheduleResult(
            order_line_id=602,
            assembly_name="Assembly-602",
            production_sequence=1,
            part_material_no="P602",
            part_name="Part 602",
            is_key_part=True,
            part_cycle_days=Decimal("12"),
            part_cycle_is_default=False,
            part_cycle_match_rule="exact_material",
            key_part_material_no="P602",
            key_part_cycle_days=Decimal("12"),
        ),
    ])
    await db_session.commit()

    resp = await app_client.get("/api/part-schedules?page_no=1&page_size=20")
    body = resp.json()

    assert body["code"] == 0
    items_by_id = {item["order_line_id"]: item for item in body["data"]["items"]}
    assert items_by_id[601]["contract_no"] == "HT601"
    assert items_by_id[601]["order_no"] == "SO601"
    assert items_by_id[602]["contract_no"] == "HT602"
    assert items_by_id[602]["order_no"] == "SO602"


@pytest.mark.asyncio
async def test_list_part_schedules_supports_snapshot_sort_without_machine_rows(app_client, db_session):
    db_session.add_all([
        OrderScheduleSnapshot(
            order_line_id=701,
            contract_no="HT701-A",
            order_no="SO701",
            product_model="MC7-701",
            schedule_status="scheduled",
            warning_level="normal",
        ),
        OrderScheduleSnapshot(
            order_line_id=702,
            contract_no="HT702-B",
            order_no="SO702",
            product_model="MC7-702",
            schedule_status="scheduled",
            warning_level="normal",
        ),
        PartScheduleResult(
            order_line_id=701,
            assembly_name="Assembly-701",
            production_sequence=1,
            part_material_no="P701",
            part_name="Part 701",
            is_key_part=True,
        ),
        PartScheduleResult(
            order_line_id=702,
            assembly_name="Assembly-702",
            production_sequence=1,
            part_material_no="P702",
            part_name="Part 702",
            is_key_part=True,
        ),
    ])
    await db_session.commit()

    resp = await app_client.get(
        "/api/part-schedules",
        params={"sort_field": "contract_no", "sort_order": "desc"},
    )
    body = resp.json()

    assert body["code"] == 0
    assert [item["contract_no"] for item in body["data"]["items"]] == ["HT702-B", "HT701-A"]


@pytest.mark.asyncio
async def test_schedule_detail_hides_placeholder_part_rows(app_client, db_session):
    db_session.add(MachineScheduleResult(
        order_line_id=910,
        contract_no="HT910",
        product_model="MC1-80",
        schedule_status="scheduled",
        machine_cycle_days=Decimal("60"),
        machine_assembly_days=Decimal("3"),
    ))
    db_session.add(PartScheduleResult(
        order_line_id=910,
        assembly_name="平衡缸",
        production_sequence=1,
        planned_end_date=datetime(2025, 3, 20, 0, 0, 0),
    ))
    db_session.add(PartScheduleResult(
        order_line_id=910,
        assembly_name="机身",
        production_sequence=2,
        part_material_no="P910",
        part_name="机身焊接件",
        is_key_part=True,
        part_cycle_days=Decimal("15"),
        key_part_material_no="P910",
        key_part_cycle_days=Decimal("15"),
        planned_end_date=datetime(2025, 3, 21, 0, 0, 0),
    ))
    await db_session.commit()

    resp = await app_client.get("/api/schedules/910")
    body = resp.json()

    assert body["code"] == 0
    assert len(body["data"]["part_schedules"]) == 1
    assert body["data"]["part_schedules"][0]["assembly_name"] == "机身"
    assert body["data"]["part_schedules"][0]["part_name"] == "机身焊接件"

@pytest.mark.asyncio
async def test_dashboard_overview_excludes_placeholder_part_rows(app_client, db_session):
    db_session.add(OrderScheduleSnapshot(
        order_line_id=950,
        contract_no="HT950",
        customer_name="Customer 950",
        product_model="MC1-80",
        order_no="SO950",
        confirmed_delivery_date=datetime(2026, 7, 1),
        schedule_status="scheduled",
        warning_level="normal",
        planned_end_date=datetime(2026, 7, 15),
        machine_cycle_days=Decimal("60"),
        machine_assembly_days=Decimal("3"),
        drawing_released=True,
    ))
    db_session.add_all([
        PartScheduleResult(
            order_line_id=950,
            assembly_name="Hidden-Assembly",
            production_sequence=1,
            warning_level="abnormal",
        ),
        PartScheduleResult(
            order_line_id=950,
            assembly_name="Visible-Assembly",
            production_sequence=2,
            part_material_no="P950",
            part_name="Visible Part",
            is_key_part=True,
            part_cycle_days=Decimal("10"),
            warning_level="normal",
        ),
    ])
    await db_session.commit()

    resp = await app_client.get("/api/dashboard/overview")
    body = resp.json()

    assert body["code"] == 0
    assert body["data"]["part_summary"]["total_parts"] == 1
    assert body["data"]["part_summary"]["abnormal_parts"] == 0
    assert {item["key"]: item["count"] for item in body["data"]["part_summary"]["warning_counts"]} == {
        "normal": 1,
    }
    assert body["data"]["part_summary"]["top_assemblies"] == [
        {"assembly_name": "Visible-Assembly", "count": 1}
    ]



@pytest.mark.asyncio
async def test_list_schedules_supports_schedule_bucket_filters(app_client, db_session):
    db_session.add_all([
        MachineScheduleResult(
            order_line_id=880,
            contract_no="HT880",
            product_model="MC1-80",
            order_no="SO880",
            schedule_status="scheduled",
            warning_level="normal",
            confirmed_delivery_date=datetime(2026, 5, 10, 0, 0, 0),
            machine_cycle_days=Decimal("30"),
            machine_assembly_days=Decimal("2"),
        ),
        MachineScheduleResult(
            order_line_id=881,
            contract_no="HT881",
            product_model="MC1-80",
            order_no="SO881",
            schedule_status="pending_trigger",
            warning_level="normal",
            confirmed_delivery_date=datetime(2026, 5, 11, 0, 0, 0),
            machine_cycle_days=Decimal("35"),
            machine_assembly_days=Decimal("2"),
        ),
        MachineScheduleResult(
            order_line_id=882,
            contract_no="HT882",
            product_model="MC1-80",
            order_no="SO882",
            schedule_status="scheduled",
            warning_level="abnormal",
            confirmed_delivery_date=datetime(2026, 5, 12, 0, 0, 0),
            machine_cycle_days=Decimal("40"),
            machine_assembly_days=Decimal("3"),
        ),
    ])
    await db_session.commit()

    resp = await app_client.get('/api/schedules?schedule_bucket=unscheduled')
    body = resp.json()
    assert body['code'] == 0
    assert {item['order_line_id'] for item in body['data']['items']} == {881}

    resp = await app_client.get('/api/schedules?schedule_bucket=risk')
    body = resp.json()
    assert body['code'] == 0
    assert {item['order_line_id'] for item in body['data']['items']} == {881, 882}
