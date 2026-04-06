import httpx
import pytest
import respx

from app.integration.sap_bom_client import SapBomClient


@pytest.fixture
def client():
    client = SapBomClient(base_url="https://sap.example.com")
    client.http_client.max_retries = 1
    client.http_client.retry_backoff_seconds = 0
    return client


@respx.mock
@pytest.mark.asyncio
async def test_fetch_bom_success(client):
    respx.post("https://sap.example.com").mock(
        return_value=httpx.Response(
            200,
            json={
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
                },
            },
        )
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
        return_value=httpx.Response(
            200, json={"ES_RET": {"CODE": "E", "MSG": "物料号不存在"}, "LT_BOM001": {"item": []}}
        )
    )
    with pytest.raises(RuntimeError, match="物料号不存在"):
        await client.fetch_bom(machine_material_no="BADMAT", plant="1000")


@respx.mock
@pytest.mark.asyncio
async def test_fetch_bom_normalizes_numeric_ids_to_string(client):
    respx.post("https://sap.example.com").mock(
        return_value=httpx.Response(
            200,
            json={
                "ES_RET": {"CODE": "", "MSG": ""},
                "LT_BOM001": {
                    "item": [
                        {
                            "ZJBM": 80077824,
                            "ZJMS": "整机",
                            "WLBH": 30683056,
                            "WLBHMS": "机身",
                            "GC": 1100,
                            "BOMZJ": 10005721,
                            "BOMMS": "电缆线",
                            "LJLX": "外购件",
                            "ZJSL": "1.7",
                        }
                    ]
                },
            },
        )
    )

    rows = await client.fetch_bom(machine_material_no="MACH001", plant="1000")
    assert rows[0]["machine_material_no"] == "80077824"
    assert rows[0]["material_no"] == "30683056"
    assert rows[0]["plant"] == "1100"
    assert rows[0]["bom_component_no"] == "10005721"


@respx.mock
@pytest.mark.asyncio
async def test_fetch_bom_retries_on_retryable_status(client):
    route = respx.post("https://sap.example.com").mock(
        side_effect=[
            httpx.Response(502, json={"message": "bad gateway"}),
            httpx.Response(
                200,
                json={
                    "ES_RET": {"CODE": "", "MSG": ""},
                    "LT_BOM001": {
                        "item": [
                            {
                                "ZJBM": "MACH001",
                                "ZJMS": "整机",
                                "WLBH": "MACH001",
                                "WLBHMS": "整机",
                                "GC": "1000",
                                "BOMZJ": "COMP001",
                                "BOMMS": "部件",
                                "LJLX": "自产件",
                                "ZJSL": "1",
                            }
                        ]
                    },
                },
            ),
        ]
    )

    rows = await client.fetch_bom(machine_material_no="MACH001", plant="1000")

    assert len(rows) == 1
    assert rows[0]["bom_component_no"] == "COMP001"
    assert route.call_count == 2
