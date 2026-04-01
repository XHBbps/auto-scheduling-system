
import logging
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from sqlalchemy import and_, select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession

from app.integration.guandata_client import GuandataClient
from app.models.sales_plan import SalesPlanOrderLineSrc
from app.models.sync_job_log import SyncJobLog
from app.repository.sales_plan_repo import SalesPlanRepo
from app.services.schedule_snapshot_refresh_service import ScheduleSnapshotRefreshService
from app.sync.sales_plan_schedule_refresh_service import SalesPlanScheduleRefreshService
from app.sync.sync_support_utils import SyncResult, finish_sync_job, start_sync_job

logger = logging.getLogger(__name__)

_ORDER_TYPE_MAP = {
    "常规": "1",
    "选配": "2",
    "定制": "3",
    "1": "1",
    "2": "2",
    "3": "3",
}
_PAGE_SIZE = 200
_SCHEDULE_REFRESH_FIELDS = (
    "confirmed_delivery_date",
    "drawing_released",
    "drawing_release_date",
    "material_no",
    "product_model",
    "quantity",
)


def _parse_date(val: str | None) -> datetime | None:
    if not val:
        return None
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y/%m/%d"):
        try:
            return datetime.strptime(val, fmt)
        except ValueError:
            continue
    return None


def _parse_decimal(val: str | None) -> Decimal | None:
    if not val:
        return None
    try:
        return Decimal(str(val))
    except (InvalidOperation, ValueError):
        return None


def _parse_bool(val: str | None) -> bool | None:
    if val is None:
        return None
    return str(val).lower() == "true"


def _normalize_order_type(val: Any) -> str | None:
    if val is None:
        return None
    normalized = str(val).strip()
    if not normalized:
        return None
    return _ORDER_TYPE_MAP.get(normalized, normalized)


