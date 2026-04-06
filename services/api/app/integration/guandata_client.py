import asyncio
import logging
import time
from datetime import datetime
from typing import Any

import httpx

from app.integration.http_client import ExternalHttpClient

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


def _parse_expire_at(value: Any) -> float:
    """Parse Guandata expireAt to millisecond Unix timestamp."""
    if value is None:
        return 0
    if isinstance(value, (int, float)):
        # Guandata may return seconds or milliseconds; normalise to ms
        ts = float(value)
        if ts < 1e12:  # looks like seconds
            ts *= 1000
        return ts
    if isinstance(value, str):
        from zoneinfo import ZoneInfo

        cst = ZoneInfo("Asia/Shanghai")
        for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S"):
            try:
                # Guandata returns CST times; attach timezone before .timestamp()
                return datetime.strptime(value, fmt).replace(tzinfo=cst).timestamp() * 1000
            except ValueError:
                continue
        try:
            return float(value)
        except ValueError:
            logger.warning("Unsupported Guandata expireAt format: %s", value)
    return 0


def _parse_total_count(response_data: dict[str, Any]) -> int:
    for field in ("rowCount", "totalCount", "total_count", "total", "count"):
        value = response_data.get(field)
        if value in (None, ""):
            continue
        try:
            return int(value)
        except (TypeError, ValueError):
            logger.warning("Invalid Guandata total count field %s=%s", field, value)
    return 0


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
        self._token_lock = asyncio.Lock()
        self.http_client = ExternalHttpClient("guandata")

    async def authenticate(self) -> str:
        if self._token and self._token_expire > time.time() * 1000:
            return self._token
        async with self._token_lock:
            # Double-check after acquiring lock
            if self._token and self._token_expire > time.time() * 1000:
                return self._token
            return await self._do_authenticate()

    async def _do_authenticate(self) -> str:
        resp = await self.http_client.request(
            "POST",
            f"{self.base_url}/public-api/sign-in",
            json={
                "domain": self.domain,
                "loginId": self.login_id,
                "password": self.password,
            },
        )
        resp.raise_for_status()
        data = resp.json()["response"]
        self._token = data["token"]
        self._token_expire = _parse_expire_at(data.get("expireAt"))
        return self._token

    async def fetch_sales_page(
        self,
        offset: int = 0,
        limit: int = 200,
        filters: dict[str, Any] | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        """Fetch one page of sales plan data. Returns (records, totalCount)."""
        body: dict[str, Any] = {
            "offset": offset,
            "limit": limit,
        }
        if filters:
            body["filter"] = filters

        resp = await self._post_sales_page(body)

        response_data = resp.json()["response"]
        preview_rows = response_data.get("preview", [])
        total_count = _parse_total_count(response_data)

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

    async def _post_sales_page(self, body: dict[str, Any]) -> httpx.Response:
        token = await self.authenticate()
        url = f"{self.base_url}/public-api/data-source/{self.ds_id}/data"
        resp = await self.http_client.request(
            "POST",
            url,
            json=body,
            headers={"X-Auth-Token": token},
        )
        if resp.status_code == 401:
            logger.warning("Guandata token unauthorized, retrying with a fresh token.")
            self._token = None
            self._token_expire = 0
            fresh_token = await self.authenticate()
            resp = await self.http_client.request(
                "POST",
                url,
                json=body,
                headers={"X-Auth-Token": fresh_token},
                retry_on_status_codes=set(),
            )
        resp.raise_for_status()
        return resp
