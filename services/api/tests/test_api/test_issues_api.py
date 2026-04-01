import pytest

from app.models.data_issue import DataIssueRecord
from app.models.order_schedule_snapshot import OrderScheduleSnapshot


@pytest.mark.asyncio
async def test_list_issues_empty(app_client):
    resp = await app_client.get("/api/issues")
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 0
    assert body["data"]["total"] == 0


@pytest.mark.asyncio
async def test_list_issues_with_filter(app_client, db_session):
    db_session.add(
        DataIssueRecord(
            issue_type="周期异常",
            issue_title="测试异常",
            status="open",
        )
    )
    await db_session.commit()

    resp = await app_client.get("/api/issues?status=open")
    body = resp.json()
    assert body["data"]["total"] == 1
    assert body["data"]["items"][0]["issue_type"] == "周期异常"


@pytest.mark.asyncio
async def test_list_issues_filter_by_biz_key_and_source_system(app_client, db_session):
    db_session.add_all(
        [
            DataIssueRecord(
                issue_type="BOM缺失",
                issue_title="排产前缺少 BOM 数据",
                status="open",
                biz_key="105",
                order_line_id=105,
                source_system="scheduler",
            ),
            DataIssueRecord(
                issue_type="BOM缺失",
                issue_title="排产前缺少 BOM 数据",
                status="open",
                biz_key="106",
                order_line_id=106,
                source_system="scheduler",
            ),
        ]
    )
    await db_session.commit()

    resp = await app_client.get("/api/issues?biz_key=105&source_system=scheduler")
    body = resp.json()

    assert body["data"]["total"] == 1
    assert body["data"]["items"][0]["biz_key"] == "105"
    assert body["data"]["items"][0]["order_line_id"] == 105


@pytest.mark.asyncio
async def test_list_issues_enriches_snapshot_fields(app_client, db_session):
    db_session.add(
        OrderScheduleSnapshot(
            order_line_id=225,
            contract_no="HT225",
            order_no="SO225",
            material_no="MAT225",
            custom_no="CUS225",
            schedule_status="scheduled",
        )
    )
    db_session.add(
        DataIssueRecord(
            issue_type="装配时长基准缺失",
            issue_title="测试异常",
            status="open",
            biz_key="225",
            order_line_id=225,
            source_system="scheduler",
        )
    )
    await db_session.commit()

    resp = await app_client.get("/api/issues")
    body = resp.json()

    assert body["code"] == 0
    assert body["data"]["total"] == 1
    item = body["data"]["items"][0]
    assert item["material_no"] == "MAT225"
    assert item["custom_no"] == "CUS225"
    assert item["order_no"] == "SO225"
    assert item["contract_no"] == "HT225"


@pytest.mark.asyncio
async def test_list_issues_non_numeric_biz_key_does_not_break_snapshot_join(app_client, db_session):
    db_session.add_all(
        [
            OrderScheduleSnapshot(
                order_line_id=226,
                contract_no="HT226",
                order_no="SO226",
                material_no="MAT226",
                custom_no="CUS226",
                schedule_status="scheduled",
            ),
            DataIssueRecord(
                issue_type="同步异常",
                issue_title="非订单异常",
                status="open",
                biz_key="sync_job:sales_plan",
                source_system="sync",
            ),
        ]
    )
    await db_session.commit()

    resp = await app_client.get("/api/issues")
    body = resp.json()

    assert body["code"] == 0
    assert body["data"]["total"] == 1
    item = body["data"]["items"][0]
    assert item["biz_key"] == "sync_job:sales_plan"
    assert item["order_line_id"] is None
    assert item["material_no"] is None
    assert item["custom_no"] is None
    assert item["order_no"] is None
    assert item["contract_no"] is None
