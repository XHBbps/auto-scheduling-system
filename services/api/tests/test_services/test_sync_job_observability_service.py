from app.services.sync_job_observability_service import parse_sync_job_progress


def test_parse_sync_job_progress_supports_part_cycle_baseline_rebuild_message():
    progress = parse_sync_job_progress(
        "零件周期基准重建完成：符合条件 8 组；提升 5 组；落库 4 组；手工保护 1 组；停用 2 组；刷新快照 9 条。"
    )

    assert progress is not None
    assert progress["kind"] == "part_cycle_baseline_rebuild"
    assert progress["eligible_groups"] == 8
    assert progress["promoted_groups"] == 5
    assert progress["persisted_groups"] == 4
    assert progress["manual_protected_groups"] == 1
    assert progress["deactivated_groups"] == 2
    assert progress["snapshot_refreshed"] == 9


def test_parse_sync_job_progress_supports_failure_kind_and_stage():
    progress = parse_sync_job_progress(
        "task_id=17; task_type=sales_plan_sync; stage=execute_task; "
        "failure_kind=external_api_failed; error=guandata timeout"
    )

    assert progress is not None
    assert progress["kind"] == "generic"
    assert progress["task_id"] == 17
    assert progress["task_type"] == "sales_plan_sync"
    assert progress["failure_stage"] == "execute_task"
    assert progress["failure_kind"] == "external_api_failed"
