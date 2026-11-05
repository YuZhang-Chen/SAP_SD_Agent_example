from datetime import date, datetime, time, timezone

import httpx


ORDER_FIELDS = [
    "SalesOrder",
    "SalesOrderType",
    "SalesOrderDate",
    "SoldToParty",
    "TotalNetAmount",
    "TransactionCurrency",
    "OverallSDProcessStatus",
    "OverallDeliveryStatus",
]


def make_client(config, transport=None):
    """Create one HTTP client with the headers required by SAP."""
    return httpx.Client(
        base_url=config["base_url"] + "/",
        auth=(config["user"], config["password"]),
        headers={
            "Accept": "application/json",
            "sap-client": config["client"],
            "Accept-Language": config["language"],
        },
        verify=config["verify_tls"],
        timeout=config["timeout"],
        transport=transport,
    )


def get_metadata(config, transport=None):
    with make_client(config, transport) as client:
        response = client.get("$metadata", headers={"Accept": "application/xml"})
        response.raise_for_status()
        return response.text


def search_sales_orders(
    config,
    sales_order=None,
    sold_to_party=None,
    date_from=None,
    date_to=None,
    limit=10,
    transport=None,
):
    """Search sales orders and return SAP's result as a list of dictionaries."""
    limit = max(1, min(int(limit), 20))
    filters = []

    if sales_order:
        value = sales_order.replace("'", "''")
        filters.append(f"SalesOrder eq '{value}'")
    if sold_to_party:
        value = sold_to_party.replace("'", "''")
        filters.append(f"SoldToParty eq '{value}'")
    if date_from:
        filters.append(f"SalesOrderDate ge datetime'{date_from}T00:00:00'")
    if date_to:
        filters.append(f"SalesOrderDate le datetime'{date_to}T23:59:59'")

    params = {
        "$format": "json",
        "$select": ",".join(ORDER_FIELDS),
        "$top": str(limit),
    }
    if filters:
        params["$filter"] = " and ".join(filters)

    with make_client(config, transport) as client:
        response = client.get("A_SalesOrder", params=params)
        response.raise_for_status()
        return response.json()["d"]["results"]


def get_sales_order(config, sales_order, transport=None):
    """Get one sales order and expand its item list."""
    order_id = str(sales_order).replace("'", "''")
    params = {"$format": "json", "$expand": "to_Item"}

    with make_client(config, transport) as client:
        response = client.get(f"A_SalesOrder('{order_id}')", params=params)
        response.raise_for_status()
        return response.json()["d"]


def odata_date(value):
    """Convert YYYY-MM-DD or date into SAP OData V2 date format."""
    if isinstance(value, str):
        value = date.fromisoformat(value)
    value_as_datetime = datetime.combine(value, time.min, tzinfo=timezone.utc)
    milliseconds = int(value_as_datetime.timestamp() * 1000)
    return f"/Date({milliseconds})/"


def build_order_payload(
    config,
    sold_to_party,
    requested_delivery_date,
    items,
    customer_reference=None,
):
    """Build the small deep-insert payload used by the demo."""
    if not items:
        raise ValueError("At least one sales order item is required")

    sap_items = []
    for item in items:
        sap_item = {
            "Material": item["material"],
            "RequestedQuantity": str(item["quantity"]),
            "RequestedQuantityUnit": item.get(
                "unit", config["quantity_unit"]
            ),
        }
        if item.get("plant"):
            sap_item["ProductionPlant"] = item["plant"]
        sap_items.append(sap_item)

    payload = {
        "SalesOrderType": config["sales_order_type"],
        "SalesOrganization": config["sales_organization"],
        "DistributionChannel": config["distribution_channel"],
        "OrganizationDivision": config["organization_division"],
        "SoldToParty": sold_to_party,
        "RequestedDeliveryDate": odata_date(requested_delivery_date),
        "TransactionCurrency": config["currency"],
        "to_Item": {"results": sap_items},
    }
    if customer_reference:
        payload["PurchaseOrderByCustomer"] = customer_reference

    return payload


def create_sales_order(config, payload, transport=None):
    """Fetch a CSRF token and create one sales order."""
    with make_client(config, transport) as client:
        token_response = client.get("", headers={"X-CSRF-Token": "Fetch"})
        token_response.raise_for_status()
        csrf_token = token_response.headers["X-CSRF-Token"]

        response = client.post(
            "A_SalesOrder",
            json=payload,
            headers={"X-CSRF-Token": csrf_token},
        )
        response.raise_for_status()
        return response.json()["d"]
