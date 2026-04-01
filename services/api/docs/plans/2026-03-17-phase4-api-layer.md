# Phase 4: API Layer Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add REST API endpoints for scheduling queries, data exports, manual sync/schedule triggers, parameter maintenance, and issue management.

**Architecture:** FastAPI routers organized by domain (schedules, exports, admin). Services coordinate existing repos and sync/scheduler modules. Global exception handler translates BizException to ApiResponse.

**Tech Stack:** FastAPI routers, Pydantic v2 schemas, openpyxl for Excel export, existing SQLAlchemy async repos.

---

## File Structure

### New files to create:
- `app/routers/__init__.py` — Router package init
- `app/routers/schedules.py` — Schedule query endpoints (list + detail)
- `app/routers/issues.py` — Issue query endpoint
- `app/routers/exports.py` — Excel export endpoints
- `app/routers/admin_sync.py` — Manual sync trigger endpoints
- `app/routers/admin_schedule.py` — Manual schedule run endpoint
- `app/routers/admin_assembly_time.py` — Assembly time CRUD
- `app/routers/admin_work_calendar.py` — Work calendar CRUD
- `app/routers/admin_issues.py` — Issue resolve/ignore
- `app/schemas/__init__.py` — Schemas package init
- `app/schemas/schedule_schemas.py` — Pydantic schemas for schedule endpoints
- `app/schemas/issue_schemas.py` — Pydantic schemas for issue endpoints
- `app/schemas/admin_schemas.py` — Pydantic schemas for admin endpoints
- `app/schemas/common.py` — Shared pagination schema
- `app/services/__init__.py` — Services package init
- `app/services/schedule_query_service.py` — List/detail query logic
- `app/services/export_service.py` — Excel generation logic
- `tests/test_api/__init__.py` — Test package init
- `tests/test_api/test_schedules_api.py` — Tests for schedule endpoints
- `tests/test_api/test_issues_api.py` — Tests for issue endpoints
- `tests/test_api/test_exports_api.py` — Tests for export endpoints
- `tests/test_api/test_admin_sync_api.py` — Tests for admin sync endpoints
- `tests/test_api/test_admin_schedule_api.py` — Tests for admin schedule endpoints
- `tests/test_api/test_admin_assembly_time_api.py` — Tests for assembly time endpoints
- `tests/test_api/test_admin_work_calendar_api.py` — Tests for work calendar endpoints
- `tests/test_api/test_admin_issues_api.py` — Tests for issue management endpoints

### Files to modify:
- `app/main.py` — Register routers, add global exception handler, CORS
- `app/repository/machine_schedule_result_repo.py` — Enhance paginate with filters
- `tests/conftest.py` — Add `app_client` fixture for API testing

---

### Task 1: Shared Schemas & Pagination

**Files:**
- Create: `app/schemas/__init__.py`
- Create: `app/schemas/common.py`

- [ ] **Step 1: Create schemas package init**

```python
# app/schemas/__init__.py
```

- [ ] **Step 2: Create common pagination schema**

```python
# app/schemas/common.py
from typing import Any
from pydantic import BaseModel


class PageParams(BaseModel):
    page_no: int = 1
    page_size: int = 20


class PageResult(BaseModel):
    total: int
    page_no: int
    page_size: int
    items: list[Any]
```

---

### Task 2: Schedule Schemas

**Files:**
- Create: `app/schemas/schedule_schemas.py`

- [ ] **Step 1: Create schedule schemas**

```python
# app/schemas/schedule_schemas.py
from datetime import datetime
from decimal import Decimal
from typing import Optional, Any
from pydantic import BaseModel


class ScheduleListFilter(BaseModel):
    page_no: int = 1
    page_size: int = 20
    contract_no: Optional[str] = None
    customer_name: Optional[str] = None
    product_series: Optional[str] = None
    product_model: Optional[str] = None
    order_no: Optional[str] = None
    schedule_status: Optional[str] = None
    warning_level: Optional[str] = None
    drawing_released: Optional[bool] = None
    date_from: Optional[str] = None
    date_to: Optional[str] = None


class ScheduleListItem(BaseModel):
    order_line_id: int
    contract_no: Optional[str] = None
    customer_name: Optional[str] = None
    product_series: Optional[str] = None
    product_model: Optional[str] = None
    product_name: Optional[str] = None
    quantity: Optional[Decimal] = None
    order_no: Optional[str] = None
    confirmed_delivery_date: Optional[datetime] = None
    drawing_released: Optional[bool] = None
    drawing_release_date: Optional[datetime] = None
    trigger_date: Optional[datetime] = None
    planned_start_date: Optional[datetime] = None
    planned_end_date: Optional[datetime] = None
    warning_level: Optional[str] = None
    schedule_status: Optional[str] = None
    default_flags: Optional[dict[str, Any]] = None

    model_config = {"from_attributes": True}


class PartScheduleItem(BaseModel):
    assembly_name: str
    production_sequence: int
    assembly_time_days: Optional[Decimal] = None
    key_part_material_no: Optional[str] = None
    key_part_name: Optional[str] = None
    key_part_raw_material_desc: Optional[str] = None
    key_part_cycle_days: Optional[Decimal] = None
    planned_start_date: Optional[datetime] = None
    planned_end_date: Optional[datetime] = None
    default_flags: Optional[dict[str, Any]] = None

    model_config = {"from_attributes": True}


class IssueItem(BaseModel):
    id: int
    issue_type: str
    issue_level: Optional[str] = None
    source_system: Optional[str] = None
    biz_key: Optional[str] = None
    issue_title: str
    issue_detail: Optional[str] = None
    status: str
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ScheduleDetailResponse(BaseModel):
    machine_schedule: ScheduleListItem
    part_schedules: list[PartScheduleItem]
    issues: list[IssueItem]
```

