# Phase 2: Integration + Sync Layer Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the external API clients (观远/SAP/飞书) and data sync services that pull data from external systems into the local database.

**Architecture:** Integration layer wraps all external HTTP calls (auth, pagination, field mapping). Sync layer orchestrates the integration clients, performs upsert/delete-insert, logs sync jobs, and records data issues. All external calls use httpx async client with retry.

**Tech Stack:** Python 3.11+, httpx (async HTTP), SQLAlchemy 2.0 (async), pytest, pytest-asyncio, respx (HTTP mocking)

**Spec documents:**
- `自动排产项目资料包/01_需求/02_PRD.md` (section 14.2 — all external interfaces)
- `自动排产项目资料包/03_设计/01_后端设计.md` (sections 2.1, 2.3, 3.1–3.5)
- `自动排产项目资料包/03_设计/02_API设计.md` (section 4 — manual sync APIs)

**This is Plan 2 of 4:**
1. **Foundation** (done): scaffold, models, repos, common utils
2. **Integration + Sync** (this plan): external API clients, data sync services
3. **Baseline + Scheduler**: cycle baselines, scheduling engine
4. **API Layer**: REST endpoints, export, admin

---

## File Structure

```
auto-scheduling-system/services/api/
├── app/
│   ├── integration/
│   │   ├── __init__.py
│   │   ├── guandata_client.py        # 观远认证 + 销售计划数据拉取
│   │   ├── sap_bom_client.py         # SAP BOM 接口
│   │   ├── feishu_client.py          # 飞书认证 + 多维表格通用操作
│   │   └── feishu_field_maps.py      # 飞书字段映射常量
│   ├── sync/
│   │   ├── __init__.py
│   │   ├── sales_plan_sync.py        # 销售计划同步
│   │   ├── research_sync.py          # 研究所同步
│   │   ├── production_order_sync.py  # 生产订单同步
│   │   ├── drawing_status_sync.py    # 发图状态回填
│   │   ├── bom_sync.py               # BOM 同步
│   │   └── sync_helpers.py           # SyncResult, sync job logging
│   └── ...
├── tests/
│   ├── test_integration/
│   │   ├── __init__.py
│   │   ├── test_guandata_client.py
│   │   ├── test_sap_bom_client.py
│   │   └── test_feishu_client.py
│   └── test_sync/
│       ├── __init__.py
│       ├── test_sales_plan_sync.py
│       ├── test_research_sync.py
│       ├── test_production_order_sync.py
│       ├── test_drawing_status_sync.py
│       └── test_bom_sync.py
└── ...
```

---

### Task 1: Sync Helpers — SyncResult and Job Logging

**Files:**
- Create: `auto-scheduling-system/services/api/app/sync/__init__.py`
- Create: `auto-scheduling-system/services/api/app/sync/sync_helpers.py`
- Test: `auto-scheduling-system/services/api/tests/test_sync/__init__.py`
- Test: `auto-scheduling-system/services/api/tests/test_sync/test_sync_helpers.py`

- [ ] **Step 1: Write failing test for SyncResult and sync job logging**

```python
# tests/test_sync/test_sync_helpers.py
import pytest
from datetime import datetime
from app.sync.sync_support_utils import SyncResult, start_sync_job, finish_sync_job
from app.repository.sync_job_log_repo import SyncJobLogRepo


@pytest.mark.asyncio
async def test_sync_result_defaults():
    r = SyncResult()
    assert r.success_count == 0
    assert r.fail_count == 0
    assert r.insert_count == 0
    assert r.update_count == 0
    assert r.issue_count == 0


@pytest.mark.asyncio
async def test_sync_result_increment():
    r = SyncResult()
    r.record_insert()
    r.record_insert()
    r.record_update()
    r.record_fail()
    r.record_issue()
    assert r.success_count == 3
    assert r.insert_count == 2
    assert r.update_count == 1
    assert r.fail_count == 1
    assert r.issue_count == 1


@pytest.mark.asyncio
async def test_start_and_finish_sync_job(db_session):
    repo = SyncJobLogRepo(db_session)
    job = await start_sync_job(db_session, job_type="sales_plan", source_system="guandata")
    await db_session.commit()
    assert job.id is not None
    assert job.status == "running"

    result = SyncResult()
    result.record_insert()
    result.record_insert()
    result.record_fail()
    await finish_sync_job(db_session, job, result, message="done")
    await db_session.commit()
    assert job.status == "completed"
    assert job.success_count == 2
    assert job.fail_count == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd auto-scheduling-system/services/api && python -m pytest tests/test_sync/test_sync_helpers.py -v`
Expected: FAIL

- [ ] **Step 3: Implement sync_helpers**

```python
# app/sync/__init__.py
```

```python
# app/sync/sync_helpers.py
from dataclasses import dataclass, field
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.sync_job_log import SyncJobLog


@dataclass
class SyncResult:
    success_count: int = 0
    fail_count: int = 0
    insert_count: int = 0
    update_count: int = 0
    issue_count: int = 0

    def record_insert(self):
        self.success_count += 1
        self.insert_count += 1

    def record_update(self):
        self.success_count += 1
        self.update_count += 1

    def record_fail(self):
        self.fail_count += 1

    def record_issue(self):
        self.issue_count += 1


async def start_sync_job(
    session: AsyncSession,
    job_type: str,
    source_system: str,
) -> SyncJobLog:
    job = SyncJobLog(
        job_type=job_type,
        source_system=source_system,
        start_time=datetime.now(),
        status="running",
    )
    session.add(job)
    await session.flush()
    return job


async def finish_sync_job(
    session: AsyncSession,
    job: SyncJobLog,
    result: SyncResult,
    message: str = "",
) -> SyncJobLog:
    job.end_time = datetime.now()
    job.status = "completed" if result.fail_count == 0 else "completed_with_errors"
    job.success_count = result.success_count
    job.fail_count = result.fail_count
    job.message = message
    await session.flush()
    return job
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd auto-scheduling-system/services/api && python -m pytest tests/test_sync/test_sync_helpers.py -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add app/sync/ tests/test_sync/
git commit -m "feat: add SyncResult and sync job logging helpers"
```

---

### Task 2: Integration — Guandata Client (Auth + Sales Plan)

**Files:**
- Create: `auto-scheduling-system/services/api/app/integration/__init__.py`
- Create: `auto-scheduling-system/services/api/app/integration/guandata_client.py`
- Test: `auto-scheduling-system/services/api/tests/test_integration/__init__.py`
- Test: `auto-scheduling-system/services/api/tests/test_integration/test_guandata_client.py`

**Key rules:**
- Auth: POST to get token, cache until `expireAt`
- Sales data: POST with offset/limit pagination, filter by `confirmed_delivery_date` not empty
- Field mapping: `response.preview[i][index]` → system fields per mapping table
- preview indices from PRD: crm_no=1, contract_no=2, customer_name=5, detail_id=16, product_model=22, product_series=23, product_name=25, material_no=26, quantity=27, contract_unit_price=29, confirmed_delivery_date=31, delivery_date=32, line_total_amount=34, order_no=40, custom_no=44, order_type=45, is_automation_project=48, business_group=49, sales_person_name=51, sales_person_job_no=52, order_date=53, sales_branch_company=59, sales_sub_branch=60, sap_code=70, sap_line_no=71, oa_flow_id=118, operator_name=136, operator_job_no=137, review_comment=139, custom_requirement=140, delivery_plant=141

- [ ] **Step 1: Write failing tests**

