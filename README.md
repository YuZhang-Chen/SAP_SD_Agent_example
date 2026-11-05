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
