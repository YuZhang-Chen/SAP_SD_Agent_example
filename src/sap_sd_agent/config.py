from __future__ import annotations

from functools import lru_cache

from pydantic import BaseModel, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class SapSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    user: str = Field(validation_alias="SAP_USER")
    password: SecretStr = Field(validation_alias="SAP_PASSWORD")
    client: str = Field(default="600", validation_alias="SAP_CLIENT")
    language: str = Field(default="ZF", validation_alias="SAP_LANGUAGE")
    base_url: str = Field(validation_alias="SAP_ODATA_BASE_URL")
    verify_tls: bool = Field(default=True, validation_alias="SAP_ODATA_VERIFY_TLS")
    timeout_seconds: float = Field(
        default=20.0,
        gt=0,
        validation_alias="SAP_ODATA_TIMEOUT_SECONDS",
    )
    default_sales_order_type: str = Field(
        default="訂單",
        validation_alias="SAP_DEFAULT_SALES_ORDER_TYPE",
    )
    default_sales_organization: str = Field(
        default="1710",
        validation_alias="SAP_DEFAULT_SALES_ORGANIZATION",
    )
    default_distribution_channel: str = Field(
        default="10",
        validation_alias="SAP_DEFAULT_DISTRIBUTION_CHANNEL",
    )
    default_organization_division: str = Field(
        default="00",
        validation_alias="SAP_DEFAULT_ORGANIZATION_DIVISION",
    )
    default_currency: str = Field(
        default="USD",
        validation_alias="SAP_DEFAULT_CURRENCY",
    )
    default_quantity_unit: str = Field(
        default="PC",
        validation_alias="SAP_DEFAULT_QUANTITY_UNIT",
    )


class AgentSettings(BaseModel):
    sap: SapSettings


@lru_cache(maxsize=1)
def get_sap_settings() -> SapSettings:
    return SapSettings()


@lru_cache(maxsize=1)
def get_agent_settings() -> AgentSettings:
    return AgentSettings(sap=get_sap_settings())