```python
# tests/test_integration/test_guandata_client.py
import pytest
import httpx
import respx
from app.integration.guandata_client import GuandataClient


@pytest.fixture
def client():
    return GuandataClient(
        base_url="https://guandata.example.com",
        domain="test_domain",
        login_id="test_user",
        password="test_pass",
        ds_id="test_ds",
    )


@respx.mock
@pytest.mark.asyncio
async def test_authenticate(client):
    respx.post("https://guandata.example.com/public/auth/login").mock(
        return_value=httpx.Response(200, json={
            "response": {"token": "tok123", "expireAt": 9999999999999}
        })
    )
    token = await client.authenticate()
    assert token == "tok123"


@respx.mock
@pytest.mark.asyncio
async def test_fetch_sales_page(client):
    respx.post("https://guandata.example.com/public/auth/login").mock(
        return_value=httpx.Response(200, json={
            "response": {"token": "tok123", "expireAt": 9999999999999}
        })
    )
    # Build a minimal preview row (142 fields, indices 0-141)
    row = [""] * 142
    row[1] = "CRM001"
    row[2] = "HT001"
    row[5] = "客户A"
    row[16] = "DT001"
    row[22] = "MC1-80"
    row[23] = "MC1"
    row[25] = "压力机"
    row[26] = "MAT001"
    row[27] = "2"
    row[31] = "2026-06-01"
    row[40] = "SO001"
    row[70] = "SAP001"
    row[71] = "10"

    respx.post("https://guandata.example.com/public/dataservice/datas/getPreview").mock(
        return_value=httpx.Response(200, json={
            "response": {
                "preview": [row],
                "totalCount": 1,
            }
        })
    )

    records, total = await client.fetch_sales_page(offset=0, limit=100)
    assert total == 1
    assert len(records) == 1
    assert records[0]["contract_no"] == "HT001"
    assert records[0]["detail_id"] == "DT001"
    assert records[0]["order_no"] == "SO001"
    assert records[0]["sap_code"] == "SAP001"
    assert records[0]["material_no"] == "MAT001"


@respx.mock
@pytest.mark.asyncio
async def test_fetch_empty_page(client):
    respx.post("https://guandata.example.com/public/auth/login").mock(
        return_value=httpx.Response(200, json={
            "response": {"token": "tok123", "expireAt": 9999999999999}
        })
    )
    respx.post("https://guandata.example.com/public/dataservice/datas/getPreview").mock(
        return_value=httpx.Response(200, json={
            "response": {"preview": [], "totalCount": 0}
        })
    )
    records, total = await client.fetch_sales_page(offset=0, limit=100)
    assert total == 0
    assert len(records) == 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd auto-scheduling-system/services/api && python -m pytest tests/test_integration/test_guandata_client.py -v`
Expected: FAIL

- [ ] **Step 3: Install respx for HTTP mocking**

Run: `cd auto-scheduling-system/services/api && pip install respx`
Then add `respx>=0.21.0` to dev dependencies in pyproject.toml.

- [ ] **Step 4: Implement GuandataClient**

```python
# app/integration/__init__.py
```

```python
# app/integration/guandata_client.py
import time
import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# preview index → system field name
_PREVIEW_FIELD_MAP: dict[int, str] = {
    1: "crm_no",
    2: "contract_no",
    5: "customer_name",
    16: "detail_id",
    22: "product_model",
    23: "product_series",
    25: "product_name",
    26: "material_no",
    27: "quantity",
    29: "contract_unit_price",
    31: "confirmed_delivery_date",
    32: "delivery_date",
    34: "line_total_amount",
    40: "order_no",
    44: "custom_no",
    45: "order_type",
    48: "is_automation_project",
    49: "business_group",
    51: "sales_person_name",
    52: "sales_person_job_no",
    53: "order_date",
    59: "sales_branch_company",
    60: "sales_sub_branch",
    70: "sap_code",
    71: "sap_line_no",
    118: "oa_flow_id",
    136: "operator_name",
    137: "operator_job_no",
    139: "review_comment",
    140: "custom_requirement",
    141: "delivery_plant",
}


class GuandataClient:
    def __init__(
        self,
        base_url: str,
        domain: str,
        login_id: str,
        password: str,
        ds_id: str,
    ):
        self.base_url = base_url.rstrip("/")
        self.domain = domain
        self.login_id = login_id
        self.password = password
        self.ds_id = ds_id
        self._token: str | None = None
        self._token_expire: float = 0

    async def authenticate(self) -> str:
        if self._token and time.time() * 1000 < self._token_expire:
            return self._token
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.base_url}/public/auth/login",
                json={
                    "domain": self.domain,
                    "loginId": self.login_id,
                    "password": self.password,
                },
            )
            resp.raise_for_status()
            data = resp.json()["response"]
            self._token = data["token"]
            self._token_expire = data["expireAt"]
            return self._token

    async def fetch_sales_page(
        self,
        offset: int = 0,
        limit: int = 200,
        filters: list[dict[str, Any]] | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        """Fetch one page of sales plan data. Returns (records, totalCount)."""
        token = await self.authenticate()
        body: dict[str, Any] = {
            "dsId": self.ds_id,
            "offset": offset,
            "limit": limit,
        }
        if filters:
            body["filter"] = filters

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.base_url}/public/dataservice/datas/getPreview",
                json=body,
                headers={"X-Auth-Token": token},
            )
            resp.raise_for_status()

        response_data = resp.json()["response"]
        preview_rows = response_data.get("preview", [])
        total_count = response_data.get("totalCount", 0)

        records = []
        for row in preview_rows:
            record = {}
            for idx, field_name in _PREVIEW_FIELD_MAP.items():
                if idx < len(row):
                    record[field_name] = row[idx] if row[idx] else None
                else:
                    record[field_name] = None
            records.append(record)

        return records, total_count
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd auto-scheduling-system/services/api && python -m pytest tests/test_integration/test_guandata_client.py -v`
Expected: ALL PASS

- [ ] **Step 6: Commit**

```bash
git add app/integration/ tests/test_integration/ pyproject.toml
git commit -m "feat: add Guandata client with auth and sales plan pagination"
```

---

### Task 3: Integration — Feishu Client (Auth + Bitable)

**Files:**
- Create: `auto-scheduling-system/services/api/app/integration/feishu_client.py`
- Create: `auto-scheduling-system/services/api/app/integration/feishu_field_maps.py`
- Test: `auto-scheduling-system/services/api/tests/test_integration/test_feishu_client.py`

**Key rules:**
- Auth: POST `/open-apis/auth/v3/tenant_access_token/internal` with app_id + app_secret
- Bitable: POST `/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records/search`
- Pagination via `page_token`, max `page_size=500`
- Text fields: `fields[name][0].text` or `fields[name]` for single-select
- Date fields: millisecond timestamps

- [ ] **Step 1: Write failing tests**

```python
# tests/test_integration/test_feishu_client.py
import pytest
import httpx
import respx
from app.integration.feishu_client import FeishuClient


@pytest.fixture
def client():
    return FeishuClient(
        app_id="test_app",
        app_secret="test_secret",
    )


@respx.mock
@pytest.mark.asyncio
async def test_get_token(client):
    respx.post("https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal").mock(
        return_value=httpx.Response(200, json={
            "code": 0,
            "tenant_access_token": "t-abc123",
            "expire": 7200,
        })
    )
    token = await client.get_token()
    assert token == "t-abc123"


@respx.mock
@pytest.mark.asyncio
async def test_search_records(client):
    respx.post("https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal").mock(
        return_value=httpx.Response(200, json={
            "code": 0, "tenant_access_token": "t-abc123", "expire": 7200,
        })
    )
    respx.post(
        "https://open.feishu.cn/open-apis/bitable/v1/apps/app123/tables/tbl456/records/search"
    ).mock(
        return_value=httpx.Response(200, json={
            "code": 0,
            "data": {
                "items": [
                    {
                        "record_id": "rec1",
                        "fields": {
                            "生产订单号": [{"text": "PO001"}],
                            "物料号": [{"text": "MAT001"}],
                            "订货数量": 5,
                            "生产订单状态": "已完工",
                        }
                    }
                ],
                "has_more": False,
                "page_token": "",
                "total": 1,
            }
        })
    )
    items, has_more, page_token, total = await client.search_records(
        app_token="app123",
        table_id="tbl456",
        field_names=["生产订单号", "物料号", "订货数量", "生产订单状态"],
    )
    assert len(items) == 1
    assert items[0]["fields"]["生产订单状态"] == "已完工"
    assert has_more is False
    assert total == 1


@respx.mock
@pytest.mark.asyncio
async def test_search_with_filter(client):
    respx.post("https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal").mock(
        return_value=httpx.Response(200, json={
            "code": 0, "tenant_access_token": "t-abc123", "expire": 7200,
        })
    )
    respx.post(
        "https://open.feishu.cn/open-apis/bitable/v1/apps/app123/tables/tbl456/records/search"
    ).mock(
        return_value=httpx.Response(200, json={
            "code": 0,
            "data": {"items": [], "has_more": False, "page_token": "", "total": 0}
        })
    )
    items, has_more, _, total = await client.search_records(
        app_token="app123",
        table_id="tbl456",
        field_names=["生产订单号"],
        filter_config={
            "conjunction": "and",
            "conditions": [
                {"field_name": "最后更新时间", "operator": "isGreater", "value": ["ExactDate", "1710000000000"]}
            ]
        },
    )
    assert total == 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd auto-scheduling-system/services/api && python -m pytest tests/test_integration/test_feishu_client.py -v`