---

### Task 3: Admin Schemas

**Files:**
- Create: `app/schemas/admin_schemas.py`
- Create: `app/schemas/issue_schemas.py`

- [ ] **Step 1: Create admin schemas**

```python
# app/schemas/admin_schemas.py
from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel


class SyncSalesPlanRequest(BaseModel):
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None


class SyncBomRequest(BaseModel):
    order_line_ids: list[int]


class SyncResearchRequest(BaseModel):
    mode: str = "increment"
    order_no: Optional[str] = None


class ScheduleRunRequest(BaseModel):
    order_line_ids: list[int]
    force_rebuild: bool = True


class AssemblyTimeRequest(BaseModel):
    machine_model: str
    product_series: Optional[str] = None
    assembly_name: str
    assembly_time_days: Decimal
    is_final_assembly: bool = False
    production_sequence: int
    is_default: bool = False
    remark: Optional[str] = None


class WorkCalendarItem(BaseModel):
    calendar_date: date
    is_workday: bool
    remark: Optional[str] = None


class WorkCalendarBatchRequest(BaseModel):
    items: list[WorkCalendarItem]
```

- [ ] **Step 2: Create issue schemas**

```python
# app/schemas/issue_schemas.py
from typing import Optional
from pydantic import BaseModel


class IssueListFilter(BaseModel):
    page_no: int = 1
    page_size: int = 20
    issue_type: Optional[str] = None
    status: Optional[str] = None
    biz_key: Optional[str] = None
    source_system: Optional[str] = None


class IssueActionRequest(BaseModel):
    remark: Optional[str] = None
```

---

### Task 4: Enhance MachineScheduleResultRepo with filters

**Files:**
- Modify: `app/repository/machine_schedule_result_repo.py`

- [ ] **Step 1: Add filter support to paginate method**

Replace the existing `paginate` method with a version that supports all filter parameters from the API design (contract_no, customer_name, product_series, product_model, order_no, schedule_status, warning_level, drawing_released, date_from, date_to).

```python
async def paginate(
    self, page_no: int = 1, page_size: int = 20, **filters: Any
) -> tuple[Sequence[MachineScheduleResult], int]:
    base = select(MachineScheduleResult)
    count_base = select(func.count()).select_from(MachineScheduleResult)

    conditions = []
    if filters.get("contract_no"):
        conditions.append(MachineScheduleResult.contract_no.ilike(f"%{filters['contract_no']}%"))
    if filters.get("customer_name"):
        conditions.append(MachineScheduleResult.customer_name.ilike(f"%{filters['customer_name']}%"))
    if filters.get("product_series"):
        conditions.append(MachineScheduleResult.product_series == filters["product_series"])
    if filters.get("product_model"):
        conditions.append(MachineScheduleResult.product_model == filters["product_model"])
    if filters.get("order_no"):
        conditions.append(MachineScheduleResult.order_no.ilike(f"%{filters['order_no']}%"))
    if filters.get("schedule_status"):
        conditions.append(MachineScheduleResult.schedule_status == filters["schedule_status"])
    if filters.get("warning_level"):
        conditions.append(MachineScheduleResult.warning_level == filters["warning_level"])
    if filters.get("drawing_released") is not None:
        conditions.append(MachineScheduleResult.drawing_released == filters["drawing_released"])
    if filters.get("date_from"):
        conditions.append(MachineScheduleResult.confirmed_delivery_date >= filters["date_from"])
    if filters.get("date_to"):
        conditions.append(MachineScheduleResult.confirmed_delivery_date <= filters["date_to"])

    if conditions:
        base = base.where(and_(*conditions))
        count_base = count_base.where(and_(*conditions))

    total = (await self.session.execute(count_base)).scalar_one()
    stmt = base.order_by(MachineScheduleResult.confirmed_delivery_date).offset(
        (page_no - 1) * page_size
    ).limit(page_size)
    items = (await self.session.execute(stmt)).scalars().all()
    return items, total
```

---

### Task 5: Schedule Query Service

**Files:**
- Create: `app/services/__init__.py`
- Create: `app/services/schedule_query_service.py`

- [ ] **Step 1: Create services package init**

```python
# app/services/__init__.py
```

- [ ] **Step 2: Create schedule query service**

