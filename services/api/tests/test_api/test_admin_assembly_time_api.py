import pytest
from datetime import datetime
from decimal import Decimal
from sqlalchemy import select

from app.models.assembly_time import AssemblyTimeBaseline
from app.models.bom_relation import BomRelationSrc
from app.models.machine_cycle_baseline import MachineCycleBaseline
from app.models.order_schedule_snapshot import OrderScheduleSnapshot
from app.models.sales_plan import SalesPlanOrderLineSrc
from app.scheduler.schedule_orchestrator import ScheduleOrchestrator


@pytest.mark.asyncio
async def test_list_assembly_times_empty(app_client):
    resp = await app_client.get("/api/admin/assembly-times")
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 0
    assert body["data"] == []


@pytest.mark.asyncio
async def test_save_and_list_assembly_time(app_client):
    resp = await app_client.post("/api/admin/assembly-times", json={
        "machine_model": "MC1-80",
        "assembly_name": "机身",
        "assembly_time_days": 2,
        "production_sequence": 1,
    })
    body = resp.json()
    assert body["code"] == 0
    assert body["data"]["id"] is not None

    # verify appears in list
    resp2 = await app_client.get("/api/admin/assembly-times?machine_model=MC1-80")
    body2 = resp2.json()
    assert len(body2["data"]) == 1
    assert body2["data"][0]["assembly_name"] == "机身"


@pytest.mark.asyncio
async def test_update_existing_assembly_time(app_client):
    # create
    await app_client.post("/api/admin/assembly-times", json={
        "machine_model": "MC2-100",
        "assembly_name": "传动",
        "assembly_time_days": 1,
        "production_sequence": 2,
    })
    # update
    resp = await app_client.post("/api/admin/assembly-times", json={
        "machine_model": "MC2-100",
        "assembly_name": "传动",
        "assembly_time_days": 3,
        "production_sequence": 2,
    })
    body = resp.json()
    assert body["code"] == 0

    resp2 = await app_client.get("/api/admin/assembly-times?machine_model=MC2-100")
    items = resp2.json()["data"]
    assert len(items) == 1
    assert items[0]["assembly_time_days"] == 3.0


@pytest.mark.asyncio
async def test_save_assembly_time_does_not_mark_scheduled_order_stale(app_client, db_session):
    order = SalesPlanOrderLineSrc(
        sap_code="SAP-ASM-1",
        sap_line_no="10",
        product_model="MC1-80",
        product_series="MC1",
        material_no="MACH-ASM-1",
        quantity=Decimal("1"),
        confirmed_delivery_date=datetime(2026, 3, 21),
        drawing_released=True,
        drawing_release_date=datetime(2026, 3, 1),
    )
    db_session.add(order)
    db_session.add(
        MachineCycleBaseline(
            machine_model="MC1-80",
            product_series="MC1",
            order_qty=Decimal("1"),
            cycle_days_median=Decimal("1"),
            sample_count=5,
            is_active=True,
        )
    )
    db_session.add(
        AssemblyTimeBaseline(
            machine_model="MC1-80",
            assembly_name="整机总装",
            assembly_time_days=Decimal("3"),
            is_final_assembly=True,
            production_sequence=99,
        )
    )
    db_session.add(
        AssemblyTimeBaseline(
            machine_model="MC1-80",
            assembly_name="机身",
            assembly_time_days=Decimal("2"),
            is_final_assembly=False,
            production_sequence=1,
        )
    )
    db_session.add(
        BomRelationSrc(
            machine_material_no="MACH-ASM-1",
            plant="1000",
            material_no="MACH-ASM-1",
            bom_component_no="ASM-ASM-1",
            bom_component_desc="机身",
            bom_level=1,
            is_self_made=True,
            part_type="自制件",
        )
    )
    db_session.add(
        BomRelationSrc(
            machine_material_no="MACH-ASM-1",
            plant="1000",
            material_no="ASM-ASM-1",
            bom_component_no="PART-ASM-1",
            bom_component_desc="传动轴",
            bom_level=2,
            is_self_made=True,
            part_type="自制件",
        )
    )
    await db_session.commit()

    schedule_result = await ScheduleOrchestrator(db_session).schedule_order(order.id)
    await db_session.commit()
    assert schedule_result["success"] is True

    resp = await app_client.post(
        "/api/admin/assembly-times",
        json={
            "machine_model": "MC1-80",
            "assembly_name": "整机总装",
            "assembly_time_days": 5,
            "production_sequence": 99,
            "is_final_assembly": True,
        },
    )
    body = resp.json()

    snapshot = (
        await db_session.execute(
            select(OrderScheduleSnapshot).where(OrderScheduleSnapshot.order_line_id == order.id)
        )
    ).scalar_one()

    assert body["code"] == 0
    assert snapshot.schedule_status == "scheduled"


