import time
from uuid import uuid4
from typing import Any

from mcp.server import MCPServer

from sap_sd_agent.odata_api import (
    build_order_payload,
    create_sales_order as sap_create_sales_order,
    get_sales_order as sap_get_sales_order,
    search_sales_orders as sap_search_sales_orders,
)
from sap_sd_agent.settings import load_sap_config


mcp = MCPServer(
    "sap-sd-agent",
    instructions="Use these tools to read SAP SD sales orders and prepare a draft.",
)

DRAFTS = {}
DRAFT_LIFETIME_SECONDS = 15 * 60


@mcp.tool(name="search_sales_orders", structured_output=True)
def search_sales_orders_tool(
    sales_order: str = "",
    sold_to_party: str = "",
    date_from: str = "",
    date_to: str = "",
    limit: int = 5,
) -> list[dict[str, Any]]:
    """Search SAP sales orders. Dates use YYYY-MM-DD."""
    config = load_sap_config()
    return sap_search_sales_orders(
        config,
        sales_order=sales_order or None,
        sold_to_party=sold_to_party or None,
        date_from=date_from or None,
        date_to=date_to or None,
        limit=limit,
    )


@mcp.tool(name="get_sales_order", structured_output=True)
def get_sales_order_tool(sales_order: str) -> dict[str, Any]:
    """Get one SAP sales order, including its items."""
    return sap_get_sales_order(load_sap_config(), sales_order)


@mcp.tool(name="prepare_sales_order", structured_output=True)
def prepare_sales_order_tool(
    sold_to_party: str,
    requested_delivery_date: str,
    material: str,
    quantity: float,
    unit: str = "PC",
    plant: str = "1710",
    customer_reference: str = "",
) -> dict[str, Any]:
    """Prepare one sales order draft. This does not write to SAP."""
    config = load_sap_config()
    payload = build_order_payload(
        config,
        sold_to_party=sold_to_party,
        requested_delivery_date=requested_delivery_date,
        items=[
            {
                "material": material,
                "quantity": quantity,
                "unit": unit,
                "plant": plant,
            }
        ],
        customer_reference=customer_reference or None,
    )

    draft_id = str(uuid4())
    expires_at = time.time() + DRAFT_LIFETIME_SECONDS
    DRAFTS[draft_id] = {"payload": payload, "expires_at": expires_at}

    return {
        "draft_id": draft_id,
        "expires_at": expires_at,
        "summary": {
            "sold_to_party": sold_to_party,
            "requested_delivery_date": requested_delivery_date,
            "material": material,
            "quantity": quantity,
            "unit": unit,
            "plant": plant,
        },
    }


@mcp.tool(name="commit_sales_order", structured_output=True)
def commit_sales_order_tool(draft_id: str) -> dict[str, Any]:
    """Create a prepared order. The host must ask the user first."""
    draft = DRAFTS.get(draft_id)
    if not draft:
        raise ValueError("Draft not found")
    if time.time() > draft["expires_at"]:
        DRAFTS.pop(draft_id)
        raise ValueError("Draft expired")

    result = sap_create_sales_order(load_sap_config(), draft["payload"])
    DRAFTS.pop(draft_id)
    return result


if __name__ == "__main__":
    mcp.run()