```python
# app/services/schedule_query_service.py
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession

from app.repository.machine_schedule_result_repo import MachineScheduleResultRepo
from app.repository.part_schedule_result_repo import PartScheduleResultRepo
from app.repository.data_issue_repo import DataIssueRepo


class ScheduleQueryService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.msr_repo = MachineScheduleResultRepo(session)
        self.psr_repo = PartScheduleResultRepo(session)
        self.issue_repo = DataIssueRepo(session)

    async def list_schedules(self, **filters: Any) -> dict[str, Any]:
        page_no = filters.pop("page_no", 1)
        page_size = filters.pop("page_size", 20)
        items, total = await self.msr_repo.paginate(
            page_no=page_no, page_size=page_size, **filters
        )
        return {
            "total": total,
            "page_no": page_no,
            "page_size": page_size,
            "items": items,
        }

    async def get_detail(self, order_line_id: int) -> dict[str, Any] | None:
        msr = await self.msr_repo.find_by_order_line_id(order_line_id)
        if not msr:
            return None
        parts = await self.psr_repo.find_by_order_line_id(order_line_id)
        issues, _ = await self.issue_repo.paginate(
            page_no=1, page_size=100,
            biz_key=str(order_line_id),
        )
        return {
            "machine_schedule": msr,
            "part_schedules": list(parts),
            "issues": list(issues),
        }
```

---

### Task 6: Export Service

**Files:**
- Create: `app/services/export_service.py`

- [ ] **Step 1: Create export service**

```python
# app/services/export_service.py
import io
from datetime import datetime
from typing import Any, Sequence
from openpyxl import Workbook
from sqlalchemy.ext.asyncio import AsyncSession

from app.repository.machine_schedule_result_repo import MachineScheduleResultRepo
from app.repository.part_schedule_result_repo import PartScheduleResultRepo
from app.models.machine_schedule_result import MachineScheduleResult
from app.models.part_schedule_result import PartScheduleResult


class ExportService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.msr_repo = MachineScheduleResultRepo(session)
        self.psr_repo = PartScheduleResultRepo(session)

    async def export_machine_schedules(self, **filters: Any) -> tuple[io.BytesIO, str]:
        filters.pop("page_no", None)
        filters.pop("page_size", None)
        items, _ = await self.msr_repo.paginate(page_no=1, page_size=10000, **filters)
        wb = Workbook()
        ws = wb.active
        ws.title = "整机排产"

        headers = [
            "合同编号", "客户名称", "产品系列", "产品型号", "产品名称",
            "数量", "订单编号", "确认交货期", "发图完成", "发图日期",
            "排产状态", "计划开工日", "计划完工日", "整机周期(天)",
            "总装天数", "预警等级",
        ]
        ws.append(headers)

        for item in items:
            ws.append([
                item.contract_no, item.customer_name, item.product_series,
                item.product_model, item.product_name,
                float(item.quantity) if item.quantity else None,
                item.order_no,
                item.confirmed_delivery_date.strftime("%Y-%m-%d") if item.confirmed_delivery_date else None,
                "是" if item.drawing_released else "否",
                item.drawing_release_date.strftime("%Y-%m-%d") if item.drawing_release_date else None,
                item.schedule_status,
                item.planned_start_date.strftime("%Y-%m-%d") if item.planned_start_date else None,
                item.planned_end_date.strftime("%Y-%m-%d") if item.planned_end_date else None,
                float(item.machine_cycle_days) if item.machine_cycle_days else None,
                float(item.machine_assembly_days) if item.machine_assembly_days else None,
                item.warning_level,
            ])

        buf = io.BytesIO()
        wb.save(buf)
        buf.seek(0)
        filename = f"machine_schedule_{datetime.now().strftime('%Y%m%d%H%M%S')}.xlsx"
        return buf, filename

    async def export_part_schedules(self, **filters: Any) -> tuple[io.BytesIO, str]:
        filters.pop("page_no", None)
        filters.pop("page_size", None)
        machine_items, _ = await self.msr_repo.paginate(page_no=1, page_size=10000, **filters)
        wb = Workbook()
        ws = wb.active
        ws.title = "关键零件排产"

        headers = [
            "合同编号", "产品型号", "订单编号",
            "部装名称", "生产顺序", "装配天数",
            "关键零件料号", "关键零件名称", "关键零件描述",
            "关键零件周期(天)", "计划开工日", "计划完工日",
        ]
        ws.append(headers)

        for machine in machine_items:
            parts = await self.psr_repo.find_by_order_line_id(machine.order_line_id)
            for p in parts:
                ws.append([
                    machine.contract_no, machine.product_model, machine.order_no,
                    p.assembly_name, p.production_sequence,
                    float(p.assembly_time_days) if p.assembly_time_days else None,
                    p.key_part_material_no, p.key_part_name, p.key_part_raw_material_desc,
                    float(p.key_part_cycle_days) if p.key_part_cycle_days else None,
                    p.planned_start_date.strftime("%Y-%m-%d") if p.planned_start_date else None,
                    p.planned_end_date.strftime("%Y-%m-%d") if p.planned_end_date else None,
                ])

        buf = io.BytesIO()
        wb.save(buf)
        buf.seek(0)
        filename = f"part_schedule_{datetime.now().strftime('%Y%m%d%H%M%S')}.xlsx"
        return buf, filename
```

---

### Task 7: App Setup — Global Exception Handler, CORS, Dependency

**Files:**
- Modify: `app/main.py`

- [ ] **Step 1: Update main.py with exception handler, CORS, routers**

