from __future__ import annotations

import pytest

from sap_sd_agent.config import SapSettings
from sap_sd_agent.odata.client import SapODataClient


@pytest.mark.integration
def test_live_sap_metadata_search_and_detail() -> None:
    settings = SapSettings()
    with SapODataClient(settings) as client:
        metadata = client.get_metadata()
        orders = client.search_sales_orders(limit=3)
        assert "EntityType" in metadata
        assert len(orders) <= 3
        if orders:
            detail = client.get_sales_order(orders[0].sales_order)
            assert detail.sales_order == orders[0].sales_order