Expected: FAIL

- [ ] **Step 3: Implement FeishuClient**

```python
# app/integration/feishu_client.py
import time
import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

FEISHU_BASE_URL = "https://open.feishu.cn"


class FeishuClient:
    def __init__(self, app_id: str, app_secret: str):
        self.app_id = app_id
        self.app_secret = app_secret
        self._token: str | None = None
        self._token_expire: float = 0

    async def get_token(self) -> str:
        if self._token and time.time() < self._token_expire:
            return self._token
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{FEISHU_BASE_URL}/open-apis/auth/v3/tenant_access_token/internal",
                json={"app_id": self.app_id, "app_secret": self.app_secret},
            )
            resp.raise_for_status()
            data = resp.json()
            self._token = data["tenant_access_token"]
            self._token_expire = time.time() + data["expire"] - 60
            return self._token

    async def search_records(
        self,
        app_token: str,
        table_id: str,
        field_names: list[str],
        filter_config: dict[str, Any] | None = None,
        page_token: str | None = None,
        page_size: int = 500,
    ) -> tuple[list[dict], bool, str, int]:
        """Search bitable records. Returns (items, has_more, page_token, total)."""
        token = await self.get_token()
        body: dict[str, Any] = {
            "field_names": field_names,
            "automatic_fields": False,
        }
        if filter_config:
            body["filter"] = filter_config
        if page_token:
            body["page_token"] = page_token

        url = (
            f"{FEISHU_BASE_URL}/open-apis/bitable/v1/apps/{app_token}"
            f"/tables/{table_id}/records/search"
            f"?user_id_type=user_id&page_size={page_size}"
        )
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                url,
                json=body,
                headers={"Authorization": f"Bearer {token}"},
            )
            resp.raise_for_status()

        result = resp.json()
        if result.get("code") != 0:
            raise RuntimeError(f"Feishu API error: {result.get('msg', 'unknown')}")

        data = result["data"]
        items = data.get("items", [])
        has_more = data.get("has_more", False)
        next_token = data.get("page_token", "")
        total = data.get("total", 0)
        return items, has_more, next_token, total
```

- [ ] **Step 4: Create feishu_field_maps**

```python
# app/integration/feishu_field_maps.py
"""Field name constants for Feishu bitable tables."""

# 生产订单表字段
PRODUCTION_ORDER_FIELDS = [
    "生产订单号", "物料号", "物料描述", "机床型号", "生产工厂",
    "加工部门", "投产时间", "完工时间", "订货数量", "生产订单状态",
    "销售订单号", "创建时间", "最后更新时间",
]

# 研究所表字段
RESEARCH_FIELDS = [
    "订单编号", "明细ID", "明细-物料编号", "发图时间（研究所）",
    "明细-产品型号", "产品大系列", "明细-数量", "报检日期",
    "定制编号", "客户名称", "合同编号", "事业群", "订单类型",
    "最后更新时间",
]


def extract_feishu_text(fields: dict, field_name: str) -> str | None:
    """Extract text value from Feishu multi-line text field structure."""
    val = fields.get(field_name)
    if val is None:
        return None
    if isinstance(val, list) and len(val) > 0:
        return val[0].get("text", "")
    if isinstance(val, str):
        return val
    return str(val)


def extract_feishu_number(fields: dict, field_name: str) -> float | None:
    """Extract numeric value from Feishu field."""
    val = fields.get(field_name)
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return float(val)
    return None


def extract_feishu_timestamp_ms(fields: dict, field_name: str) -> int | None:
    """Extract millisecond timestamp from Feishu date field."""
    val = fields.get(field_name)
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return int(val)
    return None
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd auto-scheduling-system/services/api && python -m pytest tests/test_integration/test_feishu_client.py -v`
Expected: ALL PASS

- [ ] **Step 6: Commit**

```bash
git add app/integration/feishu_client.py app/integration/feishu_field_maps.py tests/test_integration/test_feishu_client.py
git commit -m "feat: add Feishu client with auth and bitable search"
```

---

### Task 4: Integration — SAP BOM Client

**Files:**
- Create: `auto-scheduling-system/services/api/app/integration/sap_bom_client.py`
- Test: `auto-scheduling-system/services/api/tests/test_integration/test_sap_bom_client.py`

**Key rules:**
- POST with IS_REQ (fixed params) + IS_MTNRV (material_no) + IS_WERKS (plant)
- Response: `LT_BOM001.item` for BOM rows
- Error: `ES_RET.CODE != ''` means error
- Field mapping: ZJBM→machine_material_no, ZJMS→machine_material_desc, WLBH→material_no, WLBHMS→material_desc, GC→plant, BOMZJ→bom_component_no, BOMMS→bom_component_desc, LJLX→part_type, ZJSL→component_qty
- Filter top-level redundant rows: `bom_component_no == machine_material_no`
- Build tree from flat list: parent=material_no, child=bom_component_no
- Mark `is_self_made` when part_type == "自产件"

- [ ] **Step 1: Write failing tests**

```python
# tests/test_integration/test_sap_bom_client.py
import pytest
import httpx
import respx
from app.integration.sap_bom_client import SapBomClient


@pytest.fixture
def client():
    return SapBomClient(base_url="https://sap.example.com")


@respx.mock
@pytest.mark.asyncio
async def test_fetch_bom_success(client):
    respx.post("https://sap.example.com").mock(
        return_value=httpx.Response(200, json={
            "ES_RET": {"CODE": "", "MSG": ""},
            "LT_BOM001": {
                "item": [
                    {
                        "ZJBM": "MACH001",
                        "ZJMS": "压力机",
                        "WLBH": "MACH001",
                        "WLBHMS": "压力机整机",
                        "GC": "1000",
                        "BOMZJ": "MACH001",
                        "BOMMS": "压力机整机",
                        "LJLX": "自产件",
                        "ZJSL": "1",
                    },
                    {
                        "ZJBM": "MACH001",
                        "ZJMS": "压力机",
                        "WLBH": "MACH001",
                        "WLBHMS": "压力机整机",
                        "GC": "1000",
                        "BOMZJ": "COMP001",
                        "BOMMS": "机身MC1-80",
                        "LJLX": "自产件",
                        "ZJSL": "1",
                    },
                    {
                        "ZJBM": "MACH001",
                        "ZJMS": "压力机",
                        "WLBH": "MACH001",
                        "WLBHMS": "压力机整机",
                        "GC": "1000",
                        "BOMZJ": "COMP002",
                        "BOMMS": "电气柜",
                        "LJLX": "外购件",
                        "ZJSL": "2",
                    },
                ]
            }
        })
    )

    rows = await client.fetch_bom(machine_material_no="MACH001", plant="1000")
    # Top-level row (BOMZJ == MACH001) should be filtered
    assert len(rows) == 2
    assert rows[0]["bom_component_no"] == "COMP001"
    assert rows[0]["is_self_made"] is True
    assert rows[1]["bom_component_no"] == "COMP002"
    assert rows[1]["is_self_made"] is False


@respx.mock
@pytest.mark.asyncio
async def test_fetch_bom_error(client):
    respx.post("https://sap.example.com").mock(
        return_value=httpx.Response(200, json={
            "ES_RET": {"CODE": "E", "MSG": "物料号不存在"},
            "LT_BOM001": {"item": []}
        })
    )
    with pytest.raises(RuntimeError, match="物料号不存在"):
        await client.fetch_bom(machine_material_no="BADMAT", plant="1000")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd auto-scheduling-system/services/api && python -m pytest tests/test_integration/test_sap_bom_client.py -v`
