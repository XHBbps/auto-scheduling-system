
import logging
from datetime import datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.integration.feishu_client import FeishuClient
from app.integration.feishu_field_maps import (
    extract_feishu_number,
    extract_feishu_text,
    extract_feishu_timestamp_ms,
)
from app.models.machine_cycle_history import MachineCycleHistorySrc
from app.models.sync_job_log import SyncJobLog
from app.repository.machine_cycle_history_repo import MachineCycleHistoryRepo
from app.sync.sync_support_utils import SyncResult, finish_sync_job, start_sync_job

logger = logging.getLogger(__name__)

FIELD_ORDER_NO = "订单编号"
FIELD_DETAIL_ID = "明细ID"
FIELD_MACHINE_MATERIAL_NO = "明细-物料编号"
FIELD_DRAWING_RELEASE_DATE = "发图时间（研究所）"
FIELD_MACHINE_MODEL = "明细-产品型号"
FIELD_PRODUCT_SERIES = "产品大系列"
FIELD_ORDER_QTY = "明细-数量"
FIELD_INSPECTION_DATE = "报检时间"
FIELD_CUSTOM_NO = "定制编号"
FIELD_CUSTOMER_NAME = "客户名称"
FIELD_CONTRACT_NO = "合同编号"
FIELD_BUSINESS_GROUP = "事业群"
FIELD_ORDER_TYPE = "订单类型"
FIELD_LAST_MODIFIED_TIME = "最后更新时间"


def _ms_to_datetime(ms: int | None) -> datetime | None:
    if ms is None:
        return None
    try:
        return datetime.fromtimestamp(ms / 1000)
    except (OSError, ValueError):
        return None


class ResearchSyncService:
    def __init__(
        self,
        session: AsyncSession,
        client: FeishuClient,
        app_token: str,
        table_id: str,
    ):
        self.session = session
        self.client = client
        self.app_token = app_token
        self.table_id = table_id
        self.repo = MachineCycleHistoryRepo(session)
        self.last_job = None
        self._touched_product_models: set[str] = set()

    async def sync(
        self,
        last_sync_ms: int | None = None,
        order_no_filter: str | None = None,
        job: SyncJobLog | None = None,
    ) -> SyncResult:
        result = SyncResult()
        owns_job = job is None
        if owns_job:
            job = await start_sync_job(self.session, "research", "feishu")
            await self.session.commit()
        self.last_job = job
        self._touched_product_models.clear()
        page_token = None

        while True:
            try:
                items, has_more, page_token, total = await self.client.search_records(
                    app_token=self.app_token,
                    table_id=self.table_id,
                    page_token=page_token if page_token else None,
                )
            except Exception as exc:
                logger.error("Feishu research fetch failed: %s", exc)
                result.record_fail()
                break

            for item in items:
                try:
                    if not self._should_process_record(item, last_sync_ms, order_no_filter):
                        continue
                    await self._process_record(item, result)
                except Exception as exc:
                    logger.error("Research record process failed: %s", exc)
                    result.record_fail()

            if not has_more:
                break

        await finish_sync_job(self.session, job, result)
        return result

    async def update_job_message(self, message: str):
        if not self.last_job:
            return
        self.last_job.message = message
        await self.session.flush()

    def get_touched_product_models(self) -> list[str]:
        return sorted(self._touched_product_models)

    def _should_process_record(
        self,
        item: dict,
        last_sync_ms: int | None,
        order_no: str | None,
    ) -> bool:
        fields = item.get("fields", {})
        material_no = extract_feishu_text(fields, FIELD_MACHINE_MATERIAL_NO)
        if not material_no:
            return False

        if last_sync_ms:
            modified_ms = extract_feishu_timestamp_ms(fields, FIELD_LAST_MODIFIED_TIME)
            if modified_ms is None or modified_ms <= last_sync_ms:
                return False

        if order_no:
            current_order_no = extract_feishu_text(fields, FIELD_ORDER_NO)
            if current_order_no != order_no:
                return False

        return True

    async def _process_record(self, item: dict, result: SyncResult):
        fields = item.get("fields", {})
        detail_id = extract_feishu_text(fields, FIELD_DETAIL_ID)
        material_no = extract_feishu_text(fields, FIELD_MACHINE_MATERIAL_NO)
        if not material_no:
            return
        if not detail_id:
            result.record_fail()
            result.record_issue()
            return

        drawing_date = _ms_to_datetime(extract_feishu_timestamp_ms(fields, FIELD_DRAWING_RELEASE_DATE))
        inspection_date = _ms_to_datetime(extract_feishu_timestamp_ms(fields, FIELD_INSPECTION_DATE))
        cycle_days = None
        if drawing_date and inspection_date:
            delta = inspection_date - drawing_date
            cycle_days = Decimal(str(delta.days))

        order_qty_raw = extract_feishu_number(fields, FIELD_ORDER_QTY)
        order_qty = Decimal(str(order_qty_raw)) if order_qty_raw is not None else Decimal("1")
        machine_model = extract_feishu_text(fields, FIELD_MACHINE_MODEL) or ""
        if machine_model:
            self._touched_product_models.add(machine_model)

        data = {
            "machine_material_no": material_no,
            "machine_model": machine_model,
            "product_series": extract_feishu_text(fields, FIELD_PRODUCT_SERIES),
            "order_qty": order_qty,
            "drawing_release_date": drawing_date,
            "inspection_date": inspection_date,
            "custom_no": extract_feishu_text(fields, FIELD_CUSTOM_NO),
            "customer_name": extract_feishu_text(fields, FIELD_CUSTOMER_NAME),
            "contract_no": extract_feishu_text(fields, FIELD_CONTRACT_NO),
            "order_no": extract_feishu_text(fields, FIELD_ORDER_NO),
            "business_group": extract_feishu_text(fields, FIELD_BUSINESS_GROUP),
            "order_type": extract_feishu_text(fields, FIELD_ORDER_TYPE),
            "cycle_days": cycle_days,
        }

        stmt = select(MachineCycleHistorySrc).where(MachineCycleHistorySrc.detail_id == detail_id)
        existing = (await self.session.execute(stmt)).scalar_one_or_none()
        await self.repo.upsert_by_detail_id(detail_id, data)

        if existing:
            result.record_update()
        else:
            result.record_insert()
