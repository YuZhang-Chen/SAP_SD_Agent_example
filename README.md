# SAP SD OData MCP Agent

以 SAP `API_SALES_ORDER_SRV` OData V2 API 為基礎的 SAP SD 課堂展示專案。

## 環境需求

- Python 3.12
- `uv`
- 可連線的 SAP S/4HANA OData V2 服務

## 建立環境

```powershell
uv venv --python 3.12 .venv
uv pip install --python .venv\Scripts\python.exe -r requirements-dev.txt
uv pip install --python .venv\Scripts\python.exe -e . --no-deps
Copy-Item .env.example .env
```

請在 `.env` 填入 SAP 帳密。教學系統使用自簽憑證時可暫時設定
`SAP_ODATA_VERIFY_TLS=false`；正式環境應使用有效憑證並設為 `true`。

## Phase 1 測試

```powershell
.venv\Scripts\python.exe -m pytest
.venv\Scripts\python.exe -m pytest --run-integration -m integration
```

整合測試只讀取 metadata、訂單清單與訂單明細，不會建立銷售訂單。