Expected: FAIL

- [ ] **Step 3: Implement SapBomClient**

```python
# app/integration/sap_bom_client.py
import logging
from typing import Any
from decimal import Decimal

import httpx

logger = logging.getLogger(__name__)

_SAP_FIELD_MAP = {
    "ZJBM": "machine_material_no",
    "ZJMS": "machine_material_desc",
    "WLBH": "material_no",
    "WLBHMS": "material_desc",
    "GC": "plant",
    "BOMZJ": "bom_component_no",
    "BOMMS": "bom_component_desc",
    "LJLX": "part_type",
    "ZJSL": "component_qty",
}

_SELF_MADE_TYPE = "自产件"


class SapBomClient:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")

    async def fetch_bom(
        self, machine_material_no: str, plant: str
    ) -> list[dict[str, Any]]:
        body = {
            "IS_REQ": {
                "SNDPRN": "OA",
                "RCVPRN": "SAP",
                "REQUSER": "OAUSER",
            },
            "IS_MTNRV": machine_material_no,
            "IS_WERKS": plant,
        }
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(self.base_url, json=body)
            resp.raise_for_status()

        data = resp.json()
        es_ret = data.get("ES_RET", {})
        if es_ret.get("CODE"):
            raise RuntimeError(f"SAP BOM error: {es_ret.get('MSG', 'unknown')}")

        items = data.get("LT_BOM001", {}).get("item", [])
        rows = []
        for item in items:
            mapped = {}
            for sap_key, sys_key in _SAP_FIELD_MAP.items():
                mapped[sys_key] = item.get(sap_key)

            # Filter top-level redundant row
            if mapped["bom_component_no"] == machine_material_no:
                continue

            # Parse component_qty to Decimal
            try:
                mapped["component_qty"] = Decimal(str(mapped["component_qty"]))
            except (TypeError, ValueError):
                mapped["component_qty"] = None

            mapped["is_self_made"] = mapped["part_type"] == _SELF_MADE_TYPE
            rows.append(mapped)

        return rows
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd auto-scheduling-system/services/api && python -m pytest tests/test_integration/test_sap_bom_client.py -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add app/integration/sap_bom_client.py tests/test_integration/test_sap_bom_client.py
git commit -m "feat: add SAP BOM client with field mapping and top-level filtering"
```

---

### Task 5: Sync — Sales Plan Sync Service

**Files:**
- Create: `auto-scheduling-system/services/api/app/sync/sales_plan_sync.py`
- Test: `auto-scheduling-system/services/api/tests/test_sync/test_sales_plan_sync.py`

**Key rules:**
- Call GuandataClient to paginate all pages
- Map fields, parse dates/numbers
- Upsert by sap_code + sap_line_no
- Parse order_type to enum (1/2/3)
- Parse is_automation_project string to bool
- Log sync job, record issues
- Parse confirmed_delivery_date string to datetime

- [ ] **Step 1: Write failing test**

```python
# tests/test_sync/test_sales_plan_sync.py
import pytest
from unittest.mock import AsyncMock, patch
from datetime import datetime
from decimal import Decimal

from app.sync.sales_plan_sync_service import SalesPlanSyncService
from app.repository.sales_plan_repo import SalesPlanRepo


@pytest.mark.asyncio
async def test_sync_inserts_records(db_session):
    mock_client = AsyncMock()
    mock_client.fetch_sales_page.side_effect = [
        ([{
            "crm_no": "CRM001",
            "contract_no": "HT001",
            "customer_name": "客户A",
            "detail_id": "DT001",
            "product_model": "MC1-80",
            "product_series": "MC1",
            "product_name": "压力机",
            "material_no": "MAT001",
            "quantity": "2",
            "contract_unit_price": "100000",
            "confirmed_delivery_date": "2026-06-01",
            "delivery_date": "2026-06-01",
            "line_total_amount": "200000",
            "order_no": "SO001",
            "custom_no": "CUS001",
            "order_type": "常规",
            "is_automation_project": "false",
            "business_group": "事业群A",
            "sales_person_name": "张三",
            "sales_person_job_no": "EMP001",
            "order_date": "2026-03-01",
            "sales_branch_company": "分公司A",
            "sales_sub_branch": "支公司A",
            "sap_code": "SAP001",
            "sap_line_no": "10",
            "oa_flow_id": None,
            "operator_name": None,
            "operator_job_no": None,
            "review_comment": None,
            "custom_requirement": None,
            "delivery_plant": "1000",
        }], 1),
    ]

    service = SalesPlanSyncService(db_session, mock_client)
    result = await service.sync()
    await db_session.commit()

    repo = SalesPlanRepo(db_session)
    count = await repo.count()
    assert count == 1
    assert result.insert_count == 1
    assert result.success_count == 1


@pytest.mark.asyncio
async def test_sync_updates_existing(db_session):
    mock_client = AsyncMock()
    record = {
        "crm_no": "CRM001",
        "contract_no": "HT001",
        "customer_name": "客户A",
        "detail_id": "DT001",
        "product_model": "MC1-80",
        "product_series": "MC1",
        "product_name": "压力机",
        "material_no": "MAT001",
        "quantity": "2",
        "contract_unit_price": None,
        "confirmed_delivery_date": "2026-06-01",
        "delivery_date": None,
        "line_total_amount": None,
        "order_no": "SO001",
        "custom_no": None,
        "order_type": None,
        "is_automation_project": None,
        "business_group": None,
        "sales_person_name": None,
        "sales_person_job_no": None,
        "order_date": None,
        "sales_branch_company": None,
        "sales_sub_branch": None,
        "sap_code": "SAP001",
        "sap_line_no": "10",
        "oa_flow_id": None,
        "operator_name": None,
        "operator_job_no": None,
        "review_comment": None,
        "custom_requirement": None,
        "delivery_plant": None,
    }
    mock_client.fetch_sales_page.side_effect = [
        ([record], 1),
    ]

    service = SalesPlanSyncService(db_session, mock_client)
    await service.sync()
    await db_session.commit()

    # Second sync: update customer name
    record2 = dict(record)
    record2["customer_name"] = "客户B"
    mock_client.fetch_sales_page.side_effect = [([record2], 1)]

    result = await service.sync()
    await db_session.commit()

    repo = SalesPlanRepo(db_session)
    count = await repo.count()
    assert count == 1
    assert result.update_count == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd auto-scheduling-system/services/api && python -m pytest tests/test_sync/test_sales_plan_sync.py -v`
Expected: FAIL

- [ ] **Step 3: Implement SalesPlanSyncService**

