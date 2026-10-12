"""FastAPI demo for configuration precedence.

Precedence (lowest -> highest): defaults -> config.<APP_ENV>.yaml -> .env
-> OS APP_* environment variables -> repeated ?set=key=value query overrides.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import dotenv_values
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

BASE_DIR = Path(__file__).resolve().parent

DEFAULTS: dict[str, Any] = {
    "port": 8000,
    "workers": 1,
    "debug": False,
    "log_level": "info",
    "api_key": "default-secret-000",
}

TRUE_VALUES = {"true", "1", "yes", "on"}


def normalize_key(key: str, *, layer: str = "generic") -> str | None:
    """Normalize configuration names and implement the NUM_WORKERS alias."""
    original = str(key).strip()
    upper = original.upper()

    if upper == "NUM_WORKERS":
        return "workers"
    # APP_ENV selects the YAML file; it is metadata, not an output setting.
    if upper == "APP_ENV":
        return None

    # OS layer accepts only APP_* variables. The .env layer accepts APP_*
    # as well as the explicit NUM_WORKERS alias.
    if layer == "os":
        if not upper.startswith("APP_"):
            return None
        original = original[4:]
    elif upper.startswith("APP_"):
        original = original[4:]

    normalized = original.strip().lower()
    return normalized or None


def coerce_value(key: str, value: Any) -> Any:
    """Coerce known settings to their required types; other values are strings."""
    if key in {"port", "workers"}:
        # bool is an int subclass, but configuration values should be numeric.
        return int(str(value).strip())
    if key == "debug":
        if isinstance(value, bool):
            return value
        return str(value).strip().lower() in TRUE_VALUES
    if value is None:
        return ""
    return str(value)


def apply_layer(config: dict[str, Any], values: dict[str, Any], *, layer: str = "generic") -> None:
    for raw_key, raw_value in values.items():
        if raw_value is None:
            continue
        key = normalize_key(str(raw_key), layer=layer)
        if key is not None:
            config[key] = coerce_value(key, raw_value)


def load_effective_config(cli_overrides: list[str] | None = None) -> dict[str, Any]:
    config = {key: coerce_value(key, value) for key, value in DEFAULTS.items()}

    # 1. Environment-specific YAML file, e.g. config.development.yaml.
    environment_name = os.environ.get("APP_ENV", "development").strip() or "development"
    yaml_path = BASE_DIR / f"config.{environment_name}.yaml"
    if yaml_path.is_file():
        with yaml_path.open("r", encoding="utf-8") as handle:
            yaml_config = yaml.safe_load(handle) or {}
        if isinstance(yaml_config, dict):
            apply_layer(config, yaml_config, layer="yaml")

    # 2. .env file. dotenv_values reads the file without overwriting OS env vars.
    env_path = BASE_DIR / ".env"
    if env_path.is_file():
        apply_layer(config, dict(dotenv_values(env_path)), layer="dotenv")

    # 3. OS environment variables with APP_ prefix. These override .env.
    apply_layer(config, dict(os.environ), layer="os")

    # 4. CLI query overrides are highest precedence. Split at the first '=' so
    # values that themselves contain '=' are retained.
    for assignment in cli_overrides or []:
        if "=" not in assignment:
            continue
        raw_key, raw_value = assignment.split("=", 1)
        key = normalize_key(raw_key, layer="cli")
        if key is not None:
            config[key] = coerce_value(key, raw_value)

    # Never return any actual API key, regardless of which layer supplied it.
    if "api_key" in config:
        config["api_key"] = "****"
    return config


app = FastAPI(title="12-Factor Config Precedence API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "OPTIONS"],
    allow_headers=["*"],
)


@app.get("/")
def health() -> dict[str, str]:
    return {"status": "ok", "endpoint": "/effective-config"}


@app.get("/effective-config")
def effective_config(set_values: list[str] | None = Query(default=None, alias="set")) -> dict[str, Any]:
    return load_effective_config(set_values)
