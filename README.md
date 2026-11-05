# SAP SD OData MVP

這是一個刻意保持簡單的學生範例。

- `settings.py`：讀取 SAP `.env`
- `odata_api.py`：查詢與建立 SAP 銷售訂單
- `gemini_api.py`：呼叫 Gemini API

## 建立環境

```powershell
uv venv --python 3.12 .venv
uv pip install --python .venv\Scripts\python.exe -r requirements-dev.txt
uv pip install --python .venv\Scripts\python.exe -e . --no-deps
```

## SAP 查單範例

```python
from sap_sd_agent.settings import load_sap_config
from sap_sd_agent.odata_api import search_sales_orders

config = load_sap_config()
orders = search_sales_orders(config, limit=3)
print(orders)
```

## Gemini 連線測試

```powershell
.venv\Scripts\python.exe -m sap_sd_agent.gemini_api
```

## 執行測試

```powershell
.venv\Scripts\python.exe -m pytest -m "not integration"
.venv\Scripts\python.exe -m pytest --run-integration -m integration
```

SAP 整合測試只讀取資料，不會建立訂單。教學系統若使用自簽憑證，可設定 `SAP_ODATA_VERIFY_TLS=false`；正式環境應使用有效憑證。

## Phase 3：MCP Agent

啟動 MCP stdio server：

```powershell
.venv\Scripts\python.exe -m sap_sd_agent.mcp_server
```

啟動命令列聊天：

```powershell
.venv\Scripts\python.exe -m sap_sd_agent.cli
```

Gemini 只能使用查單、明細與準備草稿三個工具。`commit_sales_order` 不會交給模型，只有使用者在 CLI 輸入 `yes` 後才會呼叫。

## Phase 4：Streamlit Demo

啟動繁體中文網頁：

```powershell
.venv\Scripts\streamlit.exe run app.py
```

畫面可查詢訂單、查看 MCP 工具活動，以及準備建單草稿。只有按下「確認建立」後才會呼叫 `commit_sales_order`；按下「取消」不會寫入 SAP。

Streamlit 畫面測試：

```powershell
.venv\Scripts\python.exe -m pytest tests\test_streamlit_app_mvp.py
```
