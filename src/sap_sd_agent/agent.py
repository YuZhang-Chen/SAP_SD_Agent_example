from google.genai import types
from mcp import Client

from sap_sd_agent.gemini_api import load_gemini_config, make_gemini_client
from sap_sd_agent.mcp_server import mcp


SAFE_TOOL_NAMES = {
    "search_sales_orders",
    "get_sales_order",
    "prepare_sales_order",
}

SYSTEM_PROMPT = """你是 SAP SD 銷售訂單助理。
請使用繁體中文回答，查詢資料時使用工具，不要捏造 SAP 資料。
建立訂單時只能準備草稿，必須等待使用者在程式中確認。
"""


def read_tool_result(result):
    """Turn an MCP result into a normal Python value."""
    if result.structured_content is not None:
        value = result.structured_content
        return value.get("result", value) if isinstance(value, dict) else value
    return [block.text for block in result.content if hasattr(block, "text")]


async def get_gemini_tools(mcp_client):
    """Convert the three safe MCP tools into Gemini declarations."""
    result = await mcp_client.list_tools()
    declarations = []

    for tool in result.tools:
        if tool.name in SAFE_TOOL_NAMES:
            declarations.append(
                types.FunctionDeclaration(
                    name=tool.name,
                    description=tool.description,
                    parameters_json_schema=tool.input_schema,
                )
            )

    return types.Tool(function_declarations=declarations)


async def ask_agent(prompt, gemini_config=None, gemini_client=None):
    """Ask Gemini and let it call safe MCP tools when needed."""
    gemini_config = gemini_config or load_gemini_config()
    created_here = gemini_client is None
    gemini_client = gemini_client or make_gemini_client(gemini_config)

    contents = [
        types.Content(
            role="user",
            parts=[types.Part.from_text(text=prompt)],
        )
    ]
    activities = []
    pending_draft = None

    async with Client(mcp) as mcp_client:
        gemini_tools = await get_gemini_tools(mcp_client)
        generate_config = types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            temperature=0,
            tools=[gemini_tools],
        )

        for _ in range(5):
            response = gemini_client.models.generate_content(
                model=gemini_config["model"],
                contents=contents,
                config=generate_config,
            )
            function_calls = response.function_calls or []

            if not function_calls:
                if created_here:
                    gemini_client.close()
                return {
                    "text": response.text or "Gemini 沒有回傳文字。",
                    "activities": activities,
                    "draft": pending_draft,
                }

            contents.append(response.candidates[0].content)
            function_responses = []

            for function_call in function_calls:
                if function_call.name not in SAFE_TOOL_NAMES:
                    raise ValueError(f"Unsafe tool requested: {function_call.name}")

                tool_result = await mcp_client.call_tool(
                    function_call.name,
                    dict(function_call.args or {}),
                )
                value = read_tool_result(tool_result)
                activities.append(
                    {
                        "tool": function_call.name,
                        "arguments": dict(function_call.args or {}),
                        "result": value,
                    }
                )
                if function_call.name == "prepare_sales_order":
                    pending_draft = value

                response_args = {
                    "name": function_call.name,
                    "response": {"result": value},
                }

                function_responses.append(
                    types.Part.from_function_response(**response_args)
                )

            contents.append(
                types.Content(role="user", parts=function_responses)
            )

    raise RuntimeError("Gemini used too many tool calls")


async def commit_draft(draft_id):
    """Called by the host only after the user confirms."""
    async with Client(mcp) as mcp_client:
        result = await mcp_client.call_tool(
            "commit_sales_order",
            {"draft_id": draft_id},
        )
        return read_tool_result(result)
