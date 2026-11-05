from __future__ import annotations

import xml.etree.ElementTree as ET
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

import httpx

from sap_sd_agent.config import SapSettings
from sap_sd_agent.odata.errors import (
    SapAuthenticationError,
    SapConnectionError,
    SapNotFoundError,
    SapODataError,
)
from sap_sd_agent.odata.models import (
    CreateSalesOrderInput,
    SalesOrderDetail,
    SalesOrderItem,
    SalesOrderSummary,
    parse_odata_datetime,
)

SUMMARY_FIELDS = (
    "SalesOrder",
    "SalesOrderType",
    "SalesOrderDate",
    "SoldToParty",
    "TotalNetAmount",
    "TransactionCurrency",
    "OverallSDProcessStatus",
    "OverallDeliveryStatus",
)

DETAIL_FIELDS = SUMMARY_FIELDS + (
    "SalesOrganization",
    "DistributionChannel",
    "OrganizationDivision",
    "RequestedDeliveryDate",
    "PurchaseOrderByCustomer",
)


def _escape_odata_string(value: str) -> str:
    return value.replace("'", "''")


def _decimal_or_none(value: Any) -> Decimal | None:
    if value in (None, ""):
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise SapODataError(f"SAP returned an invalid decimal value: {value!r}") from exc


def _results(payload: dict[str, Any]) -> list[dict[str, Any]]:
    data = payload.get("d", payload)
    if isinstance(data, dict) and isinstance(data.get("results"), list):
        return data["results"]
    return []


def _entity(payload: dict[str, Any]) -> dict[str, Any]:
    data = payload.get("d", payload)
    return data if isinstance(data, dict) else {}


