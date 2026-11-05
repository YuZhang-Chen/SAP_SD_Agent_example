import os

from dotenv import load_dotenv


def load_sap_config():
    """Read SAP settings from .env and return a simple dictionary."""
    load_dotenv()

    config = {
        "user": os.getenv("SAP_USER", ""),
        "password": os.getenv("SAP_PASSWORD", ""),
        "client": os.getenv("SAP_CLIENT", "600"),
        "language": os.getenv("SAP_LANGUAGE", "ZF"),
        "base_url": os.getenv("SAP_ODATA_BASE_URL", "").rstrip("/"),
        "verify_tls": os.getenv("SAP_ODATA_VERIFY_TLS", "true").lower()
        == "true",
        "timeout": float(os.getenv("SAP_ODATA_TIMEOUT_SECONDS", "20")),
        "sales_order_type": os.getenv("SAP_DEFAULT_SALES_ORDER_TYPE", "訂單"),
        "sales_organization": os.getenv(
            "SAP_DEFAULT_SALES_ORGANIZATION", "1710"
        ),
        "distribution_channel": os.getenv(
            "SAP_DEFAULT_DISTRIBUTION_CHANNEL", "10"
        ),
        "organization_division": os.getenv(
            "SAP_DEFAULT_ORGANIZATION_DIVISION", "00"
        ),
        "currency": os.getenv("SAP_DEFAULT_CURRENCY", "USD"),
        "quantity_unit": os.getenv("SAP_DEFAULT_QUANTITY_UNIT", "PC"),
    }

    required = ["user", "password", "base_url"]
    missing = [name for name in required if not config[name]]
    if missing:
        raise ValueError(f"Missing settings in .env: {', '.join(missing)}")

    return config