```python
# app/sync/sales_plan_sync.py
import logging
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.integration.guandata_client import GuandataClient
from app.repository.sales_plan_repo import SalesPlanRepo
from app.sync.sync_support_utils import SyncResult, start_sync_job, finish_sync_job

logger = logging.getLogger(__name__)

_ORDER_TYPE_MAP = {"常规": "1", "选配": "2", "定制": "3"}
_PAGE_SIZE = 200


def _parse_date(val: str | None) -> datetime | None:
    if not val:
        return None
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y/%m/%d"):
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


class SalesPlanSyncService:
    def __init__(self, session: AsyncSession, client: GuandataClient):
        self.session = session
        self.client = client
        self.repo = SalesPlanRepo(session)

    async def sync(
        self,
        filters: list[dict[str, Any]] | None = None,
    ) -> SyncResult:
        result = SyncResult()
        job = await start_sync_job(self.session, "sales_plan", "guandata")

        offset = 0
        while True:
            try:
                records, total = await self.client.fetch_sales_page(
                    offset=offset, limit=_PAGE_SIZE, filters=filters
                )
            except Exception as e:
                logger.error(f"Guandata fetch failed at offset {offset}: {e}")
                result.record_fail()
                break

            if not records:
                break

            for raw in records:
                try:
                    await self._upsert_record(raw, result)
                except Exception as e:
                    logger.error(f"Upsert failed for {raw.get('sap_code')}: {e}")
                    result.record_fail()
                    result.record_issue()

            offset += len(records)
            if offset >= total:
                break

        await finish_sync_job(self.session, job, result, f"synced {result.success_count} records")
        return result

    async def _upsert_record(self, raw: dict[str, Any], result: SyncResult):
        sap_code = raw.get("sap_code")
        sap_line_no = raw.get("sap_line_no")
        if not sap_code or not sap_line_no:
            result.record_fail()
            return

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
            "order_type": _ORDER_TYPE_MAP.get(raw.get("order_type", ""), raw.get("order_type")),
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

        existing = await self.repo.find_by_detail_id(raw.get("detail_id", "")) if raw.get("detail_id") else None
        row = await self.repo.upsert_by_sap_key(sap_code, sap_line_no, data)

        if existing and existing.sap_code == sap_code:
            result.record_update()
        else:
            # Check if it was an update by looking at the upsert behavior
            # Simple heuristic: if the row existed before, it's an update
            all_rows = await self.repo.count()
            result.record_insert()
```

Wait — the upsert tracking logic above is fragile. Let me simplify. The `upsert_by_sap_key` already handles insert vs update; we need to know which happened. Let me modify the approach:

```python
# app/sync/sales_plan_sync.py
import logging
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.integration.guandata_client import GuandataClient
from app.models.sales_plan import SalesPlanOrderLineSrc
from app.repository.sales_plan_repo import SalesPlanRepo
from app.sync.sync_support_utils import SyncResult, start_sync_job, finish_sync_job

logger = logging.getLogger(__name__)

_ORDER_TYPE_MAP = {"常规": "1", "选配": "2", "定制": "3"}
_PAGE_SIZE = 200


def _parse_date(val: str | None) -> datetime | None:
    if not val:
        return None
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y/%m/%d"):
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


class SalesPlanSyncService:
    def __init__(self, session: AsyncSession, client: GuandataClient):
        self.session = session
        self.client = client
        self.repo = SalesPlanRepo(session)

    async def sync(
        self,
        filters: list[dict[str, Any]] | None = None,
    ) -> SyncResult:
        result = SyncResult()
        job = await start_sync_job(self.session, "sales_plan", "guandata")

        offset = 0
        while True:
            try:
                records, total = await self.client.fetch_sales_page(
                    offset=offset, limit=_PAGE_SIZE, filters=filters
                )
            except Exception as e:
                logger.error(f"Guandata fetch failed at offset {offset}: {e}")
                result.record_fail()
                break

            if not records:
                break

            for raw in records:
                try:
                    await self._upsert_record(raw, result)
                except Exception as e:
                    logger.error(f"Upsert failed for {raw.get('sap_code')}: {e}")
                    result.record_fail()
                    result.record_issue()

            offset += len(records)
            if offset >= total:
                break

        await finish_sync_job(self.session, job, result, f"synced {result.success_count} records")
        return result

    async def _upsert_record(self, raw: dict[str, Any], result: SyncResult):
        sap_code = raw.get("sap_code")
        sap_line_no = raw.get("sap_line_no")
        if not sap_code or not sap_line_no:
            result.record_fail()
            return

        # Check if record exists to track insert vs update
        stmt = select(SalesPlanOrderLineSrc).where(
            and_(
                SalesPlanOrderLineSrc.sap_code == sap_code,
                SalesPlanOrderLineSrc.sap_line_no == sap_line_no,
            )
        )
        existing = (await self.session.execute(stmt)).scalar_one_or_none()

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
            "order_type": _ORDER_TYPE_MAP.get(raw.get("order_type", ""), raw.get("order_type")),
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

        await self.repo.upsert_by_sap_key(sap_code, sap_line_no, data)

        if existing:
            result.record_update()
        else:
            result.record_insert()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd auto-scheduling-system/services/api && python -m pytest tests/test_sync/test_sales_plan_sync.py -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add app/sync/sales_plan_sync.py tests/test_sync/test_sales_plan_sync.py
git commit -m "feat: add sales plan sync service with upsert and pagination"
```

---

### Task 6: Sync — Research Institute Sync Service

**Files:**
- Create: `auto-scheduling-system/services/api/app/sync/research_sync.py`
- Test: `auto-scheduling-system/services/api/tests/test_sync/test_research_sync.py`

**Key rules:**
- Pull from Feishu research table with incremental filter on `最后更新时间`
- Filter out records with empty `明细-物料编号`
- Map fields and upsert into `machine_cycle_history_src` by `detail_id`
- Calculate `cycle_days = 报检日期 - 发图时间（研究所）` in calendar days
- Support on-demand refresh by `订单编号`

- [ ] **Step 1: Write failing test**

```python
# tests/test_sync/test_research_sync.py
import pytest
from unittest.mock import AsyncMock
from decimal import Decimal

from app.sync.research_data_sync_service import ResearchSyncService
from app.repository.machine_cycle_history_repo import MachineCycleHistoryRepo


def _make_feishu_record(detail_id="DT001", material_no="MAT001", model="MC1-80",
                         qty=2, drawing_date=1711900800000, inspection_date=1713715200000):
    """Helper to build a Feishu bitable record."""
    return {
        "record_id": "rec1",
        "fields": {
            "订单编号": [{"text": "SO001"}],
            "明细ID": [{"text": detail_id}],
            "明细-物料编号": [{"text": material_no}],
            "发图时间（研究所）": drawing_date,
            "明细-产品型号": [{"text": model}],
            "产品大系列": "MC1",
            "明细-数量": qty,
            "报检日期": inspection_date,
            "定制编号": [{"text": "CUS001"}],
            "客户名称": [{"text": "客户A"}],
            "合同编号": [{"text": "HT001"}],
            "事业群": "事业群A",
            "订单类型": "常规",
        }
    }


@pytest.mark.asyncio
async def test_sync_inserts_record(db_session):
    mock_client = AsyncMock()
    mock_client.search_records.return_value = (
        [_make_feishu_record()], False, "", 1
    )

    service = ResearchSyncService(
        session=db_session,
        client=mock_client,
        app_token="app123",
        table_id="tbl456",
    )
    result = await service.sync()
    await db_session.commit()

    repo = MachineCycleHistoryRepo(db_session)
    count = await repo.count()
    assert count == 1
    assert result.insert_count == 1


@pytest.mark.asyncio
async def test_sync_filters_empty_material(db_session):
    record = _make_feishu_record()
    record["fields"]["明细-物料编号"] = [{"text": ""}]

    mock_client = AsyncMock()
    mock_client.search_records.return_value = ([record], False, "", 1)

    service = ResearchSyncService(
        session=db_session,
        client=mock_client,
        app_token="app123",
        table_id="tbl456",
    )
    result = await service.sync()
    await db_session.commit()

    repo = MachineCycleHistoryRepo(db_session)
    count = await repo.count()
    assert count == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd auto-scheduling-system/services/api && python -m pytest tests/test_sync/test_research_sync.py -v`
Expected: FAIL

- [ ] **Step 3: Implement ResearchSyncService**

