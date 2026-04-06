import asyncio
import logging
import time
from typing import Any

from app.integration.http_client import ExternalHttpClient

logger = logging.getLogger(__name__)

FEISHU_BASE_URL = "https://open.feishu.cn"


class FeishuClient:
    def __init__(self, app_id: str, app_secret: str):
        self.app_id = app_id
        self.app_secret = app_secret
        self._token: str | None = None
        self._token_expire: float = 0
        self._token_lock = asyncio.Lock()
        self.http_client = ExternalHttpClient("feishu")

    async def get_token(self) -> str:
        if self._token and time.time() < self._token_expire:
            return self._token
        async with self._token_lock:
            # Double-check after acquiring lock
            if self._token and time.time() < self._token_expire:
                return self._token
            return await self._refresh_token()

    async def _refresh_token(self) -> str:
        resp = await self.http_client.request(
            "POST",
            f"{FEISHU_BASE_URL}/open-apis/auth/v3/tenant_access_token/internal",
            json={"app_id": self.app_id, "app_secret": self.app_secret},
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get("code") != 0:
            raise RuntimeError(f"Feishu auth error: {data.get('msg', 'unknown')}")
        self._token = data["tenant_access_token"]
        self._token_expire = time.time() + data["expire"] - 60
        return self._token

    async def search_records(
        self,
        app_token: str,
        table_id: str,
        field_names: list[str] | None = None,
        filter_config: dict[str, Any] | None = None,
        page_token: str | None = None,
        page_size: int = 500,
    ) -> tuple[list[dict], bool, str, int]:
        """Search bitable records. Returns (items, has_more, page_token, total)."""
        token = await self.get_token()
        # 2026-03-18 real integration note:
        # current live Feishu Bitable `records/search` rejects `field_names`
        # and legacy `filter.conditions[].field_name` payloads used in the
        # original design. To keep the sync chain available, we currently use
        # server-side pagination only and do local field projection / filtering
        # in sync services.
        body: dict[str, Any] = {}
        query = f"user_id_type=user_id&page_size={page_size}"
        if page_token:
            query += f"&page_token={page_token}"

        url = f"{FEISHU_BASE_URL}/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records/search?{query}"
        resp = await self.http_client.request(
            "POST",
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
