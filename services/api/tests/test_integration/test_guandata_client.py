import json

import httpx
import pytest
import respx

from app.integration.guandata_client import GuandataClient


@pytest.fixture
def client():
    client = GuandataClient(
        base_url="https://guandata.example.com",
        domain="test_domain",
        login_id="test_user",
        password="test_pass",
        ds_id="test_ds",
    )
    client.http_client.max_retries = 1
    client.http_client.retry_backoff_seconds = 0
    return client


@respx.mock
@pytest.mark.asyncio
async def test_authenticate(client):
    respx.post("https://guandata.example.com/public-api/sign-in").mock(
        return_value=httpx.Response(200, json={"response": {"token": "tok123", "expireAt": "2099-01-01 00:00:00.000"}})
    )
    token = await client.authenticate()
    assert token == "tok123"


@respx.mock
@pytest.mark.asyncio
async def test_fetch_sales_page(client):
    respx.post("https://guandata.example.com/public-api/sign-in").mock(
        return_value=httpx.Response(200, json={"response": {"token": "tok123", "expireAt": "2099-01-01 00:00:00.000"}})
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

    data_route = respx.post("https://guandata.example.com/public-api/data-source/test_ds/data").mock(
        return_value=httpx.Response(
            200,
            json={
                "response": {
                    "preview": [row],
                    "rowCount": 1,
                }
            },
        )
    )

    records, total = await client.fetch_sales_page(
        offset=0,
        limit=100,
        filters={
            "combineType": "AND",
            "conditions": [
                {
                    "type": "condition",
                    "value": {"name": "订单明细-确认交货期", "filterType": "NOT_NULL"},
                }
            ],
        },
    )
    assert total == 1
    assert len(records) == 1
    assert records[0]["contract_no"] == "HT001"
    assert records[0]["detail_id"] == "DT001"
    assert records[0]["order_no"] == "SO001"
    assert records[0]["sap_code"] == "SAP001"
    assert records[0]["material_no"] == "MAT001"
    assert json.loads(data_route.calls.last.request.content.decode("utf-8")) == {
        "offset": 0,
        "limit": 100,
        "filter": {
            "combineType": "AND",
            "conditions": [
                {
                    "type": "condition",
                    "value": {"name": "订单明细-确认交货期", "filterType": "NOT_NULL"},
                }
            ],
        },
    }


@respx.mock
@pytest.mark.asyncio
async def test_fetch_empty_page(client):
    respx.post("https://guandata.example.com/public-api/sign-in").mock(
        return_value=httpx.Response(200, json={"response": {"token": "tok123", "expireAt": "2099-01-01 00:00:00.000"}})
    )
    respx.post("https://guandata.example.com/public-api/data-source/test_ds/data").mock(
        return_value=httpx.Response(200, json={"response": {"preview": [], "rowCount": 0}})
    )
    records, total = await client.fetch_sales_page(offset=0, limit=100)
    assert total == 0
    assert len(records) == 0


@respx.mock
@pytest.mark.asyncio
async def test_authenticate_reuses_string_expire_at_token(client):
    sign_in_route = respx.post("https://guandata.example.com/public-api/sign-in").mock(
        return_value=httpx.Response(200, json={"response": {"token": "tok123", "expireAt": "2099-01-01 00:00:00.000"}})
    )
    token1 = await client.authenticate()
    token2 = await client.authenticate()
    assert token1 == "tok123"
    assert token2 == "tok123"
    assert sign_in_route.call_count == 1


@respx.mock
@pytest.mark.asyncio
async def test_fetch_sales_page_retries_after_401(client):
    sign_in_route = respx.post("https://guandata.example.com/public-api/sign-in").mock(
        side_effect=[
            httpx.Response(200, json={"response": {"token": "tok123", "expireAt": "2099-01-01 00:00:00.000"}}),
            httpx.Response(200, json={"response": {"token": "tok456", "expireAt": "2099-01-01 00:00:00.000"}}),
        ]
    )
    row = [""] * 142
    row[2] = "HT001"
    row[70] = "SAP001"
    row[71] = "10"

    data_route = respx.post("https://guandata.example.com/public-api/data-source/test_ds/data").mock(
        side_effect=[
            httpx.Response(401, json={"message": "unauthorized"}),
            httpx.Response(200, json={"response": {"preview": [row], "rowCount": 1}}),
        ]
    )

    records, total = await client.fetch_sales_page(offset=0, limit=100)
    assert total == 1
    assert len(records) == 1
    assert sign_in_route.call_count == 2
    assert data_route.call_count == 2


@respx.mock
@pytest.mark.asyncio
async def test_authenticate_retries_on_retryable_status(client):
    route = respx.post("https://guandata.example.com/public-api/sign-in").mock(
        side_effect=[
            httpx.Response(503, json={"message": "busy"}),
            httpx.Response(200, json={"response": {"token": "tok789", "expireAt": "2099-01-01 00:00:00.000"}}),
        ]
    )

    token = await client.authenticate()

    assert token == "tok789"
    assert route.call_count == 2