class SapODataClient:
    def __init__(
        self,
        settings: SapSettings,
        *,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.settings = settings
        self._client = httpx.Client(
            base_url=settings.base_url.rstrip("/") + "/",
            auth=httpx.BasicAuth(
                settings.user,
                settings.password.get_secret_value(),
            ),
            headers={
                "Accept": "application/json",
                "sap-client": settings.client,
                "Accept-Language": settings.language,
            },
            timeout=settings.timeout_seconds,
            verify=settings.verify_tls,
            transport=transport,
        )

    def __enter__(self) -> SapODataClient:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def close(self) -> None:
        self._client.close()

    def get_metadata(self) -> str:
        response = self._request("GET", "$metadata", headers={"Accept": "application/xml"})
        return response.text

    def search_sales_orders(
        self,
        *,
        sales_order: str | None = None,
        sold_to_party: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        limit: int = 10,
    ) -> list[SalesOrderSummary]:
        if not 1 <= limit <= 20:
            raise ValueError("limit must be between 1 and 20")

        filters: list[str] = []
        if sales_order:
            filters.append(f"SalesOrder eq '{_escape_odata_string(sales_order)}'")
        if sold_to_party:
            filters.append(f"SoldToParty eq '{_escape_odata_string(sold_to_party)}'")
        if date_from:
            filters.append(
                f"SalesOrderDate ge datetime'{date_from.isoformat()}T00:00:00'"
            )
        if date_to:
            filters.append(
                f"SalesOrderDate le datetime'{date_to.isoformat()}T23:59:59'"
            )

        params: dict[str, str] = {
            "$format": "json",
            "$select": ",".join(SUMMARY_FIELDS),
            "$top": str(limit),
        }
        if filters:
            params["$filter"] = " and ".join(filters)

        response = self._request("GET", "A_SalesOrder", params=params)
        return [self._parse_summary(row) for row in _results(response.json())]

    def get_sales_order(self, sales_order: str) -> SalesOrderDetail:
        key = _escape_odata_string(sales_order.strip())
        if not key:
            raise ValueError("sales_order is required")
        response = self._request(
            "GET",
            f"A_SalesOrder('{key}')",
            params={
                "$format": "json",
                "$select": ",".join(DETAIL_FIELDS),
                "$expand": "to_Item",
            },
        )
        return self._parse_detail(_entity(response.json()))

    def create_sales_order(self, order: CreateSalesOrderInput) -> SalesOrderDetail:
        token_response = self._request(
            "GET",
            "",
            headers={"X-CSRF-Token": "Fetch"},
        )
        csrf_token = token_response.headers.get("X-CSRF-Token")
        if not csrf_token:
            raise SapODataError("SAP did not return an X-CSRF-Token")

        response = self._request(
            "POST",
            "A_SalesOrder",
            headers={"X-CSRF-Token": csrf_token},
            json=order.to_odata_payload(),
        )
        return self._parse_detail(_entity(response.json()))

    def _request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        try:
            response = self._client.request(method, path, **kwargs)
        except httpx.TimeoutException as exc:
            raise SapConnectionError("SAP OData request timed out") from exc
        except httpx.HTTPError as exc:
            raise SapConnectionError(f"Unable to reach SAP OData: {exc}") from exc

        if response.is_success:
            return response
        self._raise_response_error(response)
        raise AssertionError("unreachable")

    def _raise_response_error(self, response: httpx.Response) -> None:
        message = response.reason_phrase or "SAP OData request failed"
        code: str | None = None
        try:
            payload = response.json()
            error = payload.get("error", {})
            code = error.get("code")
            error_message = error.get("message", {})
            if isinstance(error_message, dict):
                message = error_message.get("value") or message
            elif isinstance(error_message, str):
                message = error_message
        except (ValueError, TypeError, AttributeError):
            try:
                root = ET.fromstring(response.text)
                message_node = next(
                    (node for node in root.iter() if node.tag.endswith("message")),
                    None,
                )
                if message_node is not None and message_node.text:
                    message = message_node.text
            except ET.ParseError:
                pass

        exception_type: type[SapODataError]
        if response.status_code in (401, 403):
            exception_type = SapAuthenticationError
        elif response.status_code == 404:
            exception_type = SapNotFoundError
        else:
            exception_type = SapODataError
        raise exception_type(message, status_code=response.status_code, code=code)

    @staticmethod
    def _parse_summary(row: dict[str, Any]) -> SalesOrderSummary:
        return SalesOrderSummary(
            sales_order=str(row.get("SalesOrder", "")),
            sales_order_type=row.get("SalesOrderType"),
            sales_order_date=parse_odata_datetime(row.get("SalesOrderDate")),
            sold_to_party=row.get("SoldToParty"),
            total_net_amount=_decimal_or_none(row.get("TotalNetAmount")),
            transaction_currency=row.get("TransactionCurrency"),
            overall_sd_process_status=row.get("OverallSDProcessStatus"),
            overall_delivery_status=row.get("OverallDeliveryStatus"),
        )

    @classmethod
    def _parse_detail(cls, row: dict[str, Any]) -> SalesOrderDetail:
        summary = cls._parse_summary(row)
        item_rows = row.get("to_Item", {}).get("results", [])
        items = [
            SalesOrderItem(
                sales_order_item=item.get("SalesOrderItem"),
                material=item.get("Material"),
                sales_order_item_text=item.get("SalesOrderItemText"),
                requested_quantity=_decimal_or_none(item.get("RequestedQuantity")),
                requested_quantity_unit=item.get("RequestedQuantityUnit"),
                production_plant=item.get("ProductionPlant"),
            )
            for item in item_rows
        ]
        return SalesOrderDetail(
            **summary.model_dump(),
            sales_organization=row.get("SalesOrganization"),
            distribution_channel=row.get("DistributionChannel"),
            organization_division=row.get("OrganizationDivision"),
            requested_delivery_date=parse_odata_datetime(
                row.get("RequestedDeliveryDate")
            ),
            purchase_order_by_customer=row.get("PurchaseOrderByCustomer"),
            items=items,
        )