```python
# app/main.py
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.common.exceptions import BizException

app = FastAPI(title="自动排产工具", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(BizException)
async def biz_exception_handler(request: Request, exc: BizException):
    return JSONResponse(
        status_code=200,
        content={"code": int(exc.code), "message": exc.message, "data": None},
    )


@app.get("/health")
async def health():
    return {"status": "ok"}


# Register routers — imported after app creation to avoid circular imports
from app.routers import schedules, issues, exports  # noqa: E402
from app.routers import admin_sync, admin_schedule  # noqa: E402
from app.routers import admin_assembly_time, admin_work_calendar, admin_issues  # noqa: E402

app.include_router(schedules.router)
app.include_router(issues.router)
app.include_router(exports.router)
app.include_router(admin_sync.router)
app.include_router(admin_schedule.router)
app.include_router(admin_assembly_time.router)
app.include_router(admin_work_calendar.router)
app.include_router(admin_issues.router)
```

---

### Task 8: Schedule Query Router

**Files:**
- Create: `app/routers/__init__.py`
- Create: `app/routers/schedules.py`

- [ ] **Step 1: Create routers init**

```python
# app/routers/__init__.py
```

- [ ] **Step 2: Create schedules router**

```python
# app/routers/schedules.py
from fastapi import APIRouter, Depends, Query
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.response import ApiResponse
from app.common.exceptions import BizException, ErrorCode
from app.database import get_session
from app.schemas.schedule_schemas import ScheduleListItem, PartScheduleItem, IssueItem
from app.services.schedule_query_service import ScheduleQueryService

router = APIRouter(prefix="/api", tags=["排产查询"])


@router.get("/schedules")
async def list_schedules(
    page_no: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    contract_no: Optional[str] = None,
    customer_name: Optional[str] = None,
    product_series: Optional[str] = None,
    product_model: Optional[str] = None,
    order_no: Optional[str] = None,
    schedule_status: Optional[str] = None,
    warning_level: Optional[str] = None,
    drawing_released: Optional[bool] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    session: AsyncSession = Depends(get_session),
):
    service = ScheduleQueryService(session)
    result = await service.list_schedules(
        page_no=page_no, page_size=page_size,
        contract_no=contract_no, customer_name=customer_name,
        product_series=product_series, product_model=product_model,
        order_no=order_no, schedule_status=schedule_status,
        warning_level=warning_level, drawing_released=drawing_released,
        date_from=date_from, date_to=date_to,
    )
    result["items"] = [
        ScheduleListItem.model_validate(i).model_dump() for i in result["items"]
    ]
    return ApiResponse.ok(data=result)


@router.get("/schedules/{order_line_id}")
async def get_schedule_detail(
    order_line_id: int,
    session: AsyncSession = Depends(get_session),
):
    service = ScheduleQueryService(session)
    detail = await service.get_detail(order_line_id)
    if not detail:
        raise BizException(ErrorCode.NOT_FOUND, f"排产记录不存在: {order_line_id}")
    return ApiResponse.ok(data={
        "machine_schedule": ScheduleListItem.model_validate(
            detail["machine_schedule"]
        ).model_dump(),
        "part_schedules": [
            PartScheduleItem.model_validate(p).model_dump()
            for p in detail["part_schedules"]
        ],
        "issues": [
            IssueItem.model_validate(i).model_dump()
            for i in detail["issues"]
        ],
    })
```

---

### Task 9: Issues Query Router

**Files:**
- Create: `app/routers/issues.py`

- [ ] **Step 1: Create issues router**

```python
# app/routers/issues.py
from fastapi import APIRouter, Depends, Query
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.response import ApiResponse
from app.database import get_session
from app.repository.data_issue_repo import DataIssueRepo
from app.schemas.schedule_schemas import IssueItem

router = APIRouter(prefix="/api", tags=["异常查询"])


@router.get("/issues")
async def list_issues(
    page_no: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    issue_type: Optional[str] = None,
    status: Optional[str] = None,
    biz_key: Optional[str] = None,
    source_system: Optional[str] = None,
    session: AsyncSession = Depends(get_session),
):
    repo = DataIssueRepo(session)
    items, total = await repo.paginate(
        page_no=page_no, page_size=page_size,
        issue_type=issue_type, status=status,
        biz_key=biz_key, source_system=source_system,
    )
    return ApiResponse.ok(data={
        "total": total,
        "page_no": page_no,
        "page_size": page_size,
        "items": [IssueItem.model_validate(i).model_dump() for i in items],
    })
```

---

### Task 10: Export Router

**Files:**
- Create: `app/routers/exports.py`

- [ ] **Step 1: Create exports router**

```python
# app/routers/exports.py
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.services.schedule_export_service import ExportService

router = APIRouter(prefix="/api/exports", tags=["导出"])


@router.get("/machine-schedules")
async def export_machine_schedules(
    contract_no: Optional[str] = None,
    customer_name: Optional[str] = None,
    product_series: Optional[str] = None,
    product_model: Optional[str] = None,
    order_no: Optional[str] = None,
    schedule_status: Optional[str] = None,
    session: AsyncSession = Depends(get_session),
):
    service = ExportService(session)
    buf, filename = await service.export_machine_schedules(
        contract_no=contract_no, customer_name=customer_name,
        product_series=product_series, product_model=product_model,
        order_no=order_no, schedule_status=schedule_status,
    )
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/part-schedules")
async def export_part_schedules(
    contract_no: Optional[str] = None,
    customer_name: Optional[str] = None,
    product_series: Optional[str] = None,
    product_model: Optional[str] = None,
    order_no: Optional[str] = None,
    schedule_status: Optional[str] = None,
    session: AsyncSession = Depends(get_session),
):
    service = ExportService(session)
    buf, filename = await service.export_part_schedules(
        contract_no=contract_no, customer_name=customer_name,
        product_series=product_series, product_model=product_model,
        order_no=order_no, schedule_status=schedule_status,
    )
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
```

