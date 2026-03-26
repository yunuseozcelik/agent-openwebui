from __future__ import annotations

import json
import os
from typing import Any


def _is_true(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "on"}


PORTKEY_ENABLED = _is_true(os.getenv("PORTKEY_ENABLED"))
PORTKEY_BASE_URL = os.getenv("PORTKEY_BASE_URL", "https://api.portkey.ai/v1")
PORTKEY_API_KEY = os.getenv("PORTKEY_API_KEY", "")
PORTKEY_PROVIDER = os.getenv("PORTKEY_PROVIDER", "openai")
PORTKEY_VIRTUAL_KEY = os.getenv("PORTKEY_VIRTUAL_KEY", "")
PORTKEY_CONFIG = os.getenv("PORTKEY_CONFIG", "")
PORTKEY_MODEL_PREFIX = os.getenv("PORTKEY_MODEL_PREFIX", "")
PORTKEY_CLIENT_API_KEY = os.getenv("PORTKEY_CLIENT_API_KEY", "portkey-gateway")
PORTKEY_DASHBOARD_URL = os.getenv("PORTKEY_DASHBOARD_URL", "https://app.portkey.ai")


def is_gateway_enabled() -> bool:
    return PORTKEY_ENABLED and bool(PORTKEY_API_KEY)


def resolve_model_name(model_id: str) -> str:
    model_id = (model_id or "").strip()
    if not model_id:
        return model_id
    if not is_gateway_enabled():
        return model_id
    if not PORTKEY_MODEL_PREFIX or model_id.startswith("@"):
        return model_id
    prefix = PORTKEY_MODEL_PREFIX.rstrip("/")
    return f"{prefix}/{model_id}"


def build_gateway_headers(*, engine: str, component: str) -> dict[str, str]:
    if not is_gateway_enabled():
        return {}

    headers = {
        "x-portkey-api-key": PORTKEY_API_KEY,
        "x-portkey-provider": PORTKEY_PROVIDER,
        "x-portkey-metadata": json.dumps(
            {
                "app": "agent-openwebui",
                "engine": engine,
                "component": component,
            },
            ensure_ascii=False,
        ),
    }

    if PORTKEY_VIRTUAL_KEY:
        headers["x-portkey-virtual-key"] = PORTKEY_VIRTUAL_KEY
        headers.pop("x-portkey-provider", None)

    if PORTKEY_CONFIG:
        headers["x-portkey-config"] = PORTKEY_CONFIG

    return headers


def get_client_api_key(primary_api_key: str | None) -> str | None:
    if not is_gateway_enabled():
        return primary_api_key
    if PORTKEY_VIRTUAL_KEY or PORTKEY_CONFIG:
        return PORTKEY_CLIENT_API_KEY
    return primary_api_key or PORTKEY_CLIENT_API_KEY


def get_langchain_client_options(
    *,
    model_id: str,
    primary_api_key: str | None,
    engine: str,
    component: str,
) -> dict[str, Any]:
    options: dict[str, Any] = {
        "model": resolve_model_name(model_id),
        "api_key": get_client_api_key(primary_api_key),
    }
    if is_gateway_enabled():
        options["base_url"] = PORTKEY_BASE_URL
        options["default_headers"] = build_gateway_headers(engine=engine, component=component)
    return options


def get_maf_client_options(
    *,
    model_id: str,
    primary_api_key: str | None,
    engine: str,
    component: str,
) -> dict[str, Any]:
    options: dict[str, Any] = {
        "model_id": resolve_model_name(model_id),
        "api_key": get_client_api_key(primary_api_key),
    }
    if is_gateway_enabled():
        options["base_url"] = PORTKEY_BASE_URL
        options["default_headers"] = build_gateway_headers(engine=engine, component=component)
    return options


def get_gateway_status() -> dict[str, Any]:
    enabled = is_gateway_enabled()
    if not enabled:
        mode = "disabled"
    elif PORTKEY_VIRTUAL_KEY:
        mode = "virtual_key"
    elif PORTKEY_CONFIG:
        mode = "config"
    else:
        mode = "provider_auth"

    return {
        "enabled": enabled,
        "provider": PORTKEY_PROVIDER,
        "base_url": PORTKEY_BASE_URL,
        "dashboard_url": PORTKEY_DASHBOARD_URL,
        "mode": mode,
        "virtual_key_configured": bool(PORTKEY_VIRTUAL_KEY),
        "config_configured": bool(PORTKEY_CONFIG),
        "model_prefix": PORTKEY_MODEL_PREFIX or None,
    }
