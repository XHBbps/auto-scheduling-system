import pytest
from app.models import DataIssueRecord
from app.repository.data_issue_repo import DataIssueRepo


@pytest.mark.asyncio
async def test_paginate_with_filter(db_session):
    db_session.add_all([
        DataIssueRecord(issue_type="sync", issue_title="问题1", status="open"),
        DataIssueRecord(issue_type="sync", issue_title="问题2", status="resolved"),
        DataIssueRecord(issue_type="baseline", issue_title="问题3", status="open"),
    ])
    await db_session.commit()

    repo = DataIssueRepo(db_session)

    # No filter
    items, total = await repo.paginate(page_no=1, page_size=10)
    assert total == 3

    # Filter by status
    items, total = await repo.paginate(page_no=1, page_size=10, status="open")
    assert total == 2

    # Filter by type
    items, total = await repo.paginate(page_no=1, page_size=10, issue_type="sync")
    assert total == 2


def test_normalize_issue_keys_autofills_biz_key_for_order_linked_issue():
    biz_key, order_line_id = DataIssueRepo._normalize_issue_keys(
        biz_key=None,
        order_line_id=123,
    )

    assert biz_key == "123"
    assert order_line_id == 123


def test_normalize_issue_keys_rejects_mismatched_order_link():
    with pytest.raises(ValueError, match="does not match"):
        DataIssueRepo._normalize_issue_keys(
            biz_key="999",
            order_line_id=123,
        )


def test_normalize_source_system_trims_blank_to_none():
    assert DataIssueRepo._normalize_source_system(None) is None
    assert DataIssueRepo._normalize_source_system("") is None
    assert DataIssueRepo._normalize_source_system("   ") is None
    assert DataIssueRepo._normalize_source_system(" scheduler ") == "scheduler"


def test_data_issue_record_autofills_biz_key_when_order_linked():
    issue = DataIssueRecord(
        issue_type="BOM缺失",
        issue_title="测试",
        status="open",
        order_line_id=456,
    )

    assert issue.biz_key == "456"
    assert issue.order_line_id == 456


def test_data_issue_record_rejects_mismatched_order_link():
    with pytest.raises(ValueError, match="does not match"):
        DataIssueRecord(
            issue_type="BOM缺失",
            issue_title="测试",
            status="open",
            biz_key="999",
            order_line_id=456,
        )


def test_data_issue_record_normalizes_blank_source_system():
    issue = DataIssueRecord(
        issue_type="BOM缺失",
        issue_title="测试",
        status="open",
        source_system="   ",
    )

    assert issue.source_system is None


def test_build_open_issue_match_conditions_ignores_title_for_order_linked_issue():
    conditions = DataIssueRepo._build_open_issue_match_conditions(
        issue_type="BOM缺失",
        source_system="scheduler",
        issue_title="标题A",
        biz_key="123",
        order_line_id=123,
    )

    rendered = [str(condition) for condition in conditions]
    assert any("issue_type" in item for item in rendered)
    assert any("source_system" in item for item in rendered)
    assert any("order_line_id" in item for item in rendered)
    assert all("issue_title" not in item for item in rendered)


@pytest.mark.asyncio
async def test_upsert_open_issue_reuses_order_linked_issue_when_title_changes(db_session):
    repo = DataIssueRepo(db_session)
    first = await repo.upsert_open_issue(
        issue_type="BOM缺失",
        issue_level="high",
        source_system="scheduler",
        biz_key="123",
        order_line_id=123,
        issue_title="旧标题",
        issue_detail="旧说明",
    )
    await db_session.flush()

    second = await repo.upsert_open_issue(
        issue_type="BOM缺失",
        issue_level="medium",
        source_system="scheduler",
        biz_key="123",
        order_line_id=123,
        issue_title="新标题",
        issue_detail="新说明",
    )
    await db_session.commit()

    assert second.id == first.id
    assert second.issue_title == "新标题"
    assert second.issue_detail == "新说明"


@pytest.mark.asyncio
async def test_upsert_open_issue_reuses_issue_when_source_system_only_differs_by_blank(db_session):
    repo = DataIssueRepo(db_session)
    first = await repo.upsert_open_issue(
        issue_type="同步异常",
        issue_level="high",
        source_system=None,
        biz_key="sync_job:sales_plan",
        order_line_id=None,
        issue_title="旧标题",
        issue_detail="旧说明",
    )
    await db_session.flush()

    second = await repo.upsert_open_issue(
        issue_type="同步异常",
        issue_level="medium",
        source_system="   ",
        biz_key="sync_job:sales_plan",
        order_line_id=None,
        issue_title="旧标题",
        issue_detail="新说明",
    )
    await db_session.commit()

    assert second.id == first.id
    assert second.source_system is None
    assert second.issue_title == "旧标题"


@pytest.mark.asyncio
async def test_upsert_open_issue_dedupes_historical_duplicate_open_issues(db_session):
    repo = DataIssueRepo(db_session)
    db_session.add_all(
        [
            DataIssueRecord(
                issue_type="BOM缺失",
                issue_level="high",
                source_system="scheduler",
                biz_key="321",
                order_line_id=321,
                issue_title="旧标题1",
                issue_detail="旧说明1",
                status="open",
            ),
            DataIssueRecord(
                issue_type="BOM缺失",
                issue_level="high",
                source_system="scheduler",
                biz_key="321",
                order_line_id=321,
                issue_title="旧标题2",
                issue_detail="旧说明2",
                status="open",
            ),
        ]
    )
    await db_session.commit()

    latest = await repo.upsert_open_issue(
        issue_type="BOM缺失",
        issue_level="medium",
        source_system="scheduler",
        biz_key="321",
        order_line_id=321,
        issue_title="新标题",
        issue_detail="新说明",
    )
    await db_session.commit()

    rows = (await repo.list_all())
    open_rows = [row for row in rows if row.status == "open"]
    resolved_rows = [row for row in rows if row.status == "resolved"]

    assert len(open_rows) == 1
    assert open_rows[0].id == latest.id
    assert open_rows[0].issue_title == "新标题"
    assert len(resolved_rows) == 1
    assert resolved_rows[0].remark == f"auto-deduped into open issue {latest.id}"
