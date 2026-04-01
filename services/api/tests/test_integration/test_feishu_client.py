import pytest
import httpx
import respx
from app.integration.feishu_client import FeishuClient


@pytest.fixture
def client():
    client = FeishuClient(
        app_id="test_app",
        app_secret="test_secret",
    )
    client.http_client.max_retries = 1
    client.http_client.retry_backoff_seconds = 0
    return client


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

    request = respx.calls.last.request
    assert request.content == b"{}"


@respx.mock
@pytest.mark.asyncio
async def test_get_token_retries_on_request_error(client):
    route = respx.post("https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal").mock(
        side_effect=[
            httpx.ReadTimeout("timeout"),
            httpx.Response(200, json={
                "code": 0,
                "tenant_access_token": "t-retry-ok",
                "expire": 7200,
            }),
        ]
    )

    token = await client.get_token()

    assert token == "t-retry-ok"
    assert route.call_count == 2
