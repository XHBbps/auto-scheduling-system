import pytest

from app.models.machine_schedule_result import MachineScheduleResult
from app.models.order_schedule_snapshot import OrderScheduleSnapshot
from app.repository.order_schedule_snapshot_repo import OrderScheduleSnapshotRepo


@pytest.mark.asyncio
async def test_upsert_loaded_snapshot_rejects_mismatched_machine_schedule_binding(db_session):
    machine_schedule = MachineScheduleResult(
        order_line_id=202,
        schedule_status="scheduled",
    )
    db_session.add(machine_schedule)
    await db_session.flush()

    repo = OrderScheduleSnapshotRepo(db_session)

    with pytest.raises(ValueError, match="does not belong"):
        await repo.upsert_by_order_line_id(
            order_line_id=101,
            data={
                "schedule_status": "scheduled",
                "machine_schedule_id": machine_schedule.id,
            },
        )


@pytest.mark.asyncio
async def test_upsert_loaded_snapshot_accepts_matching_machine_schedule_binding(db_session):
    machine_schedule = MachineScheduleResult(
        order_line_id=303,
        schedule_status="scheduled",
    )
    db_session.add(machine_schedule)
    await db_session.flush()

    repo = OrderScheduleSnapshotRepo(db_session)
    snapshot = await repo.upsert_by_order_line_id(
        order_line_id=303,
        data={
            "schedule_status": "scheduled",
            "machine_schedule_id": machine_schedule.id,
        },
    )
    await db_session.commit()

    assert snapshot.order_line_id == 303
    assert snapshot.machine_schedule_id == machine_schedule.id


@pytest.mark.asyncio
async def test_upsert_loaded_snapshot_clears_machine_schedule_for_non_scheduled_status(db_session):
    machine_schedule = MachineScheduleResult(
        order_line_id=404,
        schedule_status="scheduled",
    )
    db_session.add(machine_schedule)
    await db_session.flush()

    repo = OrderScheduleSnapshotRepo(db_session)
    snapshot = await repo.upsert_by_order_line_id(
        order_line_id=404,
        data={
            "schedule_status": "missing_bom",
            "machine_schedule_id": machine_schedule.id,
        },
    )
    await db_session.commit()

    assert snapshot.order_line_id == 404
    assert snapshot.schedule_status == "missing_bom"
    assert snapshot.machine_schedule_id is None


def test_order_schedule_snapshot_model_clears_machine_schedule_for_non_scheduled_status():
    snapshot = OrderScheduleSnapshot(
        order_line_id=505,
        schedule_status="missing_bom",
        machine_schedule_id=999,
    )

    assert snapshot.schedule_status == "missing_bom"
    assert snapshot.machine_schedule_id is None
