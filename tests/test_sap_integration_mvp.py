import pytest

from sap_sd_agent.odata_api import (
    get_metadata,
    get_sales_order,
    search_sales_orders,
)
from sap_sd_agent.settings import load_sap_config


@pytest.mark.integration
def test_live_sap_read_only():
    config = load_sap_config()

    metadata = get_metadata(config)
    orders = search_sales_orders(config, limit=3)

    assert "EntityType" in metadata
    assert len(orders) <= 3

    if orders:
        order_id = orders[0]["SalesOrder"]
        order = get_sales_order(config, order_id)
        assert order["SalesOrder"] == order_id
