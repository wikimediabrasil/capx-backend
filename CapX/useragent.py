"""Global User-Agent utility for outbound HTTP requests.

Provides a consistent User-Agent string across management commands and
service modules. Format: "CapacityExchange/<version>" optionally with
an extra component suffix: "CapacityExchange/<version> (<extra>)".
"""
from django.conf import settings

def get_user_agent(extra: str | None = None) -> str:
    version = getattr(settings, "SPECTACULAR_SETTINGS", {}).get("VERSION", "dev")
    base = f"CapacityExchange/{version}"
    if extra:
        return f"{base} ({extra})"
    return base