---

### Task 11: Admin Sync Router

**Files:**
- Create: `app/routers/admin_sync.py`

- [ ] **Step 1: Create admin sync router**

```python
# app/routers/admin_sync.py
import logging
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.response import ApiResponse
from app.common.exceptions import BizException, ErrorCode
from app.database import get_session
from app.schemas.admin_schemas import SyncSalesPlanRequest, SyncBomRequest, SyncResearchRequest
from app.sync.sales_plan_sync_service import SalesPlanSyncService
from app.sync.bom_sync_service import BomSyncService
from app.sync.production_order_sync_service import ProductionOrderSyncService
from app.sync.research_data_sync_service import ResearchSyncService
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin/sync", tags=["手动同步"])


@router.post("/sales-plan")
async def sync_sales_plan(
    req: SyncSalesPlanRequest,
    session: AsyncSession = Depends(get_session),
):
    try:
        service = SalesPlanSyncService(session, settings)
        result = await service.sync(
            start_time=req.start_time,
            end_time=req.end_time,
        )
        await session.commit()
        return ApiResponse.ok(data={
            "success_count": result.success_count,
            "fail_count": result.fail_count,
            "insert_count": result.insert_count,
            "update_count": result.update_count,
            "issue_count": result.issue_count,
        })
    except Exception as e:
        logger.error(f"Sales plan sync failed: {e}")
        raise BizException(ErrorCode.EXTERNAL_API_FAILED, str(e))


@router.post("/bom")
async def sync_bom(
    req: SyncBomRequest,
    session: AsyncSession = Depends(get_session),
):
    try:
        service = BomSyncService(session, settings)
        result = await service.sync_batch(req.order_line_ids)
        await session.commit()
        return ApiResponse.ok(data={
            "success_count": result.success_count,
            "fail_count": result.fail_count,
        })
    except Exception as e:
        logger.error(f"BOM sync failed: {e}")
        raise BizException(ErrorCode.EXTERNAL_API_FAILED, str(e))


@router.post("/production-orders")
async def sync_production_orders(
    session: AsyncSession = Depends(get_session),
):
    try:
        service = ProductionOrderSyncService(session, settings)
        result = await service.sync()
        await session.commit()
        return ApiResponse.ok(data={
            "success_count": result.success_count,
            "fail_count": result.fail_count,
            "insert_count": result.insert_count,
            "update_count": result.update_count,
            "issue_count": result.issue_count,
        })
    except Exception as e:
        logger.error(f"Production order sync failed: {e}")
        raise BizException(ErrorCode.EXTERNAL_API_FAILED, str(e))


@router.post("/research")
async def sync_research(
    req: SyncResearchRequest,
    session: AsyncSession = Depends(get_session),
):
    try:
        service = ResearchSyncService(session, settings)
        result = await service.sync()
        await session.commit()
        return ApiResponse.ok(data={
            "success_count": result.success_count,
            "fail_count": result.fail_count,
            "insert_count": result.insert_count,
            "update_count": result.update_count,
            "issue_count": result.issue_count,
        })
    except Exception as e:
        logger.error(f"Research sync failed: {e}")
        raise BizException(ErrorCode.EXTERNAL_API_FAILED, str(e))
```

---

### Task 12: Admin Schedule Router

**Files:**
- Create: `app/routers/admin_schedule.py`

- [ ] **Step 1: Create admin schedule router**

```python
# app/routers/admin_schedule.py
import logging
from datetime import datetime
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.response import ApiResponse
from app.common.exceptions import BizException, ErrorCode
from app.database import get_session
from app.schemas.admin_schemas import ScheduleRunRequest
from app.scheduler.schedule_orchestrator import ScheduleOrchestrator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin/schedule", tags=["手动排产"])


@router.post("/run")
async def run_schedule(
    req: ScheduleRunRequest,
    session: AsyncSession = Depends(get_session),
):
    try:
        orchestrator = ScheduleOrchestrator(session)
        batch_result = await orchestrator.schedule_batch(req.order_line_ids)
        await session.commit()
        run_batch_no = f"SCH{datetime.now().strftime('%Y%m%d%H%M%S')}"
        return ApiResponse.ok(data={
            "run_batch_no": run_batch_no,
            "total": batch_result["total"],
            "success_count": batch_result["scheduled"],
            "fail_count": batch_result["failed"],
        })
    except Exception as e:
        logger.error(f"Schedule run failed: {e}")
        raise BizException(ErrorCode.SCHEDULE_CALC_FAILED, str(e))
```

---

### Task 13: Admin Assembly Time Router