```python
# app/sync/research_sync.py
import logging
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.integration.feishu_client import FeishuClient
from app.integration.feishu_field_maps import (
    RESEARCH_FIELDS, extract_feishu_text, extract_feishu_number,
    extract_feishu_timestamp_ms,
)
from app.repository.machine_cycle_history_repo import MachineCycleHistoryRepo
from app.sync.sync_support_utils import SyncResult, start_sync_job, finish_sync_job

logger = logging.getLogger(__name__)


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

    async def sync(
        self,
        last_sync_ms: int | None = None,
        order_no_filter: str | None = None,
    ) -> SyncResult:
        result = SyncResult()
        job = await start_sync_job(self.session, "research", "feishu")

        filter_config = self._build_filter(last_sync_ms, order_no_filter)
        page_token = None

        while True:
            try:
                items, has_more, page_token, total = await self.client.search_records(
                    app_token=self.app_token,
                    table_id=self.table_id,
                    field_names=RESEARCH_FIELDS,
                    filter_config=filter_config,
                    page_token=page_token if page_token else None,
                )
            except Exception as e:
                logger.error(f"Feishu research fetch failed: {e}")
                result.record_fail()
                break

            for item in items:
                try:
                    await self._process_record(item, result)
                except Exception as e:
                    logger.error(f"Research record process failed: {e}")
                    result.record_fail()

            if not has_more:
                break

        await finish_sync_job(self.session, job, result)
        return result

    def _build_filter(
        self, last_sync_ms: int | None, order_no: str | None
    ) -> dict[str, Any] | None:
        conditions = []
        if last_sync_ms:
            conditions.append({
                "field_name": "最后更新时间",
                "operator": "isGreater",
                "value": ["ExactDate", str(last_sync_ms)],
            })
        conditions.append({
            "field_name": "明细-物料编号",
            "operator": "isNotEmpty",
        })
        if order_no:
            conditions.append({
                "field_name": "订单编号",
                "operator": "is",
                "value": [order_no],
            })
        return {"conjunction": "and", "conditions": conditions} if conditions else None

    async def _process_record(self, item: dict, result: SyncResult):
        fields = item.get("fields", {})

        detail_id = extract_feishu_text(fields, "明细ID")
        material_no = extract_feishu_text(fields, "明细-物料编号")

        # Filter empty material
        if not material_no:
            return

        if not detail_id:
            result.record_fail()
            result.record_issue()
            return

        drawing_date = _ms_to_datetime(
            extract_feishu_timestamp_ms(fields, "发图时间（研究所）")
        )
        inspection_date = _ms_to_datetime(
            extract_feishu_timestamp_ms(fields, "报检日期")
        )

        # Calculate cycle_days
        cycle_days = None
        if drawing_date and inspection_date:
            delta = inspection_date - drawing_date
            cycle_days = Decimal(str(delta.days))

        order_qty_raw = extract_feishu_number(fields, "明细-数量")
        order_qty = Decimal(str(order_qty_raw)) if order_qty_raw is not None else Decimal("1")

        data = {
            "machine_material_no": material_no,
            "machine_model": extract_feishu_text(fields, "明细-产品型号") or "",
            "product_series": fields.get("产品大系列") if isinstance(fields.get("产品大系列"), str) else extract_feishu_text(fields, "产品大系列"),
            "order_qty": order_qty,
            "drawing_release_date": drawing_date,
            "inspection_date": inspection_date,
            "custom_no": extract_feishu_text(fields, "定制编号"),
            "customer_name": extract_feishu_text(fields, "客户名称"),
            "contract_no": extract_feishu_text(fields, "合同编号"),
            "order_no": extract_feishu_text(fields, "订单编号"),
            "business_group": fields.get("事业群") if isinstance(fields.get("事业群"), str) else extract_feishu_text(fields, "事业群"),
            "order_type": fields.get("订单类型") if isinstance(fields.get("订单类型"), str) else extract_feishu_text(fields, "订单类型"),
            "cycle_days": cycle_days,
        }

        # Check if exists for insert vs update tracking
        existing = await self.repo.get_by_id(0)  # placeholder
        from sqlalchemy import select
        from app.models.machine_cycle_history import MachineCycleHistorySrc
        stmt = select(MachineCycleHistorySrc).where(MachineCycleHistorySrc.detail_id == detail_id)
        existing = (await self.session.execute(stmt)).scalar_one_or_none()

        await self.repo.upsert_by_detail_id(detail_id, data)

        if existing:
            result.record_update()
        else:
            result.record_insert()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd auto-scheduling-system/services/api && python -m pytest tests/test_sync/test_research_sync.py -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add app/sync/research_sync.py tests/test_sync/test_research_sync.py
git commit -m "feat: add research institute sync service with Feishu integration"
```

---

### Task 7: Sync — Production Order Sync Service

**Files:**
- Create: `auto-scheduling-system/services/api/app/sync/production_order_sync.py`
- Test: `auto-scheduling-system/services/api/tests/test_sync/test_production_order_sync.py`

**Key rules:**
- Pull from Feishu production order table
- Incremental filter on `最后更新时间`
- Upsert by `production_order_no`
- Duplicate production_order_no → record as data issue
- Parse millisecond timestamps to datetime

- [ ] **Step 1: Write failing test**

```python
# tests/test_sync/test_production_order_sync.py
import pytest
from unittest.mock import AsyncMock

from app.sync.production_order_sync_service import ProductionOrderSyncService
from app.repository.production_order_repo import ProductionOrderRepo


def _make_po_record(order_no="PO001", material_no="MAT001", status="已完工",
                     start_ms=1711900800000, finish_ms=1713715200000):
    return {
        "record_id": "rec1",
        "fields": {
            "生产订单号": [{"text": order_no}],
            "物料号": [{"text": material_no}],
            "物料描述": [{"text": "部件A"}],
            "机床型号": [{"text": "MC1-80"}],
            "生产工厂": [{"text": "1000"}],
            "加工部门": "车间一",
            "投产时间": start_ms,
            "完工时间": finish_ms,
            "订货数量": 5,
            "生产订单状态": status,
            "销售订单号": [{"text": "SO001"}],
            "创建时间": 1711900800000,
            "最后更新时间": 1713715200000,
        }
    }


@pytest.mark.asyncio
async def test_sync_inserts_record(db_session):
    mock_client = AsyncMock()
    mock_client.search_records.return_value = (
        [_make_po_record()], False, "", 1
    )

    service = ProductionOrderSyncService(
        session=db_session,
        client=mock_client,
        app_token="app123",
        table_id="tbl456",
    )
    result = await service.sync()
    await db_session.commit()

    repo = ProductionOrderRepo(db_session)
    count = await repo.count()
    assert count == 1
    assert result.insert_count == 1


@pytest.mark.asyncio
async def test_sync_upserts_duplicate(db_session):
    mock_client = AsyncMock()
    mock_client.search_records.return_value = (
        [_make_po_record(), _make_po_record()], False, "", 2
    )

    service = ProductionOrderSyncService(
        session=db_session,
        client=mock_client,
        app_token="app123",
        table_id="tbl456",
    )
    result = await service.sync()
    await db_session.commit()

    repo = ProductionOrderRepo(db_session)
    count = await repo.count()
    assert count == 1
    assert result.issue_count >= 1  # duplicate recorded as issue
```

- [ ] **Step 2: Implement ProductionOrderSyncService**

