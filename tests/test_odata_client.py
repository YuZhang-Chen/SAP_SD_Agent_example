from __future__ import annotations

import json
from datetime import date
from decimal import Decimal
from typing import Any

import httpx
import pytest
from pydantic import SecretStr

from sap_sd_agent.config import SapSettings
from sap_sd_agent.odata.client import SapODataClient
from sap_sd_agent.odata.errors import SapAuthenticationError, SapODataError
from sap_sd_agent.odata.models import CreateSalesOrderInput, SalesOrderItemInput


def settings() -> SapSettings:
    return SapSettings(
        user="demo",
        password=SecretStr("secret"),
        client="600",
        language="ZF",
        base_url="https://sap.example.test/sap/opu/odata/sap/API_SALES_ORDER_SRV",
        verify_tls=False,
    )


def test_metadata_and_search_encode_odata_query() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path.endswith("/$metadata"):
            return httpx.Response(200, text="<edmx:Edmx />")
        return httpx.Response(
            200,
            json={
                "d": {
                    "results": [
                        {
                            "SalesOrder": "2",
                            "SalesOrderType": "訂單",
                            "SalesOrderDate": "/Date(1507248000000)/",
                            "SoldToParty": "O'Reilly",
                            "TotalNetAmount": "125.50",
                            "TransactionCurrency": "USD",
                            "OverallSDProcessStatus": "C",
                            "OverallDeliveryStatus": "B",
                        }
                    ]
                }
            },
        )

    with SapODataClient(settings(), transport=httpx.MockTransport(handler)) as client:
        assert client.get_metadata() == "<edmx:Edmx />"
        orders = client.search_sales_orders(
            sold_to_party="O'Reilly",
            date_from=date(2026, 1, 1),
            date_to=date(2026, 12, 31),
            limit=3,
        )

    assert orders[0].sales_order == "2"
    assert orders[0].total_net_amount == Decimal("125.50")
    assert requests[0].headers["sap-client"] == "600"
    query = dict(requests[1].url.params.multi_items())
    assert query["$top"] == "3"
    assert "SoldToParty eq 'O''Reilly'" in query["$filter"]
    assert "SalesOrderDate ge datetime'2026-01-01T00:00:00'" in query["$filter"]


def test_get_sales_order_parses_expanded_items() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/A_SalesOrder('2')")
        assert request.url.params["$expand"] == "to_Item"
        return httpx.Response(
            200,
            json={
                "d": {
                    "SalesOrder": "2",
                    "SalesOrderType": "訂單",
                    "SalesOrganization": "1710",
                    "DistributionChannel": "10",
                    "OrganizationDivision": "00",
                    "SoldToParty": "17100003",
                    "RequestedDeliveryDate": "/Date(1507248000000)/",
                    "to_Item": {
                        "results": [
                            {
                                "SalesOrderItem": "10",
                                "Material": "TG11",
                                "RequestedQuantity": "10",
                                "RequestedQuantityUnit": "PC",
                                "ProductionPlant": "1710",
                            }
                        ]
                    },
                }
            },
        )

    with SapODataClient(settings(), transport=httpx.MockTransport(handler)) as client:
        order = client.get_sales_order("2")

    assert order.sales_organization == "1710"
    assert order.items[0].material == "TG11"
    assert order.items[0].requested_quantity == Decimal("10")


def test_create_fetches_csrf_and_posts_deep_insert() -> None:
    posted: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "GET":
            assert request.headers["X-CSRF-Token"] == "Fetch"
            return httpx.Response(
                200,
                headers={
                    "X-CSRF-Token": "csrf-value",
                    "Set-Cookie": "SAP_SESSIONID=abc; Path=/",
                },
                json={"d": {}},
            )
        posted["headers"] = request.headers
        posted["json"] = json.loads(request.content)
        return httpx.Response(
            201,
            json={
                "d": {
                    "SalesOrder": "900001",
                    "SoldToParty": "17100003",
                    "to_Item": {"results": []},
                }
            },
        )

    order = CreateSalesOrderInput(
        sales_order_type="訂單",
        sales_organization="1710",
        distribution_channel="10",
        organization_division="00",
        sold_to_party="17100003",
        requested_delivery_date=date(2026, 11, 12),
        items=[
            SalesOrderItemInput(
                material="TG11",
                requested_quantity=Decimal("1"),
            )
        ],
    )

    with SapODataClient(settings(), transport=httpx.MockTransport(handler)) as client:
        created = client.create_sales_order(order)

    assert created.sales_order == "900001"
    assert posted["headers"]["X-CSRF-Token"] == "csrf-value"
    assert "SAP_SESSIONID=abc" in posted["headers"]["Cookie"]
    assert posted["json"]["to_Item"]["results"][0]["Material"] == "TG11"


@pytest.mark.parametrize("status", [401, 403])
def test_authentication_errors_are_normalized(status: int) -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            status,
            json={"error": {"code": "AUTH", "message": {"value": "Denied"}}},
        )

    with SapODataClient(settings(), transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(SapAuthenticationError, match="Denied") as exc_info:
            client.get_metadata()

    assert exc_info.value.status_code == status
    assert exc_info.value.code == "AUTH"


def test_missing_csrf_token_fails_closed() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"d": {}})

    order = CreateSalesOrderInput(
        sales_order_type="訂單",
        sales_organization="1710",
        distribution_channel="10",
        organization_division="00",
        sold_to_party="17100003",
        requested_delivery_date=date(2026, 11, 12),
        items=[SalesOrderItemInput(material="TG11", requested_quantity=1)],
    )
    with SapODataClient(settings(), transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(SapODataError, match="X-CSRF-Token"):
            client.create_sales_order(order)