**Files:**
- Create: `app/routers/admin_assembly_time.py`

- [ ] **Step 1: Create assembly time router**

```python
# app/routers/admin_assembly_time.py
from fastapi import APIRouter, Depends, Query
from typing import Optional
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.response import ApiResponse
from app.database import get_session
from app.models.assembly_time import AssemblyTimeBaseline
from app.repository.assembly_time_repo import AssemblyTimeRepo
from app.schemas.admin_schemas import AssemblyTimeRequest

router = APIRouter(prefix="/api/admin/assembly-times", tags=["装配时长维护"])


@router.get("")
async def list_assembly_times(
    machine_model: Optional[str] = None,
    product_series: Optional[str] = None,
    assembly_name: Optional[str] = None,
    session: AsyncSession = Depends(get_session),
):
    stmt = select(AssemblyTimeBaseline)
    conditions = []
    if machine_model:
        conditions.append(AssemblyTimeBaseline.machine_model == machine_model)
    if product_series:
        conditions.append(AssemblyTimeBaseline.product_series == product_series)
    if assembly_name:
        conditions.append(AssemblyTimeBaseline.assembly_name == assembly_name)
    if conditions:
        stmt = stmt.where(and_(*conditions))
    stmt = stmt.order_by(AssemblyTimeBaseline.machine_model, AssemblyTimeBaseline.production_sequence)
    result = await session.execute(stmt)
    items = result.scalars().all()
    return ApiResponse.ok(data=[
        {
            "id": i.id,
            "machine_model": i.machine_model,
            "product_series": i.product_series,
            "assembly_name": i.assembly_name,
            "assembly_time_days": float(i.assembly_time_days),
            "is_final_assembly": i.is_final_assembly,
            "production_sequence": i.production_sequence,
            "is_default": i.is_default,
            "remark": i.remark,
        }
        for i in items
    ])


@router.post("")
async def save_assembly_time(
    req: AssemblyTimeRequest,
    session: AsyncSession = Depends(get_session),
):
    repo = AssemblyTimeRepo(session)
    existing = await repo.find_by_model_and_assembly(req.machine_model, req.assembly_name)
    if existing:
        existing.product_series = req.product_series
        existing.assembly_time_days = req.assembly_time_days
        existing.is_final_assembly = req.is_final_assembly
        existing.production_sequence = req.production_sequence
        existing.is_default = req.is_default
        existing.remark = req.remark
        await session.flush()
        entity = existing
    else:
        entity = AssemblyTimeBaseline(
            machine_model=req.machine_model,
            product_series=req.product_series,
            assembly_name=req.assembly_name,
            assembly_time_days=req.assembly_time_days,
            is_final_assembly=req.is_final_assembly,
            production_sequence=req.production_sequence,
            is_default=req.is_default,
            remark=req.remark,
        )
        await repo.add(entity)
    await session.commit()
    return ApiResponse.ok(data={"id": entity.id, "machine_model": entity.machine_model})
```

---

### Task 14: Admin Work Calendar Router

**Files:**
- Create: `app/routers/admin_work_calendar.py`

- [ ] **Step 1: Create work calendar router**

```python
# app/routers/admin_work_calendar.py
from fastapi import APIRouter, Depends, Query
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.response import ApiResponse
from app.database import get_session
from app.repository.work_calendar_repo import WorkCalendarRepo
from app.schemas.admin_schemas import WorkCalendarBatchRequest

router = APIRouter(prefix="/api/admin/work-calendar", tags=["工作日历维护"])


@router.get("")
async def get_work_calendar(
    month: Optional[str] = Query(None, description="yyyy-MM"),
    session: AsyncSession = Depends(get_session),
):
    repo = WorkCalendarRepo(session)
    if month:
        parts = month.split("-")
        year, m = int(parts[0]), int(parts[1])
        items = await repo.get_by_month(year, m)
    else:
        items = await repo.list_all()
    return ApiResponse.ok(data=[
        {
            "id": i.id,
            "calendar_date": i.calendar_date.isoformat(),
            "is_workday": i.is_workday,
            "remark": i.remark,
        }
        for i in items
    ])


@router.post("")
async def update_work_calendar(
    req: WorkCalendarBatchRequest,
    session: AsyncSession = Depends(get_session),
):
    repo = WorkCalendarRepo(session)
    count = 0
    for item in req.items:
        await repo.upsert(item.calendar_date, item.is_workday, item.remark)
        count += 1
    await session.commit()
    return ApiResponse.ok(data={"updated_count": count})
```

---

### Task 15: Admin Issues Router

**Files:**
- Create: `app/routers/admin_issues.py`

- [ ] **Step 1: Create admin issues router**