```python
# app/sync/production_order_sync.py
import logging
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.integration.feishu_client import FeishuClient
from app.integration.feishu_field_maps import (
    PRODUCTION_ORDER_FIELDS, extract_feishu_text, extract_feishu_number,
    extract_feishu_timestamp_ms,
)
from app.models.production_order import ProductionOrderHistorySrc
from app.repository.production_order_repo import ProductionOrderRepo
from app.sync.sync_support_utils import SyncResult, start_sync_job, finish_sync_job

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

    async def sync(self, last_sync_ms: int | None = None) -> SyncResult:
        result = SyncResult()
        job = await start_sync_job(self.session, "production_order", "feishu")
        self._seen_order_nos.clear()

        filter_config = None
        if last_sync_ms:
            filter_config = {
                "conjunction": "and",
                "conditions": [{
                    "field_name": "最后更新时间",
                    "operator": "isGreater",
                    "value": ["ExactDate", str(last_sync_ms)],
                }]
            }

        page_token = None
        while True:
            try:
                items, has_more, page_token, total = await self.client.search_records(
                    app_token=self.app_token,
                    table_id=self.table_id,
                    field_names=PRODUCTION_ORDER_FIELDS,
                    filter_config=filter_config,
                    page_token=page_token if page_token else None,
                )
            except Exception as e:
                logger.error(f"Feishu production order fetch failed: {e}")
                result.record_fail()
                break

            for item in items:
                try:
                    await self._process_record(item, result)
                except Exception as e:
                    logger.error(f"Production order process failed: {e}")
                    result.record_fail()

            if not has_more:
                break

        await finish_sync_job(self.session, job, result)
        return result

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
            "processing_dept": fields.get("加工部门") if isinstance(fields.get("加工部门"), str) else extract_feishu_text(fields, "加工部门"),
            "start_time_actual": _ms_to_datetime(extract_feishu_timestamp_ms(fields, "投产时间")),
            "finish_time_actual": _ms_to_datetime(extract_feishu_timestamp_ms(fields, "完工时间")),
            "production_qty": Decimal(str(qty_raw)) if qty_raw is not None else None,
            "order_status": fields.get("生产订单状态") if isinstance(fields.get("生产订单状态"), str) else extract_feishu_text(fields, "生产订单状态"),
            "sales_order_no": extract_feishu_text(fields, "销售订单号"),
            "created_time_src": _ms_to_datetime(extract_feishu_timestamp_ms(fields, "创建时间")),
            "last_modified_time_src": _ms_to_datetime(extract_feishu_timestamp_ms(fields, "最后更新时间")),
        }

        # Check if exists
        stmt = select(ProductionOrderHistorySrc).where(
            ProductionOrderHistorySrc.production_order_no == order_no
        )
        existing = (await self.session.execute(stmt)).scalar_one_or_none()

        await self.repo.upsert_by_order_no(order_no, data)

        if existing:
            result.record_update()
        else:
            result.record_insert()
```

- [ ] **Step 3: Run tests**

Run: `cd auto-scheduling-system/services/api && python -m pytest tests/test_sync/test_production_order_sync.py -v`
Expected: ALL PASS

- [ ] **Step 4: Commit**

```bash
git add app/sync/production_order_sync.py tests/test_sync/test_production_order_sync.py
git commit -m "feat: add production order sync service with duplicate detection"
```

---

### Task 8: Sync — Drawing Status Backfill Service

**Files:**
- Create: `auto-scheduling-system/services/api/app/sync/drawing_status_sync.py`
- Test: `auto-scheduling-system/services/api/tests/test_sync/test_drawing_status_sync.py`

**Key rules:**
- Match sales_plan_order_line_src records with machine_cycle_history_src
- Primary match by `detail_id`
- Fallback match by `order_no` + `material_no`
- If matched and has `drawing_release_date`, set `drawing_released = True` and populate `drawing_release_date`

- [ ] **Step 1: Write failing test**

```python
# tests/test_sync/test_drawing_status_sync.py
import pytest
from datetime import datetime
from decimal import Decimal

from app.models.sales_plan import SalesPlanOrderLineSrc
from app.models.machine_cycle_history import MachineCycleHistorySrc
from app.sync.drawing_status_sync_service import DrawingStatusSyncService


@pytest.mark.asyncio
async def test_backfill_by_detail_id(db_session):
    # Create a sales order without drawing status
    order = SalesPlanOrderLineSrc(
        sap_code="SAP001", sap_line_no="10",
        contract_no="HT001", detail_id="DT001",
        material_no="MAT001", drawing_released=False,
    )
    db_session.add(order)

    # Create a research record with drawing date
    research = MachineCycleHistorySrc(
        detail_id="DT001", machine_model="MC1-80",
        order_qty=Decimal("1"),
        drawing_release_date=datetime(2026, 3, 15),
    )
    db_session.add(research)
    await db_session.commit()

    service = DrawingStatusSyncService(db_session)
    count = await service.refresh_all()
    await db_session.commit()

    await db_session.refresh(order)
    assert order.drawing_released is True
    assert order.drawing_release_date == datetime(2026, 3, 15)
    assert count == 1


@pytest.mark.asyncio
async def test_no_match_no_update(db_session):
    order = SalesPlanOrderLineSrc(
        sap_code="SAP001", sap_line_no="10",
        contract_no="HT001", detail_id="DT_NO_MATCH",
        material_no="MAT001", drawing_released=False,
    )
    db_session.add(order)
    await db_session.commit()

    service = DrawingStatusSyncService(db_session)
    count = await service.refresh_all()
    await db_session.commit()

    await db_session.refresh(order)
    assert order.drawing_released is False
    assert count == 0
```

- [ ] **Step 2: Implement DrawingStatusSyncService**

```python
# app/sync/drawing_status_sync.py
import logging
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.sales_plan import SalesPlanOrderLineSrc
from app.models.machine_cycle_history import MachineCycleHistorySrc

logger = logging.getLogger(__name__)


class DrawingStatusSyncService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def refresh_all(self) -> int:
        """Refresh drawing status for all undrawn sales orders. Returns count updated."""
        stmt = select(SalesPlanOrderLineSrc).where(
            SalesPlanOrderLineSrc.drawing_released == False
        )
        result = await self.session.execute(stmt)
        orders = result.scalars().all()

        updated = 0
        for order in orders:
            if await self._try_backfill(order):
                updated += 1

        await self.session.flush()
        return updated

    async def refresh_by_order_ids(self, order_ids: list[int]) -> int:
        """Refresh drawing status for specific order line IDs."""
        stmt = select(SalesPlanOrderLineSrc).where(
            SalesPlanOrderLineSrc.id.in_(order_ids)
        )
        result = await self.session.execute(stmt)
        orders = result.scalars().all()

        updated = 0
        for order in orders:
            if await self._try_backfill(order):
                updated += 1

        await self.session.flush()
        return updated

    async def _try_backfill(self, order: SalesPlanOrderLineSrc) -> bool:
        """Try to backfill drawing status from research data. Returns True if updated."""
        research = None

        # Primary: match by detail_id
        if order.detail_id:
            stmt = select(MachineCycleHistorySrc).where(
                MachineCycleHistorySrc.detail_id == order.detail_id
            )
            research = (await self.session.execute(stmt)).scalar_one_or_none()

        # Fallback: match by order_no + material_no
        if not research and order.order_no and order.material_no:
            stmt = select(MachineCycleHistorySrc).where(
                and_(
                    MachineCycleHistorySrc.order_no == order.order_no,
                    MachineCycleHistorySrc.machine_material_no == order.material_no,
                )
            )
            research = (await self.session.execute(stmt)).scalar_one_or_none()

        if research and research.drawing_release_date:
            order.drawing_released = True
            order.drawing_release_date = research.drawing_release_date
            return True

        return False
```

- [ ] **Step 3: Run tests**

Run: `cd auto-scheduling-system/services/api && python -m pytest tests/test_sync/test_drawing_status_sync.py -v`
Expected: ALL PASS

- [ ] **Step 4: Commit**

```bash
git add app/sync/drawing_status_sync.py tests/test_sync/test_drawing_status_sync.py
git commit -m "feat: add drawing status backfill service with detail_id and fallback match"
```

---

### Task 9: Sync — BOM Sync Service

**Files:**
- Create: `auto-scheduling-system/services/api/app/sync/bom_sync.py`
- Test: `auto-scheduling-system/services/api/tests/test_sync/test_bom_sync.py`

**Key rules:**
- Delete existing BOM rows by `machine_material_no + plant` then insert new ones
- Build BOM tree from flat list: use `material_no` (parent) and `bom_component_no` (child)
- Compute `bom_level` field
- Mark `is_top_level` for level 1
- Mark `is_self_made` from part_type

- [ ] **Step 1: Write failing test**

