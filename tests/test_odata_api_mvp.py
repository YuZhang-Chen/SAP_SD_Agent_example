import json
from datetime import date

import httpx

from sap_sd_agent.odata_api import (
    build_order_payload,
    create_sales_order,
    get_sales_order,
    search_sales_orders,
)


def sap_config():
    return {
        "user": "demo",
        "password": "secret",
        "client": "600",
        "language": "ZF",
        "base_url": "https://sap.example.test/odata",
        "verify_tls": False,
        "timeout": 20,
        "sales_order_type": "訂單",
        "sales_organization": "1710",
        "distribution_channel": "10",
        "organization_division": "00",
        "currency": "USD",
        "quantity_unit": "PC",
    }


def test_search_sales_orders_builds_filter():
    def fake_sap(request):
        assert request.url.params["$top"] == "3"
        assert "SoldToParty eq '17100003'" in request.url.params["$filter"]
        return httpx.Response(
            200,
            json={"d": {"results": [{"SalesOrder": "2"}]}},
        )

    orders = search_sales_orders(
        sap_config(),
        sold_to_party="17100003",
        date_from=date(2026, 1, 1),
        limit=3,
        transport=httpx.MockTransport(fake_sap),
    )

    assert orders == [{"SalesOrder": "2"}]


def test_get_sales_order_expands_items():
    def fake_sap(request):
        assert request.url.path.endswith("/A_SalesOrder('2')")
        assert request.url.params["$expand"] == "to_Item"
        return httpx.Response(
            200,
            json={
                "d": {
                    "SalesOrder": "2",
                    "to_Item": {"results": [{"Material": "TG11"}]},
                }
            },
        )

    order = get_sales_order(
        sap_config(),
        "2",
        transport=httpx.MockTransport(fake_sap),
    )

    assert order["to_Item"]["results"][0]["Material"] == "TG11"


def test_build_order_payload_is_easy_to_read():
    payload = build_order_payload(
        sap_config(),
        sold_to_party="17100003",
        requested_delivery_date="2026-11-12",
        items=[{"material": "TG11", "quantity": 2, "plant": "1710"}],
        customer_reference="DEMO-001",
    )

    assert payload["SoldToParty"] == "17100003"
    assert payload["RequestedDeliveryDate"] == "/Date(1794441600000)/"
    assert payload["to_Item"]["results"] == [
        {
            "Material": "TG11",
            "RequestedQuantity": "2",
            "RequestedQuantityUnit": "PC",
            "ProductionPlant": "1710",
        }
    ]


def test_create_sales_order_uses_csrf_token_and_cookie():
    requests = []

    def fake_sap(request):
        requests.append(request)
        if request.method == "GET":
            return httpx.Response(
                200,
                headers={
                    "X-CSRF-Token": "csrf-demo",
                    "Set-Cookie": "SAP_SESSIONID=abc; Path=/",
                },
            )

        assert request.headers["X-CSRF-Token"] == "csrf-demo"
        assert "SAP_SESSIONID=abc" in request.headers["Cookie"]
        assert json.loads(request.content)["SoldToParty"] == "17100003"
        return httpx.Response(201, json={"d": {"SalesOrder": "900001"}})

    created = create_sales_order(
        sap_config(),
        {"SoldToParty": "17100003"},
        transport=httpx.MockTransport(fake_sap),
    )

    assert created["SalesOrder"] == "900001"
    assert [request.method for request in requests] == ["GET", "POST"]
