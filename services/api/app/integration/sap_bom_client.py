import logging
from typing import Any
from decimal import Decimal

from app.integration.http_client import ExternalHttpClient
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


def _normalize_text(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)


class SapBomClient:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
        self.http_client = ExternalHttpClient("sap_bom")

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
        resp = await self.http_client.request(
            "POST",
            self.base_url,
            json=body,
        )
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
                value = item.get(sap_key)
                if sys_key in {
                    "machine_material_no",
                    "machine_material_desc",
                    "material_no",
                    "material_desc",
                    "plant",
                    "bom_component_no",
                    "bom_component_desc",
                    "part_type",
                }:
                    value = _normalize_text(value)
                mapped[sys_key] = value

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