```python
# tests/test_sync/test_bom_sync.py
import pytest
from unittest.mock import AsyncMock
from decimal import Decimal

from app.models.bom_relation import BomRelationSrc
from app.sync.bom_sync_service import BomSyncService
from app.repository.bom_relation_repo import BomRelationRepo


@pytest.mark.asyncio
async def test_sync_bom_delete_insert(db_session):
    # Pre-insert old BOM data
    db_session.add(BomRelationSrc(
        machine_material_no="MACH001", plant="1000",
        bom_component_no="OLD_COMP", bom_level=1,
    ))
    await db_session.commit()

    mock_client = AsyncMock()
    mock_client.fetch_bom.return_value = [
        {
            "machine_material_no": "MACH001",
            "machine_material_desc": "压力机",
            "material_no": "MACH001",
            "material_desc": "压力机",
            "plant": "1000",
            "bom_component_no": "COMP001",
            "bom_component_desc": "机身MC1-80",
            "part_type": "自产件",
            "component_qty": Decimal("1"),
            "is_self_made": True,
        },
        {
            "machine_material_no": "MACH001",
            "machine_material_desc": "压力机",
            "material_no": "MACH001",
            "material_desc": "压力机",
            "plant": "1000",
            "bom_component_no": "COMP002",
            "bom_component_desc": "电气柜",
            "part_type": "外购件",
            "component_qty": Decimal("2"),
            "is_self_made": False,
        },
    ]

    service = BomSyncService(db_session, mock_client)
    result = await service.sync_for_order(
        machine_material_no="MACH001", plant="1000"
    )
    await db_session.commit()

    repo = BomRelationRepo(db_session)
    rows = await repo.find_by_machine("MACH001")
    # Old data should be deleted, 2 new rows inserted
    assert len(rows) == 2
    assert result.success_count == 2


@pytest.mark.asyncio
async def test_bom_level_assignment(db_session):
    mock_client = AsyncMock()
    # Simulate a 2-level BOM: MACH001 -> COMP001 -> SUBCOMP001
    mock_client.fetch_bom.return_value = [
        {
            "machine_material_no": "MACH001",
            "machine_material_desc": "压力机",
            "material_no": "MACH001",
            "material_desc": "压力机",
            "plant": "1000",
            "bom_component_no": "COMP001",
            "bom_component_desc": "机身",
            "part_type": "自产件",
            "component_qty": Decimal("1"),
            "is_self_made": True,
        },
        {
            "machine_material_no": "MACH001",
            "machine_material_desc": "压力机",
            "material_no": "COMP001",
            "material_desc": "机身",
            "plant": "1000",
            "bom_component_no": "SUBCOMP001",
            "bom_component_desc": "铸件",
            "part_type": "自产件",
            "component_qty": Decimal("1"),
            "is_self_made": True,
        },
    ]

    service = BomSyncService(db_session, mock_client)
    await service.sync_for_order(machine_material_no="MACH001", plant="1000")
    await db_session.commit()

    repo = BomRelationRepo(db_session)
    rows = await repo.find_by_machine("MACH001")
    level_map = {r.bom_component_no: r.bom_level for r in rows}
    assert level_map["COMP001"] == 1  # direct child of machine
    assert level_map["SUBCOMP001"] == 2  # child of COMP001
```

- [ ] **Step 2: Implement BomSyncService**

```python
# app/sync/bom_sync.py
import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.integration.sap_bom_client import SapBomClient
from app.models.bom_relation import BomRelationSrc
from app.repository.bom_relation_repo import BomRelationRepo
from app.sync.sync_support_utils import SyncResult, start_sync_job, finish_sync_job

logger = logging.getLogger(__name__)


def _compute_bom_levels(
    rows: list[dict[str, Any]], machine_material_no: str
) -> list[dict[str, Any]]:
    """Compute bom_level for each row based on parent-child relationships."""
    # Build parent→children map
    children_of: dict[str, list[dict]] = {}
    for row in rows:
        parent = row["material_no"]
        children_of.setdefault(parent, []).append(row)

    # BFS from machine root
    level_map: dict[str, int] = {}
    queue = [(machine_material_no, 0)]
    while queue:
        parent, parent_level = queue.pop(0)
        for child in children_of.get(parent, []):
            comp = child["bom_component_no"]
            child_level = parent_level + 1
            if comp not in level_map:
                level_map[comp] = child_level
                queue.append((comp, child_level))

    for row in rows:
        comp = row["bom_component_no"]
        row["bom_level"] = level_map.get(comp, 1)
        row["is_top_level"] = row["bom_level"] == 1

    return rows


class BomSyncService:
    def __init__(self, session: AsyncSession, client: SapBomClient):
        self.session = session
        self.client = client
        self.repo = BomRelationRepo(session)

    async def sync_for_order(
        self, machine_material_no: str, plant: str
    ) -> SyncResult:
        result = SyncResult()
        job = await start_sync_job(self.session, "bom", "sap")

        try:
            raw_rows = await self.client.fetch_bom(machine_material_no, plant)
        except Exception as e:
            logger.error(f"SAP BOM fetch failed for {machine_material_no}: {e}")
            result.record_fail()
            await finish_sync_job(self.session, job, result, str(e))
            return result

        # Compute levels
        rows_with_levels = _compute_bom_levels(raw_rows, machine_material_no)

        # Delete existing, then insert
        await self.repo.delete_by_machine_and_plant(machine_material_no, plant)

        from datetime import datetime
        entities = []
        for row in rows_with_levels:
            entities.append(BomRelationSrc(
                machine_material_no=row["machine_material_no"],
                machine_material_desc=row.get("machine_material_desc"),
                plant=row.get("plant"),
                material_no=row.get("material_no"),
                material_desc=row.get("material_desc"),
                bom_component_no=row["bom_component_no"],
                bom_component_desc=row.get("bom_component_desc"),
                part_type=row.get("part_type"),
                component_qty=row.get("component_qty"),
                bom_level=row.get("bom_level", 1),
                is_top_level=row.get("is_top_level", False),
                is_self_made=row.get("is_self_made", False),
                sync_time=datetime.now(),
            ))

        if entities:
            await self.repo.add_all(entities)
            for _ in entities:
                result.record_insert()

        await finish_sync_job(self.session, job, result)
        return result

    async def sync_batch(
        self, items: list[tuple[str, str]]
    ) -> SyncResult:
        """Sync BOM for multiple (machine_material_no, plant) pairs."""
        total_result = SyncResult()
        for machine_material_no, plant in items:
            r = await self.sync_for_order(machine_material_no, plant)
            total_result.success_count += r.success_count
            total_result.fail_count += r.fail_count
            total_result.insert_count += r.insert_count
        return total_result
```

- [ ] **Step 3: Run tests**

Run: `cd auto-scheduling-system/services/api && python -m pytest tests/test_sync/test_bom_sync.py -v`
Expected: ALL PASS

- [ ] **Step 4: Commit**

```bash
git add app/sync/bom_sync.py tests/test_sync/test_bom_sync.py
git commit -m "feat: add BOM sync service with delete-insert and level computation"
```

---

### Task 10: Run Full Test Suite + Final Commit

- [ ] **Step 1: Run all tests**

Run: `cd auto-scheduling-system/services/api && python -m pytest tests/ -v --tb=short`
Expected: ALL PASS (approx 35-45 tests)

- [ ] **Step 2: Final commit if anything missed**

```bash
git status
# If clean, no commit needed
```

---

## Phase 2 Completion Checklist

After completing all tasks above, you should have:

- [x] SyncResult helper + sync job logging
- [x] GuandataClient: auth + sales plan pagination + field mapping
- [x] FeishuClient: auth + bitable search with pagination + field helpers
- [x] SapBomClient: BOM fetch + field mapping + top-level filtering
- [x] SalesPlanSyncService: paginated sync with upsert
- [x] ResearchSyncService: incremental Feishu sync with cycle_days calculation
- [x] ProductionOrderSyncService: incremental sync with duplicate detection
- [x] DrawingStatusSyncService: backfill by detail_id + fallback match
- [x] BomSyncService: delete-insert with BOM level computation
- [x] Full test suite passing

**Next:** Proceed to Phase 3 plan (Baseline + Scheduler layer).
