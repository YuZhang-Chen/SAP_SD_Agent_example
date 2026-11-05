from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal

from sap_sd_agent.odata.models import (
    CreateSalesOrderInput,
    SalesOrderItemInput,
    format_odata_date,
    parse_odata_datetime,
)


def test_parse_and_format_odata_date() -> None:
    assert parse_odata_datetime("/Date(1507248000000)/") == datetime(
        2017, 10, 6, tzinfo=timezone.utc
    )
    assert format_odata_date(date(2026, 11, 12)) == "/Date(1794441600000)/"


def test_create_payload_uses_v2_deep_insert_shape() -> None:
    order = CreateSalesOrderInput(
        sales_order_type="訂單",
        sales_organization="1710",
        distribution_channel="10",
        organization_division="00",
        sold_to_party="17100003",
        requested_delivery_date=date(2026, 11, 12),
        transaction_currency="USD",
        purchase_order_by_customer="DEMO-001",
        items=[
            SalesOrderItemInput(
                material="TG11",
                requested_quantity=Decimal("2.5"),
                requested_quantity_unit="PC",
                production_plant="1710",
            )
        ],
    )

    payload = order.to_odata_payload()

    assert payload["SoldToParty"] == "17100003"
    assert payload["RequestedDeliveryDate"] == "/Date(1794441600000)/"
    assert payload["to_Item"]["results"] == [
        {
            "Material": "TG11",
            "RequestedQuantity": "2.5",
            "RequestedQuantityUnit": "PC",
            "ProductionPlant": "1710",
        }
    ]
