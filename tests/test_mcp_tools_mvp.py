from types import SimpleNamespace

import pytest
from google.genai import types
from mcp import Client

import sap_sd_agent.mcp_server as server
from sap_sd_agent.agent import ask_agent, get_gemini_tools, read_tool_result


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


@pytest.mark.asyncio
async def test_mcp_lists_four_tools_and_calls_search(monkeypatch):
    monkeypatch.setattr(server, "load_sap_config", sap_config)
    monkeypatch.setattr(
        server,
        "sap_search_sales_orders",
        lambda config, **kwargs: [{"SalesOrder": "2"}],
    )

    async with Client(server.mcp) as client:
        tools = await client.list_tools()
        result = await client.call_tool("search_sales_orders", {"limit": 1})

    assert {tool.name for tool in tools.tools} == {
        "search_sales_orders",
        "get_sales_order",
        "prepare_sales_order",
        "commit_sales_order",
    }
    assert read_tool_result(result) == [{"SalesOrder": "2"}]


@pytest.mark.asyncio
async def test_gemini_does_not_receive_commit_tool():
    async with Client(server.mcp) as client:
        gemini_tools = await get_gemini_tools(client)

    names = {tool.name for tool in gemini_tools.function_declarations}
    assert names == {
        "search_sales_orders",
        "get_sales_order",
        "prepare_sales_order",
    }


def test_prepare_then_commit_draft(monkeypatch):
    server.DRAFTS.clear()
    monkeypatch.setattr(server, "load_sap_config", sap_config)
    monkeypatch.setattr(
        server,
        "sap_create_sales_order",
        lambda config, payload: {"SalesOrder": "900001"},
    )

    draft = server.prepare_sales_order_tool(
        sold_to_party="17100003",
        requested_delivery_date="2026-11-12",
        material="TG11",
        quantity=2,
    )
    result = server.commit_sales_order_tool(draft["draft_id"])

    assert result["SalesOrder"] == "900001"
    assert draft["draft_id"] not in server.DRAFTS


class FakeModels:
    def __init__(self):
        function_call = types.FunctionCall(
            id="call-1",
            name="search_sales_orders",
            args={"limit": 1},
        )
        model_content = types.Content(
            role="model",
            parts=[
                types.Part.from_function_call(
                    name="search_sales_orders",
                    args={"limit": 1},
                )
            ],
        )
        self.responses = [
            SimpleNamespace(
                function_calls=[function_call],
                candidates=[SimpleNamespace(content=model_content)],
                text=None,
            ),
            SimpleNamespace(function_calls=[], candidates=[], text="找到訂單 2"),
        ]

    def generate_content(self, **kwargs):
        return self.responses.pop(0)


class FakeGeminiClient:
    def __init__(self):
        self.models = FakeModels()


@pytest.mark.asyncio
async def test_agent_routes_gemini_call_through_mcp(monkeypatch):
    monkeypatch.setattr(server, "load_sap_config", sap_config)
    monkeypatch.setattr(
        server,
        "sap_search_sales_orders",
        lambda config, **kwargs: [{"SalesOrder": "2"}],
    )

    reply = await ask_agent(
        "查一筆訂單",
        gemini_config={"model": "gemini-test"},
        gemini_client=FakeGeminiClient(),
    )

    assert reply["text"] == "找到訂單 2"
    assert reply["activities"][0]["tool"] == "search_sales_orders"
    assert reply["activities"][0]["result"] == [{"SalesOrder": "2"}]



def test_expired_draft_cannot_be_committed():
    server.DRAFTS.clear()
    server.DRAFTS["expired"] = {"payload": {}, "expires_at": 0}

    with pytest.raises(ValueError, match="Draft expired"):
        server.commit_sales_order_tool("expired")
