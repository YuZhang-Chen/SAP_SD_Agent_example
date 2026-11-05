import asyncio
import os

import streamlit as st
from dotenv import load_dotenv

from sap_sd_agent.agent import ask_agent, commit_draft


st.set_page_config(
    page_title="SAP SD Agent",
    layout="wide",
)

st.markdown(
    """
    <style>
    .stApp { background: #f7f8fa; color: #171717; }
    .block-container { max-width: 1100px; padding-top: 2rem; }
    h1, h2, h3 { letter-spacing: -0.02em; }
    [data-testid="stSidebar"] { background: #171717; }
    [data-testid="stSidebar"] * { color: #ffffff; }
    [data-testid="stChatMessage"] {
        background: #ffffff;
        border: 1px solid #e5e7eb;
        border-radius: 12px;
        margin-bottom: 0.75rem;
    }
    div.stButton > button[kind="primary"] {
        background: #0a6ed1;
        border-color: #0a6ed1;
        min-height: 44px;
    }
    div.stButton > button { min-height: 44px; }
    </style>
    """,
    unsafe_allow_html=True,
)


def run_async(job):
    """Run one async agent action from Streamlit."""
    return asyncio.run(job)


def initialize_state():
    """Create the small amount of state used by this demo."""
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "pending_draft" not in st.session_state:
        st.session_state.pending_draft = None


def show_tool_activities(activities):
    """Show which MCP tools the agent used."""
    if not activities:
        return

    with st.expander("MCP 工具活動"):
        for activity in activities:
            st.markdown(f"**{activity['tool']}**")
            st.caption("輸入")
            st.json(activity["arguments"])
            st.caption("結果")
            st.json(activity["result"])


def show_order_draft(draft):
    """Show the draft and require a real button click before writing."""
    summary = draft["summary"]
    sales_area = "/".join(
        [
            os.getenv("SAP_DEFAULT_SALES_ORGANIZATION", "1710"),
            os.getenv("SAP_DEFAULT_DISTRIBUTION_CHANNEL", "10"),
            os.getenv("SAP_DEFAULT_ORGANIZATION_DIVISION", "00"),
        ]
    )

    with st.container(border=True):
        st.subheader("待確認銷售訂單")
        st.warning("這一步尚未寫入 SAP。請核對資料後再確認建立。")

        first, second, third = st.columns(3)
        first.metric("買方", summary["sold_to_party"])
        second.metric("銷售範圍", sales_area)
        third.metric("要求交貨日", summary["requested_delivery_date"])

        st.dataframe(
            [
                {
                    "物料": summary["material"],
                    "數量": summary["quantity"],
                    "單位": summary["unit"],
                    "工廠": summary["plant"],
                }
            ],
            hide_index=True,
            use_container_width=True,
        )

        confirm_column, cancel_column = st.columns(2)
        confirm_clicked = confirm_column.button(
            "確認建立",
            type="primary",
            use_container_width=True,
            key="confirm_order",
        )
        cancel_clicked = cancel_column.button(
            "取消",
            use_container_width=True,
            key="cancel_order",
        )

    if cancel_clicked:
        st.session_state.pending_draft = None
        st.session_state.messages.append(
            {"role": "assistant", "content": "已取消，本次不會寫入 SAP。"}
        )
        st.rerun()

    if confirm_clicked:
        commit_function = st.session_state.get("commit_function", commit_draft)
        try:
            with st.spinner("正在建立 SAP 銷售訂單..."):
                result = run_async(commit_function(draft["draft_id"]))
            order_number = result.get("SalesOrder", "已建立")
            st.session_state.pending_draft = None
            st.session_state.messages.append(
                {
                    "role": "assistant",
                    "content": f"銷售訂單建立成功：{order_number}",
                }
            )
            st.rerun()
        except Exception as error:
            st.error(f"建立失敗：{error}")


load_dotenv()
initialize_state()

with st.sidebar:
    st.header("系統狀態")
    sap_ready = all(
        os.getenv(name)
        for name in ["SAP_USER", "SAP_PASSWORD", "SAP_ODATA_BASE_URL"]
    )
    gemini_ready = bool(os.getenv("GEMINI_API_KEY"))

    if sap_ready:
        st.success("SAP 設定完成")
    else:
        st.warning("SAP 尚未設定")

    if gemini_ready:
        st.success("Gemini 設定完成")
    else:
        st.warning("Gemini 尚未設定")

    st.divider()
    st.caption("安全模式")
    st.write("Gemini 只能查詢與準備草稿，不能直接建立訂單。")

    if st.button("清除對話", use_container_width=True):
        st.session_state.messages = []
        st.session_state.pending_draft = None
        st.rerun()

st.title("SAP SD Agent")
st.caption("用自然語言查詢銷售訂單，或準備一張新的訂單草稿。")

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        show_tool_activities(message.get("activities", []))

if st.session_state.pending_draft:
    show_order_draft(st.session_state.pending_draft)

prompt = st.chat_input("例如：查詢最近 3 張銷售訂單")
if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    ask_function = st.session_state.get("ask_function", ask_agent)

    try:
        with st.spinner("Gemini 正在使用 MCP 工具..."):
            answer = run_async(ask_function(prompt))
        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": answer["text"],
                "activities": answer.get("activities", []),
            }
        )
        st.session_state.pending_draft = answer.get("draft")
    except Exception as error:
        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": f"處理失敗：{error}",
            }
        )

    st.rerun()
