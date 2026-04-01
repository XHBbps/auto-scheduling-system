import pytest
from decimal import Decimal
from app.repository.machine_schedule_result_repo import MachineScheduleResultRepo


@pytest.mark.asyncio
async def test_upsert_by_order_line_id(db_session):
    repo = MachineScheduleResultRepo(db_session)
    row = await repo.upsert_by_order_line_id(
        order_line_id=101,
        data={
            "contract_no": "HT001",
            "schedule_status": "scheduled",
            "machine_cycle_days": Decimal("20"),
            "run_batch_no": "SCH001",
        }
    )
    await db_session.commit()
    assert row.id is not None
    assert row.order_line_id == 101

    # Upsert again — should update
    row2 = await repo.upsert_by_order_line_id(
        order_line_id=101,
        data={"schedule_status": "scheduled", "run_batch_no": "SCH002"}
    )
    await db_session.commit()
    assert row2.id == row.id
    assert row2.run_batch_no == "SCH002"
