import logging
from types import SimpleNamespace

import pytest

from app.services.schedule_export_service import ExportService


@pytest.mark.asyncio
async def test_export_machine_schedules_logs_success(db_session, monkeypatch, caplog):
    service = ExportService(db_session)

    async def fake_ensure_ready():
        return None

    def fake_write_machine_csv(buffer, filters):
        buffer.write(b"ok")
        buffer.seek(0)
        return 3

    monkeypatch.setattr(service, "_ensure_ready", fake_ensure_ready)
    monkeypatch.setattr(service, "_write_machine_csv", fake_write_machine_csv)

    with caplog.at_level(logging.INFO):
        buffer, _, content_type = await service.export_machine_schedules(
            export_format="csv",
            contract_no="HT001",
            plant="1000",
        )

    assert content_type == "text/csv; charset=utf-8"
    assert buffer.read() == b"ok"
    assert "Machine schedule export started" in caplog.text
    assert "Machine schedule export finished" in caplog.text
    assert "row_count=3" in caplog.text
    assert "contract_no" in caplog.text


@pytest.mark.asyncio
async def test_export_part_schedules_logs_failure(db_session, monkeypatch, caplog):
    service = ExportService(db_session)

    async def fake_ensure_ready():
        return None

    def fake_ensure_part_xlsx_within_limit(filters):
        return 12

    def fail_write_part_xlsx(buffer, filters):
        raise RuntimeError("xlsx writer exploded")

    monkeypatch.setattr(service, "_ensure_ready", fake_ensure_ready)
    monkeypatch.setattr(service, "_ensure_part_xlsx_within_limit", fake_ensure_part_xlsx_within_limit)
    monkeypatch.setattr(service, "_write_part_xlsx", fail_write_part_xlsx)

    with caplog.at_level(logging.INFO):
        with pytest.raises(RuntimeError, match="xlsx writer exploded"):
            await service.export_part_schedules(
                export_format="xlsx",
                assembly_name="电控",
            )

    assert "Part schedule export started" in caplog.text
    assert "Part schedule export failed" in caplog.text
    assert "assembly_name" in caplog.text


@pytest.mark.asyncio
async def test_export_machine_schedules_streams_rows_without_cross_loop_errors(db_session, monkeypatch):
    service = ExportService(db_session)

    async def fake_ensure_ready():
        return None

    async def fake_stream_for_export_batches(*, batch_size, **filters):
        yield [
            SimpleNamespace(
                order_line_id=1,
                contract_no='HT001',
                customer_name='Customer',
                product_series='MC',
                product_model='MC1-80',
                product_name='Machine',
                material_no='MAT001',
                plant='1000',
                quantity=1,
                order_type='1',
                order_date=None,
                line_total_amount=None,
                business_group=None,
                custom_no=None,
                sales_person_name=None,
                sales_branch_company=None,
                sales_sub_branch=None,
                order_no='SO001',
                sap_code=None,
                sap_line_no=None,
                confirmed_delivery_date=None,
                drawing_released=True,
                drawing_release_date=None,
                custom_requirement=None,
                review_comment=None,
                trigger_date=None,
                schedule_status='scheduled',
                planned_start_date=None,
                planned_end_date=None,
                machine_cycle_days=None,
                machine_assembly_days=None,
                warning_level='normal',
            )
        ]

    monkeypatch.setattr(service, '_ensure_ready', fake_ensure_ready)
    monkeypatch.setattr(service.snapshot_repo, 'stream_for_export_batches', fake_stream_for_export_batches)

    buffer, _, content_type = await service.export_machine_schedules(export_format='csv', order_line_id=1)

    payload = buffer.read().decode('utf-8-sig')
    assert content_type == 'text/csv; charset=utf-8'
    assert 'HT001' in payload
    assert len([line for line in payload.splitlines() if line.strip()]) == 2


@pytest.mark.asyncio
async def test_export_part_schedules_streams_rows_without_cross_loop_errors(db_session, monkeypatch):
    service = ExportService(db_session)

    async def fake_ensure_ready():
        return None

    async def fake_stream_for_export_rows(*, batch_size, snapshot_sort_field=None, snapshot_sort_order=None, part_sort_field=None, part_sort_order=None, **filters):
        yield [
            (
                SimpleNamespace(
                    order_line_id=1,
                    contract_no='HT001',
                    product_model='MC1-80',
                    plant='1000',
                    order_no='SO001',
                ),
                SimpleNamespace(
                    assembly_name='??',
                    parent_material_no='ASM001',
                    parent_name='????',
                    node_level=1,
                    bom_path='??/??',
                    production_sequence=1,
                    assembly_time_days=1,
                    part_material_no='P001',
                    part_name='Part-1',
                    is_key_part=True,
                    part_cycle_days=2,
                    key_part_material_no='P001',
                    key_part_name='Part-1',
                    key_part_raw_material_desc='Steel',
                    key_part_cycle_days=2,
                    planned_start_date=None,
                    planned_end_date=None,
                ),
            )
        ]

    monkeypatch.setattr(service, '_ensure_ready', fake_ensure_ready)
    monkeypatch.setattr(service.psr_repo, 'stream_for_export_rows', fake_stream_for_export_rows)

    buffer, _, content_type = await service.export_part_schedules(export_format='csv', order_line_id=1)

    payload = buffer.read().decode('utf-8-sig')
    assert content_type == 'text/csv; charset=utf-8'
    assert 'HT001' in payload
    assert 'P001' in payload
    assert len([line for line in payload.splitlines() if line.strip()]) == 2
