import pytest
from mcp import Client

from sap_sd_agent.agent import read_tool_result
from sap_sd_agent.mcp_server import mcp


@pytest.mark.integration
@pytest.mark.asyncio
async def test_live_mcp_search_sales_orders():
    async with Client(mcp) as client:
        result = await client.call_tool("search_sales_orders", {"limit": 1})

    orders = read_tool_result(result)
    assert len(orders) <= 1