class SalesPlanSyncService:
    def __init__(self, session: AsyncSession, client: GuandataClient):
        self.session = session
        self.client = client
        self.repo = SalesPlanRepo(session)
        self.schedule_refresh_service = SalesPlanScheduleRefreshService(session)
        self.snapshot_refresh_service = ScheduleSnapshotRefreshService(session)
        self._touched_order_line_ids: set[int] = set()
        self._pending_snapshot_refresh_ids: set[int] = set()

    async def sync(
        self,
        filters: dict[str, Any] | None = None,
        job: SyncJobLog | None = None,
    ) -> SyncResult:
        result = SyncResult()
        self._touched_order_line_ids.clear()
        self._pending_snapshot_refresh_ids.clear()
        owns_job = job is None
        if owns_job:
            job = await start_sync_job(self.session, "sales_plan", "guandata")
            await self.session.commit()

        offset = 0
        while True:
            try:
                records, total = await self.client.fetch_sales_page(
                    offset=offset, limit=_PAGE_SIZE, filters=filters
                )
            except Exception as exc:
                logger.error("Guandata fetch failed at offset %s: %s", offset, exc)
                result.record_fail()
                break

            if not records:
                break

            await self._upsert_records(records, result)

            offset += len(records)
            if total > 0 and offset >= total:
                break
            if len(records) < _PAGE_SIZE:
                break

        await self._flush_pending_snapshot_refreshes()
        await finish_sync_job(self.session, job, result, f"synced {result.success_count} records")
        return result

    def get_touched_order_line_ids(self) -> list[int]:
        return sorted(self._touched_order_line_ids)

    async def _upsert_records(self, records: list[dict[str, Any]], result: SyncResult) -> None:
        existing_map = await self._prefetch_existing_rows(records)
        for raw in records:
            try:
                await self._upsert_record(raw, result, existing_map=existing_map)
            except Exception as exc:
                logger.error("Upsert failed for %s: %s", raw.get("sap_code"), exc)
                result.record_fail()
                result.record_issue()

    async def _upsert_record(
        self,
        raw: dict[str, Any],
        result: SyncResult,
        *,
        existing_map: dict[tuple[str, str], SalesPlanOrderLineSrc],
    ):
        sap_code = raw.get("sap_code")
        sap_line_no = raw.get("sap_line_no")
        if not sap_code or not sap_line_no:
            result.record_fail()
            return

        key = (sap_code, sap_line_no)
        existing = existing_map.get(key)

        data = {
            "crm_no": raw.get("crm_no"),
            "contract_no": raw.get("contract_no"),
            "customer_name": raw.get("customer_name"),
            "custom_no": raw.get("custom_no"),
            "sales_person_name": raw.get("sales_person_name"),
            "sales_person_job_no": raw.get("sales_person_job_no"),
            "product_series": raw.get("product_series"),
            "product_model": raw.get("product_model"),
            "product_name": raw.get("product_name"),
            "material_no": raw.get("material_no"),
            "quantity": _parse_decimal(raw.get("quantity")),
            "contract_unit_price": _parse_decimal(raw.get("contract_unit_price")),
            "line_total_amount": _parse_decimal(raw.get("line_total_amount")),
            "confirmed_delivery_date": _parse_date(raw.get("confirmed_delivery_date")),
            "delivery_date": _parse_date(raw.get("delivery_date")),
            "order_type": _normalize_order_type(raw.get("order_type")),
            "is_automation_project": _parse_bool(raw.get("is_automation_project")),
            "business_group": raw.get("business_group"),
            "order_date": _parse_date(raw.get("order_date")),
            "sales_branch_company": raw.get("sales_branch_company"),
            "sales_sub_branch": raw.get("sales_sub_branch"),
            "oa_flow_id": raw.get("oa_flow_id"),
            "operator_name": raw.get("operator_name"),
            "operator_job_no": raw.get("operator_job_no"),
            "custom_requirement": raw.get("custom_requirement"),
            "review_comment": raw.get("review_comment"),
            "delivery_plant": raw.get("delivery_plant"),
            "detail_id": raw.get("detail_id"),
            "order_no": raw.get("order_no"),
        }

        row_changed = self._is_row_changed(existing, data)
        changed_schedule_fields = self._get_changed_schedule_fields(existing, data)
        if existing:
            for field_name, value in data.items():
                setattr(existing, field_name, value)
            entity = existing
        else:
            entity = SalesPlanOrderLineSrc(sap_code=sap_code, sap_line_no=sap_line_no, **data)
            self.session.add(entity)
        await self.session.flush()
        existing_map[key] = entity
        if entity.id is not None:
            self._touched_order_line_ids.add(int(entity.id))

        if existing and changed_schedule_fields:
            await self.schedule_refresh_service.refresh_if_scheduled(
                order_line_id=entity.id,
                changed_fields=changed_schedule_fields,
            )
        elif row_changed and entity.id is not None:
            self._pending_snapshot_refresh_ids.add(int(entity.id))

        if existing:
            result.record_update()
        else:
            result.record_insert()

    async def _prefetch_existing_rows(
        self,
        records: list[dict[str, Any]],
    ) -> dict[tuple[str, str], SalesPlanOrderLineSrc]:
        keys = sorted(
            {
                (str(raw.get("sap_code")), str(raw.get("sap_line_no")))
                for raw in records
                if raw.get("sap_code") and raw.get("sap_line_no")
            }
        )
        if not keys:
            return {}

        stmt = select(SalesPlanOrderLineSrc).where(
            tuple_(
                SalesPlanOrderLineSrc.sap_code,
                SalesPlanOrderLineSrc.sap_line_no,
            ).in_(keys)
        )
        rows = (await self.session.execute(stmt)).scalars().all()
        return {(row.sap_code, row.sap_line_no): row for row in rows}

    async def _flush_pending_snapshot_refreshes(self) -> None:
        if not self._pending_snapshot_refresh_ids:
            return
        await self.snapshot_refresh_service.refresh_batch(
            sorted(self._pending_snapshot_refresh_ids),
            source="sales_plan_sync",
            reason="sales_plan_batch_upsert",
        )
        self._pending_snapshot_refresh_ids.clear()

    @staticmethod
    def _is_row_changed(
        existing: SalesPlanOrderLineSrc | None,
        data: dict[str, Any],
    ) -> bool:
        if not existing:
            return True
        return any(getattr(existing, field) != value for field, value in data.items())

    @staticmethod
    def _get_changed_schedule_fields(
        existing: SalesPlanOrderLineSrc | None,
        data: dict[str, Any],
    ) -> list[str]:
        if not existing:
            return []

        changed_fields: list[str] = []
        for field in _SCHEDULE_REFRESH_FIELDS:
            if field not in data:
                continue
            if getattr(existing, field) != data.get(field):
                changed_fields.append(field)
        return changed_fields
