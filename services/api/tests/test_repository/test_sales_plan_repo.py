from decimal import Decimal

import pytest

from app.models import SalesPlanOrderLineSrc
from app.repository.sales_plan_repo import SalesPlanRepo


@pytest.mark.asyncio
async def test_upsert_insert(db_session):
    repo = SalesPlanRepo(db_session)
    row = await repo.upsert_by_sap_key(
        sap_code="SAP001",
        sap_line_no="10",
        data={"contract_no": "HT001", "customer_name": "客户A", "quantity": Decimal("1")},
    )
    await db_session.commit()
    assert row.id is not None
    assert row.contract_no == "HT001"


@pytest.mark.asyncio
async def test_upsert_update(db_session):
    repo = SalesPlanRepo(db_session)
    await repo.upsert_by_sap_key(
        sap_code="SAP001", sap_line_no="10", data={"contract_no": "HT001", "customer_name": "客户A"}
    )
    await db_session.commit()

    await repo.upsert_by_sap_key(
        sap_code="SAP001", sap_line_no="10", data={"contract_no": "HT001", "customer_name": "客户B"}
    )
    await db_session.commit()

    count = await repo.count()
    assert count == 1

    rows = await repo.list_all()
    assert rows[0].customer_name == "客户B"


@pytest.mark.asyncio
async def test_paginate(db_session):
    repo = SalesPlanRepo(db_session)
    for i in range(5):
        db_session.add(
            SalesPlanOrderLineSrc(
                sap_code=f"SAP{i:03d}", sap_line_no="10", contract_no=f"HT{i:03d}", customer_name=f"客户{i}"
            )
        )
    await db_session.commit()

    items, total = await repo.paginate(page_no=1, page_size=2)
    assert total == 5
    assert len(items) == 2
