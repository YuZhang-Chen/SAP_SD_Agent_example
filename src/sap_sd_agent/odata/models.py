from __future__ import annotations

import re
from datetime import date, datetime, time, timezone
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

ODATA_DATE_PATTERN = re.compile(r"^/Date\((-?\d+)(?:[+-]\d{4})?\)/$")


def parse_odata_datetime(value: Any) -> datetime | None:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime.combine(value, time.min, tzinfo=timezone.utc)
    if isinstance(value, str):
        match = ODATA_DATE_PATTERN.match(value)
        if match:
            return datetime.fromtimestamp(int(match.group(1)) / 1000, tz=timezone.utc)
        normalized = value.replace("Z", "+00:00")
        parsed = datetime.fromisoformat(normalized)
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    raise TypeError(f"Unsupported OData date value: {value!r}")


def format_odata_date(value: date) -> str:
    as_datetime = datetime.combine(value, time.min, tzinfo=timezone.utc)
    milliseconds = int(as_datetime.timestamp() * 1000)
    return f"/Date({milliseconds})/"


class SalesOrderItemInput(BaseModel):
    material: str = Field(min_length=1)
    requested_quantity: Decimal = Field(gt=0)
    requested_quantity_unit: str = Field(default="PC", min_length=1)
    production_plant: str | None = None

    @field_validator("material", "requested_quantity_unit", "production_plant")
    @classmethod
    def strip_text(cls, value: str | None) -> str | None:
        return value.strip() if isinstance(value, str) else value


class CreateSalesOrderInput(BaseModel):
    sales_order_type: str
    sales_organization: str
    distribution_channel: str
    organization_division: str
    sold_to_party: str
    requested_delivery_date: date
    items: list[SalesOrderItemInput] = Field(min_length=1)
    transaction_currency: str = "USD"
    purchase_order_by_customer: str | None = None

    @field_validator(
        "sales_order_type",
        "sales_organization",
        "distribution_channel",
        "organization_division",
        "sold_to_party",
        "transaction_currency",
        "purchase_order_by_customer",
    )
    @classmethod
    def strip_header_text(cls, value: str | None) -> str | None:
        return value.strip() if isinstance(value, str) else value

    def to_odata_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "SalesOrderType": self.sales_order_type,
            "SalesOrganization": self.sales_organization,
            "DistributionChannel": self.distribution_channel,
            "OrganizationDivision": self.organization_division,
            "SoldToParty": self.sold_to_party,
            "RequestedDeliveryDate": format_odata_date(self.requested_delivery_date),
            "TransactionCurrency": self.transaction_currency,
            "to_Item": {
                "results": [
                    {
                        "Material": item.material,
                        "RequestedQuantity": str(item.requested_quantity),
                        "RequestedQuantityUnit": item.requested_quantity_unit,
                        **(
                            {"ProductionPlant": item.production_plant}
                            if item.production_plant
                            else {}
                        ),
                    }
                    for item in self.items
                ]
            },
        }
        if self.purchase_order_by_customer:
            payload["PurchaseOrderByCustomer"] = self.purchase_order_by_customer
        return payload


class SalesOrderSummary(BaseModel):
    model_config = ConfigDict(extra="ignore")

    sales_order: str
    sales_order_type: str | None = None
    sales_order_date: datetime | None = None
    sold_to_party: str | None = None
    total_net_amount: Decimal | None = None
    transaction_currency: str | None = None
    overall_sd_process_status: str | None = None
    overall_delivery_status: str | None = None


class SalesOrderItem(BaseModel):
    model_config = ConfigDict(extra="ignore")

    sales_order_item: str | None = None
    material: str | None = None
    sales_order_item_text: str | None = None
    requested_quantity: Decimal | None = None
    requested_quantity_unit: str | None = None
    production_plant: str | None = None


class SalesOrderDetail(SalesOrderSummary):
    sales_organization: str | None = None
    distribution_channel: str | None = None
    organization_division: str | None = None
    requested_delivery_date: datetime | None = None
    purchase_order_by_customer: str | None = None
    items: list[SalesOrderItem] = Field(default_factory=list)


class SalesOrderDraft(BaseModel):
    draft_id: str
    created_at: datetime
    expires_at: datetime
    order: CreateSalesOrderInput