```python
# app/routers/admin_issues.py
from datetime import datetime
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.response import ApiResponse
from app.common.exceptions import BizException, ErrorCode
from app.database import get_session
from app.repository.data_issue_repo import DataIssueRepo
from app.schemas.issue_schemas import IssueActionRequest

router = APIRouter(prefix="/api/admin/issues", tags=["异常处理"])


@router.post("/{issue_id}/resolve")
async def resolve_issue(
    issue_id: int,
    req: IssueActionRequest,
    session: AsyncSession = Depends(get_session),
):
    repo = DataIssueRepo(session)
    issue = await repo.get_by_id(issue_id)
    if not issue:
        raise BizException(ErrorCode.NOT_FOUND, f"异常记录不存在: {issue_id}")
    issue.status = "resolved"
    issue.remark = req.remark
    issue.handled_at = datetime.now()
    await session.commit()
    return ApiResponse.ok(data={"id": issue.id, "status": issue.status})


@router.post("/{issue_id}/ignore")
async def ignore_issue(
    issue_id: int,
    req: IssueActionRequest,
    session: AsyncSession = Depends(get_session),
):
    repo = DataIssueRepo(session)
    issue = await repo.get_by_id(issue_id)
    if not issue:
        raise BizException(ErrorCode.NOT_FOUND, f"异常记录不存在: {issue_id}")
    issue.status = "ignored"
    issue.remark = req.remark
    issue.handled_at = datetime.now()
    await session.commit()
    return ApiResponse.ok(data={"id": issue.id, "status": issue.status})
```

---

### Task 16: Test Conftest — Add App Client Fixture

**Files:**
- Modify: `tests/conftest.py`

- [ ] **Step 1: Add `app_client` fixture**

Add httpx AsyncClient fixture for FastAPI TestClient pattern, using the existing `db_session` fixture to override the `get_session` dependency.

```python
# Add to tests/conftest.py — after existing db_session fixture

@pytest_asyncio.fixture
async def app_client(db_session):
    from httpx import AsyncClient, ASGITransport
    from app.main import app
    from app.database import get_session

    async def override_get_session():
        yield db_session

    app.dependency_overrides[get_session] = override_get_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()
```

---

### Task 17: API Tests — Schedule Query

**Files:**
- Create: `tests/test_api/__init__.py`
- Create: `tests/test_api/test_schedules_api.py`

- [ ] **Step 1: Create test_api package**

- [ ] **Step 2: Create schedule API tests**

```python
# tests/test_api/test_schedules_api.py
import pytest
from decimal import Decimal
from datetime import datetime

from app.models.machine_schedule_result import MachineScheduleResult
from app.models.part_schedule_result import PartScheduleResult


@pytest.mark.asyncio
async def test_list_schedules_empty(app_client):
    resp = await app_client.get("/api/schedules")
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 0
    assert body["data"]["total"] == 0


@pytest.mark.asyncio
async def test_list_schedules_with_data(app_client, db_session):
    db_session.add(MachineScheduleResult(
        order_line_id=1, contract_no="HT001", product_model="MC1-80",
        schedule_status="scheduled", planned_start_date=datetime(2026, 4, 1),
        planned_end_date=datetime(2026, 6, 30),
        machine_cycle_days=Decimal("60"), machine_assembly_days=Decimal("3"),
    ))
    await db_session.commit()

    resp = await app_client.get("/api/schedules")
    body = resp.json()
    assert body["data"]["total"] == 1
    assert body["data"]["items"][0]["contract_no"] == "HT001"


@pytest.mark.asyncio
async def test_schedule_detail(app_client, db_session):
    db_session.add(MachineScheduleResult(
        order_line_id=99, contract_no="HT002", product_model="MC1-80",
        schedule_status="scheduled",
        machine_cycle_days=Decimal("60"), machine_assembly_days=Decimal("3"),
    ))
    db_session.add(PartScheduleResult(
        order_line_id=99, assembly_name="机身", production_sequence=1,
        key_part_material_no="P001", key_part_cycle_days=Decimal("15"),
    ))
    await db_session.commit()

    resp = await app_client.get("/api/schedules/99")
    body = resp.json()
    assert body["code"] == 0
    assert body["data"]["machine_schedule"]["contract_no"] == "HT002"
    assert len(body["data"]["part_schedules"]) == 1


@pytest.mark.asyncio
async def test_schedule_detail_not_found(app_client):
    resp = await app_client.get("/api/schedules/9999")
    body = resp.json()
    assert body["code"] == 4002
```

---

### Task 18: API Tests — Issues, Exports, Admin

**Files:**
- Create: `tests/test_api/test_issues_api.py`
- Create: `tests/test_api/test_exports_api.py`
- Create: `tests/test_api/test_admin_schedule_api.py`
- Create: `tests/test_api/test_admin_assembly_time_api.py`
- Create: `tests/test_api/test_admin_work_calendar_api.py`
- Create: `tests/test_api/test_admin_issues_api.py`

- [ ] **Step 1: Create issue API tests**

```python
# tests/test_api/test_issues_api.py
import pytest
from app.models.data_issue import DataIssueRecord


@pytest.mark.asyncio
async def test_list_issues_empty(app_client):
    resp = await app_client.get("/api/issues")
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 0
    assert body["data"]["total"] == 0


@pytest.mark.asyncio
async def test_list_issues_with_filter(app_client, db_session):
    db_session.add(DataIssueRecord(
        issue_type="周期异常", issue_title="测试异常", status="open",
    ))
    await db_session.commit()

    resp = await app_client.get("/api/issues?status=open")
    body = resp.json()
    assert body["data"]["total"] == 1
```

- [ ] **Step 2: Create export API tests**

