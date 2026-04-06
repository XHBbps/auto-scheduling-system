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
from app.models.production_order import ProductionOrderHistorySrc
from app.models.sync_job_log import SyncJobLog
from app.repository.production_order_repo import ProductionOrderRepo
from app.sync.sync_support_utils import SyncResult, finish_sync_job, start_sync_job

logger = logging.getLogger(__name__)


def _ms_to_datetime(ms: int | None) -> datetime | None:
    if ms is None:
        return None
    try:
        return datetime.fromtimestamp(ms / 1000)
    except (OSError, ValueError):
        return None


class ProductionOrderSyncService:
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
        self.repo = ProductionOrderRepo(session)
        self._seen_order_nos: set[str] = set()
        self._has_fetch_error: bool = False

    @property
    def has_fetch_error(self) -> bool:
        return self._has_fetch_error

    async def sync(
        self,
        last_sync_ms: int | None = None,
        job: SyncJobLog | None = None,
    ) -> SyncResult:
        result = SyncResult()
        owns_job = job is None
        if owns_job:
            job = await start_sync_job(self.session, "production_order", "feishu")
            await self.session.commit()
        self._seen_order_nos.clear()
        self._has_fetch_error = False

        page_token = None
        while True:
            try:
                items, has_more, page_token, _total = await self.client.search_records(
                    app_token=self.app_token,
                    table_id=self.table_id,
                    page_token=page_token if page_token else None,
                )
            except Exception as e:
                logger.error(f"Feishu production order fetch failed: {e}")
                result.record_fail()
                self._has_fetch_error = True
                break

            for item in items:
                try:
                    if not self._should_process_record(item, last_sync_ms):
                        continue
                    await self._process_record(item, result)
                except Exception as e:
                    logger.error(f"Production order process failed: {e}")
                    result.record_fail()

            if not has_more:
                break

        await finish_sync_job(self.session, job, result)
        return result

    def _should_process_record(self, item: dict, last_sync_ms: int | None) -> bool:
        if not last_sync_ms:
            return True
        fields = item.get("fields", {})
        modified_ms = extract_feishu_timestamp_ms(fields, "最后更新时间")
        return modified_ms is not None and modified_ms > last_sync_ms

    async def _process_record(self, item: dict, result: SyncResult):
        fields = item.get("fields", {})
        order_no = extract_feishu_text(fields, "生产订单号")
        if not order_no:
            result.record_fail()
            return

        # Check for duplicate in this batch
        if order_no in self._seen_order_nos:
            result.record_issue()
            logger.warning(f"Duplicate production order: {order_no}")
        self._seen_order_nos.add(order_no)

        qty_raw = extract_feishu_number(fields, "订货数量")

        data = {
            "material_no": extract_feishu_text(fields, "物料号"),
            "material_desc": extract_feishu_text(fields, "物料描述"),
            "machine_model": extract_feishu_text(fields, "机床型号"),
            "plant": extract_feishu_text(fields, "生产工厂"),
            "processing_dept": fields.get("加工部门")
            if isinstance(fields.get("加工部门"), str)
            else extract_feishu_text(fields, "加工部门"),
            "start_time_actual": _ms_to_datetime(extract_feishu_timestamp_ms(fields, "投产时间")),
            "finish_time_actual": _ms_to_datetime(extract_feishu_timestamp_ms(fields, "完工时间")),
            "production_qty": Decimal(str(qty_raw)) if qty_raw is not None else None,
            "order_status": fields.get("生产订单状态")
            if isinstance(fields.get("生产订单状态"), str)
            else extract_feishu_text(fields, "生产订单状态"),
            "sales_order_no": extract_feishu_text(fields, "销售订单号"),
            "created_time_src": _ms_to_datetime(extract_feishu_timestamp_ms(fields, "创建时间")),
            "last_modified_time_src": _ms_to_datetime(extract_feishu_timestamp_ms(fields, "最后更新时间")),
        }

        # Check if exists
        stmt = select(ProductionOrderHistorySrc).where(ProductionOrderHistorySrc.production_order_no == order_no)
        existing = (await self.session.execute(stmt)).scalar_one_or_none()

        await self.repo.upsert_by_order_no(order_no, data)

        if existing:
            result.record_update()
        else:
            result.record_insert()
