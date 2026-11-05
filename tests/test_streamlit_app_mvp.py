from pathlib import Path

from streamlit.testing.v1 import AppTest

APP_PATH = Path(__file__).parents[1] / "app.py"


DRAFT = {
    "draft_id": "draft-123",
    "summary": {
        "sold_to_party": "17100001",
        "requested_delivery_date": "2026-11-20",
        "material": "TG11",
        "quantity": 2,
        "unit": "PC",
        "plant": "1710",
    },
}


async def fake_prepare_order(prompt):
    return {
        "text": "訂單草稿已準備完成。",
        "activities": [
            {
                "tool": "prepare_sales_order",
                "arguments": {"sold_to_party": "17100001"},
                "result": DRAFT,
            }
        ],
        "draft": DRAFT,
    }


async def fake_commit_order(draft_id):
    assert draft_id == "draft-123"
    return {"SalesOrder": "90000001"}


async def fake_commit_error(draft_id):
    raise RuntimeError("SAP 暫時無法建立訂單")


async def fake_agent_error(prompt):
    raise RuntimeError("Gemini 暫時無法使用")


def open_app(**state):
    app = AppTest.from_file(APP_PATH, default_timeout=10)
    for name, value in state.items():
        app.session_state[name] = value
    return app.run()


def prepare_draft(commit_function=fake_commit_order):
    app = open_app(
        ask_function=fake_prepare_order,
        commit_function=commit_function,
    )
    return app.chat_input[0].set_value("幫我準備一張訂單").run()


def find_button(app, label):
    return next(button for button in app.button if button.label == label)


def test_app_starts():
    app = open_app()

    assert not app.exception
    assert app.title[0].value == "SAP SD Agent"
    assert len(app.chat_input) == 1


def test_draft_can_be_cancelled_without_commit():
    app = prepare_draft()

    assert any(metric.label == "買方" for metric in app.metric)
    assert any(expander.label == "MCP 工具活動" for expander in app.expander)
    assert find_button(app, "確認建立")

    app = find_button(app, "取消").click().run()

    assert not any(button.label == "確認建立" for button in app.button)
    assert any("已取消" in item.value for item in app.markdown)


def test_confirm_button_creates_order():
    app = prepare_draft()
    app = find_button(app, "確認建立").click().run()

    assert any("90000001" in item.value for item in app.markdown)
    assert not any(button.label == "確認建立" for button in app.button)


def test_commit_error_is_shown():
    app = prepare_draft(fake_commit_error)
    app = find_button(app, "確認建立").click().run()

    assert any("SAP 暫時無法建立訂單" in item.value for item in app.error)
    assert any(button.label == "確認建立" for button in app.button)


def test_agent_error_is_shown_in_chat():
    app = open_app(ask_function=fake_agent_error)
    app = app.chat_input[0].set_value("查詢訂單").run()

    assert any("Gemini 暫時無法使用" in item.value for item in app.markdown)