```python
# tests/test_api/test_exports_api.py
import pytest
from decimal import Decimal
from datetime import datetime
from app.models.machine_schedule_result import MachineScheduleResult


@pytest.mark.asyncio
async def test_export_machine_schedules(app_client, db_session):
    db_session.add(MachineScheduleResult(
        order_line_id=1, contract_no="HT001", product_model="MC1-80",
        schedule_status="scheduled",
        machine_cycle_days=Decimal("60"), machine_assembly_days=Decimal("3"),
    ))
    await db_session.commit()

    resp = await app_client.get("/api/exports/machine-schedules")
    assert resp.status_code == 200
    assert "spreadsheetml" in resp.headers["content-type"]


@pytest.mark.asyncio
async def test_export_part_schedules(app_client, db_session):
    resp = await app_client.get("/api/exports/part-schedules")
    assert resp.status_code == 200
    assert "spreadsheetml" in resp.headers["content-type"]
```

- [ ] **Step 3: Create admin schedule API test**

```python
# tests/test_api/test_admin_schedule_api.py
import pytest
from decimal import Decimal
from datetime import datetime
from app.models.sales_plan import SalesPlanOrderLineSrc
from app.models.machine_cycle_baseline import MachineCycleBaseline
from app.models.assembly_time import AssemblyTimeBaseline


@pytest.mark.asyncio
async def test_run_schedule(app_client, db_session):
    order = SalesPlanOrderLineSrc(
        sap_code="SAP001", sap_line_no="10",
        product_model="MC1-80", product_series="MC1",
        material_no="MACH001", quantity=Decimal("1"),
        confirmed_delivery_date=datetime(2026, 6, 30),
        drawing_released=True,
        drawing_release_date=datetime(2026, 3, 1),
    )
    db_session.add(order)
    db_session.add(MachineCycleBaseline(
        machine_model="MC1-80", product_series="MC1",
        order_qty=Decimal("1"), cycle_days_median=Decimal("60"),
        sample_count=5, is_active=True,
    ))
    db_session.add(AssemblyTimeBaseline(
        machine_model="MC1-80", assembly_name="整机总装",
        assembly_time_days=Decimal("3"), is_final_assembly=True,
        production_sequence=99,
    ))
    await db_session.commit()

    resp = await app_client.post("/api/admin/schedule/run", json={
        "order_line_ids": [order.id],
    })
    body = resp.json()
    assert body["code"] == 0
    assert body["data"]["total"] == 1
```

- [ ] **Step 4: Create admin assembly time API tests**

```python
# tests/test_api/test_admin_assembly_time_api.py
import pytest


@pytest.mark.asyncio
async def test_list_assembly_times_empty(app_client):
    resp = await app_client.get("/api/admin/assembly-times")
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 0
    assert body["data"] == []


@pytest.mark.asyncio
async def test_save_assembly_time(app_client):
    resp = await app_client.post("/api/admin/assembly-times", json={
        "machine_model": "MC1-80",
        "assembly_name": "机身",
        "assembly_time_days": 2,
        "production_sequence": 1,
    })
    body = resp.json()
    assert body["code"] == 0
    assert body["data"]["id"] is not None

    # verify appears in list
    resp2 = await app_client.get("/api/admin/assembly-times?machine_model=MC1-80")
    body2 = resp2.json()
    assert len(body2["data"]) == 1
```

- [ ] **Step 5: Create admin work calendar API tests**

```python
# tests/test_api/test_admin_work_calendar_api.py
import pytest


@pytest.mark.asyncio
async def test_update_work_calendar(app_client):
    resp = await app_client.post("/api/admin/work-calendar", json={
        "items": [
            {"calendar_date": "2026-04-05", "is_workday": False, "remark": "清明节"},
            {"calendar_date": "2026-04-12", "is_workday": True, "remark": "调休上班"},
        ]
    })
    body = resp.json()
    assert body["code"] == 0
    assert body["data"]["updated_count"] == 2


@pytest.mark.asyncio
async def test_get_work_calendar_by_month(app_client):
    # first insert some data
    await app_client.post("/api/admin/work-calendar", json={
        "items": [{"calendar_date": "2026-04-05", "is_workday": False}]
    })

    resp = await app_client.get("/api/admin/work-calendar?month=2026-04")
    body = resp.json()
    assert body["code"] == 0
    assert len(body["data"]) >= 1
```

- [ ] **Step 6: Create admin issues API tests**

```python
# tests/test_api/test_admin_issues_api.py
import pytest
from app.models.data_issue import DataIssueRecord


@pytest.mark.asyncio
async def test_resolve_issue(app_client, db_session):
    issue = DataIssueRecord(
        issue_type="周期异常", issue_title="测试", status="open",
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
        issue_type="数据异常", issue_title="测试2", status="open",
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
```

---

### Task 19: Run All Tests

- [ ] **Step 1: Run tests**

```bash
cd auto-scheduling-system/services/api && python -m pytest tests/ -v
```

Expected: ALL tests pass (existing 72 + new API tests).

---

### Task 20: Commit

- [ ] **Step 1: Commit Phase 4**

```bash
git add app/schemas/ app/routers/ app/services/ tests/test_api/
git add app/main.py app/repository/machine_schedule_result_repo.py tests/conftest.py
git commit -m "feat: Phase 4 API layer — REST endpoints, export, admin"
```
