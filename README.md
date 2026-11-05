# SAP SD OData MVP

這是一個刻意保持簡單的學生範例。Phase 1 只有兩個主要檔案：

- `settings.py`：讀取 `.env`
- `odata_api.py`：查詢與建立 SAP 銷售訂單

## 建立環境

```powershell
uv venv --python 3.12 .venv
uv pip install --python .venv\Scripts\python.exe -r requirements-dev.txt
uv pip install --python .venv\Scripts\python.exe -e . --no-deps
```

## 最小查單範例

```python
from sap_sd_agent.settings import load_sap_config
from sap_sd_agent.odata_api import search_sales_orders

config = load_sap_config()
orders = search_sales_orders(config, limit=3)
print(orders)
```

## 測試

```powershell
.venv\Scripts\python.exe -m pytest -m "not integration"
.venv\Scripts\python.exe -m pytest --run-integration -m integration
```

整合測試只讀取 SAP，不會建立訂單。教學系統若使用自簽憑證，可在 `.env` 設定 `SAP_ODATA_VERIFY_TLS=false`；正式環境應使用有效憑證。
