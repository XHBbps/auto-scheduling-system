import pytest
from decimal import Decimal

from app.common.exceptions import ErrorCode
from app.models.machine_cycle_history import MachineCycleHistorySrc


@pytest.mark.asyncio
async def test_delete_assembly_time(app_client):
    create_resp = await app_client.post("/api/admin/assembly-times", json={
        "machine_model": "MC1-80",
        "assembly_name": "机身",
        "assembly_time_days": 2,
        "production_sequence": 1,
    })
    create_body = create_resp.json()
    record_id = create_body["data"]["id"]

    delete_resp = await app_client.delete(f"/api/admin/assembly-times/{record_id}")
    delete_body = delete_resp.json()
    assert delete_body["code"] == 0

    list_resp = await app_client.get("/api/admin/assembly-times?machine_model=MC1-80")
    list_body = list_resp.json()
    assert list_body["code"] == 0
    assert list_body["data"] == []


@pytest.mark.asyncio
async def test_delete_machine_cycle_baseline(app_client):
    create_resp = await app_client.post("/api/admin/machine-cycle-baselines", json={
        "machine_model": "MC2-100",
        "product_series": "MC2",
        "order_qty": 1,
        "cycle_days_median": 30,
        "sample_count": 5,
        "is_active": True,
    })
    create_body = create_resp.json()
    record_id = create_body["data"]["id"]

    delete_resp = await app_client.delete(f"/api/admin/machine-cycle-baselines/{record_id}")
    delete_body = delete_resp.json()
    assert delete_body["code"] == 0

    list_resp = await app_client.get("/api/admin/machine-cycle-baselines?machine_model=MC2-100")
    list_body = list_resp.json()
    assert list_body["code"] == 0
    assert list_body["data"]["items"] == []


@pytest.mark.asyncio
async def test_delete_part_cycle_baseline(app_client):
    create_resp = await app_client.post("/api/admin/part-cycle-baselines", json={
        "part_type": "机身体焊接件",
        "material_desc": "机身体焊接件",
        "machine_model": "MC2-100",
        "ref_batch_qty": 1,
        "cycle_days": 10,
        "unit_cycle_days": 1,
        "is_active": True,
    })
    create_body = create_resp.json()
    record_id = create_body["data"]["id"]

    delete_resp = await app_client.delete(f"/api/admin/part-cycle-baselines/{record_id}")
    delete_body = delete_resp.json()
    assert delete_body["code"] == 0

    list_resp = await app_client.get("/api/admin/part-cycle-baselines?part_type=机身体焊接件")
    list_body = list_resp.json()
    assert list_body["code"] == 0
    assert list_body["data"] == []


@pytest.mark.asyncio
async def test_delete_assembly_time_not_found_returns_not_found_code(app_client):
    delete_resp = await app_client.delete("/api/admin/assembly-times/999999")
    delete_body = delete_resp.json()
    assert delete_body["code"] == ErrorCode.NOT_FOUND
    assert delete_body["message"] == "记录不存在"


@pytest.mark.asyncio
async def test_delete_machine_cycle_baseline_not_found_returns_not_found_code(app_client):
    delete_resp = await app_client.delete("/api/admin/machine-cycle-baselines/999999")
    delete_body = delete_resp.json()
    assert delete_body["code"] == ErrorCode.NOT_FOUND
    assert delete_body["message"] == "记录不存在"


@pytest.mark.asyncio
async def test_delete_part_cycle_baseline_not_found_returns_not_found_code(app_client):
    delete_resp = await app_client.delete("/api/admin/part-cycle-baselines/999999")
    delete_body = delete_resp.json()
    assert delete_body["code"] == ErrorCode.NOT_FOUND
    assert delete_body["message"] == "记录不存在"


@pytest.mark.asyncio
async def test_rebuild_machine_cycle_baseline(app_client, db_session):
    db_session.add_all([
        MachineCycleHistorySrc(
            detail_id="RB-001",
            machine_model="MC3-200",
            product_series="MC3",
            order_qty=Decimal("1"),
            cycle_days=Decimal("50"),
        ),
        MachineCycleHistorySrc(
            detail_id="RB-002",
            machine_model="MC3-200",
            product_series="MC3",
            order_qty=Decimal("1"),
            cycle_days=Decimal("70"),
        ),
        MachineCycleHistorySrc(
            detail_id="RB-003",
            machine_model="MC3-200",
            product_series="MC3",
            order_qty=Decimal("1"),
            cycle_days=Decimal("60"),
        ),
    ])
    await db_session.commit()

    rebuild_resp = await app_client.post("/api/admin/machine-cycle-baselines/rebuild")
    rebuild_body = rebuild_resp.json()

    assert rebuild_body["code"] == 0
    assert rebuild_body["data"] == {
        "groups_processed": 1,
        "total_samples": 3,
    }

    list_resp = await app_client.get("/api/admin/machine-cycle-baselines?machine_model=MC3-200")
    list_body = list_resp.json()
    assert list_body["code"] == 0
    assert len(list_body["data"]["items"]) == 1
    assert list_body["data"]["items"][0]["cycle_days_median"] == 60.0
    assert list_body["data"]["items"][0]["sample_count"] == 3


@pytest.mark.asyncio
async def test_list_machine_cycle_baseline_pagination(app_client):
    for idx in range(3):
        await app_client.post("/api/admin/machine-cycle-baselines", json={
            "machine_model": f"MC9-10{idx}",
            "product_series": "MC9",
            "order_qty": 1,
            "cycle_days_median": 20 + idx,
            "sample_count": 2,
            "is_active": True,
        })

    list_resp = await app_client.get("/api/admin/machine-cycle-baselines?page_no=1&page_size=2")
    list_body = list_resp.json()

    assert list_body["code"] == 0
    assert list_body["data"]["page_no"] == 1
    assert list_body["data"]["page_size"] == 2
    assert list_body["data"]["total"] >= 3
    assert len(list_body["data"]["items"]) == 2


@pytest.mark.asyncio
async def test_list_machine_cycle_baseline_supports_sort_by_remark(app_client):
    await app_client.post("/api/admin/machine-cycle-baselines", json={
        "machine_model": "MC-REMARK-Z",
        "product_series": "MC-R",
        "order_qty": 1,
        "cycle_days_median": 20,
        "sample_count": 2,
        "is_active": True,
        "remark": "alpha",
    })
    await app_client.post("/api/admin/machine-cycle-baselines", json={
        "machine_model": "MC-REMARK-A",
        "product_series": "MC-R",
        "order_qty": 1,
        "cycle_days_median": 21,
        "sample_count": 2,
        "is_active": True,
        "remark": "beta",
    })

    list_resp = await app_client.get(
        "/api/admin/machine-cycle-baselines?sort_field=remark&sort_order=asc&page_size=20"
    )
    list_body = list_resp.json()

    assert list_body["code"] == 0
    items = [
        item for item in list_body["data"]["items"]
        if item["machine_model"] in {"MC-REMARK-Z", "MC-REMARK-A"}
    ]
    assert [item["remark"] for item in items] == ["alpha", "beta"]
