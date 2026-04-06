import pytest

from app.models.data_issue import DataIssueRecord


@pytest.mark.asyncio
async def test_resolve_issue(app_client, db_session):
    issue = DataIssueRecord(
        issue_type="周期异常",
        issue_title="测试",
        status="open",
    )
    db_session.add(issue)
    await db_session.commit()

    resp = await app_client.post(
        f"/api/admin/issues/{issue.id}/resolve",
        json={"remark": "已处理"},
    )
    body = resp.json()
    assert body["code"] == 0
    assert body["data"]["status"] == "resolved"


@pytest.mark.asyncio
async def test_ignore_issue(app_client, db_session):
    issue = DataIssueRecord(
        issue_type="数据异常",
        issue_title="测试2",
        status="open",
    )
    db_session.add(issue)
    await db_session.commit()

    resp = await app_client.post(
        f"/api/admin/issues/{issue.id}/ignore",
        json={"remark": "无需处理"},
    )
    body = resp.json()
    assert body["code"] == 0
    assert body["data"]["status"] == "ignored"


@pytest.mark.asyncio
async def test_resolve_nonexistent(app_client):
    resp = await app_client.post(
        "/api/admin/issues/9999/resolve",
        json={"remark": "test"},
    )
    body = resp.json()
    assert body["code"] == 4002