@pytest.mark.asyncio
async def test_save_final_assembly_forces_sequence_to_last_sub_assembly_plus_one(app_client):
    await app_client.post('/api/admin/assembly-times', json={
        'machine_model': 'JH21-80',
        'assembly_name': '机身',
        'assembly_time_days': 1,
        'production_sequence': 1,
        'is_final_assembly': False,
    })
    await app_client.post('/api/admin/assembly-times', json={
        'machine_model': 'JH21-80',
        'assembly_name': '传动',
        'assembly_time_days': 1,
        'production_sequence': 2,
        'is_final_assembly': False,
    })
    await app_client.post('/api/admin/assembly-times', json={
        'machine_model': 'JH21-80',
        'assembly_name': '电气',
        'assembly_time_days': 1,
        'production_sequence': 5,
        'is_final_assembly': False,
    })

    resp = await app_client.post('/api/admin/assembly-times', json={
        'machine_model': 'JH21-80',
        'assembly_name': '整机总装',
        'assembly_time_days': 3,
        'production_sequence': 1,
        'is_final_assembly': True,
    })
    body = resp.json()
    assert body['code'] == 0

    resp2 = await app_client.get('/api/admin/assembly-times?machine_model=JH21-80')
    items = resp2.json()['data']
    final_item = next(item for item in items if item['assembly_name'] == '整机总装')
    assert final_item['is_final_assembly'] is True
    assert final_item['production_sequence'] == 6


@pytest.mark.asyncio
async def test_update_existing_final_assembly_recalculates_sequence(app_client):
    await app_client.post('/api/admin/assembly-times', json={
        'machine_model': 'JH21-80-EDIT',
        'assembly_name': '机身',
        'assembly_time_days': 1,
        'production_sequence': 1,
        'is_final_assembly': False,
    })
    await app_client.post('/api/admin/assembly-times', json={
        'machine_model': 'JH21-80-EDIT',
        'assembly_name': '电气',
        'assembly_time_days': 1,
        'production_sequence': 5,
        'is_final_assembly': False,
    })
    await app_client.post('/api/admin/assembly-times', json={
        'machine_model': 'JH21-80-EDIT',
        'assembly_name': '整机总装',
        'assembly_time_days': 3,
        'production_sequence': 1,
        'is_final_assembly': True,
    })

    resp = await app_client.post('/api/admin/assembly-times', json={
        'machine_model': 'JH21-80-EDIT',
        'assembly_name': '整机总装',
        'assembly_time_days': 4,
        'production_sequence': 99,
        'is_final_assembly': True,
    })
    body = resp.json()
    assert body['code'] == 0

    resp2 = await app_client.get('/api/admin/assembly-times?machine_model=JH21-80-EDIT')
    items = resp2.json()['data']
    final_item = next(item for item in items if item['assembly_name'] == '整机总装')
    assert final_item['assembly_time_days'] == 4.0
    assert final_item['production_sequence'] == 6


@pytest.mark.asyncio
async def test_save_sub_assembly_reconciles_existing_final_assembly_sequence(app_client):
    await app_client.post('/api/admin/assembly-times', json={
        'machine_model': 'JH21-80-LATE',
        'assembly_name': '整机总装',
        'assembly_time_days': 3,
        'production_sequence': 1,
        'is_final_assembly': True,
    })
    await app_client.post('/api/admin/assembly-times', json={
        'machine_model': 'JH21-80-LATE',
        'assembly_name': '机身',
        'assembly_time_days': 1,
        'production_sequence': 1,
        'is_final_assembly': False,
    })

    resp = await app_client.post('/api/admin/assembly-times', json={
        'machine_model': 'JH21-80-LATE',
        'assembly_name': '电气',
        'assembly_time_days': 1,
        'production_sequence': 5,
        'is_final_assembly': False,
    })
    body = resp.json()
    assert body['code'] == 0

    resp2 = await app_client.get('/api/admin/assembly-times?machine_model=JH21-80-LATE')
    items = resp2.json()['data']
    final_item = next(item for item in items if item['assembly_name'] == '整机总装')
    assert final_item['production_sequence'] == 6


@pytest.mark.asyncio
async def test_delete_sub_assembly_reconciles_existing_final_assembly_sequence(app_client):
    await app_client.post('/api/admin/assembly-times', json={
        'machine_model': 'JH21-80-DELETE',
        'assembly_name': '机身',
        'assembly_time_days': 1,
        'production_sequence': 1,
        'is_final_assembly': False,
    })
    await app_client.post('/api/admin/assembly-times', json={
        'machine_model': 'JH21-80-DELETE',
        'assembly_name': '电气',
        'assembly_time_days': 1,
        'production_sequence': 5,
        'is_final_assembly': False,
    })
    await app_client.post('/api/admin/assembly-times', json={
        'machine_model': 'JH21-80-DELETE',
        'assembly_name': '整机总装',
        'assembly_time_days': 3,
        'production_sequence': 1,
        'is_final_assembly': True,
    })

    before_resp = await app_client.get('/api/admin/assembly-times?machine_model=JH21-80-DELETE')
    before_items = before_resp.json()['data']
    electric_item = next(item for item in before_items if item['assembly_name'] == '电气')

    delete_resp = await app_client.delete(f"/api/admin/assembly-times/{electric_item['id']}")
    delete_body = delete_resp.json()
    assert delete_body['code'] == 0

    after_resp = await app_client.get('/api/admin/assembly-times?machine_model=JH21-80-DELETE')
    after_items = after_resp.json()['data']
    final_item = next(item for item in after_items if item['assembly_name'] == '整机总装')
    assert final_item['production_sequence'] == 2
