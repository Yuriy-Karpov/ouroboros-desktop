"""Helpers shared by server startup, onboarding, and WebSocket liveness."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Awaitable, Callable

from ouroboros.config import SETTINGS_DEFAULTS


_OPENAI_AUTO_DEFAULTS = {
    "OUROBOROS_MODEL": "openai::gpt-5.2",
    "OUROBOROS_MODEL_CODE": "openai::gpt-5.2",
    "OUROBOROS_MODEL_LIGHT": "openai::gpt-4.1",
    "OUROBOROS_MODEL_FALLBACK": "openai::gpt-4.1",
}
_MODEL_LANE_KEYS = tuple(_OPENAI_AUTO_DEFAULTS.keys())
_OPENAI_REVIEW_RUNS = 3


def _truthy_setting(value) -> bool:
    return str(value or "").strip().lower() in {"true", "1", "yes", "on"}


def _setting_text(settings: dict, key: str) -> str:
    return str(settings.get(key, "") or "").strip()


def _parse_model_list(value: str) -> list[str]:
    return [item.strip() for item in str(value or "").split(",") if item.strip()]


def _serialize_model_list(models: list[str]) -> str:
    return ",".join(model.strip() for model in models if str(model or "").strip())


def _migrate_openai_model_value(value: str) -> str:
    text = str(value or "").strip()
    if not text.startswith("openai/"):
        return text
    return f"openai::{text[len('openai/'):]}"


def _is_official_openai_only_remote(settings: dict) -> bool:
    has_openrouter = bool(_setting_text(settings, "OPENROUTER_API_KEY"))
    has_official_openai = bool(_setting_text(settings, "OPENAI_API_KEY"))
    has_legacy_openai_base = bool(_setting_text(settings, "OPENAI_BASE_URL"))
    has_compatible = bool(_setting_text(settings, "OPENAI_COMPATIBLE_API_KEY"))
    has_cloudru = bool(_setting_text(settings, "CLOUDRU_FOUNDATION_MODELS_API_KEY"))
    return (
        not has_openrouter
        and has_official_openai
        and not has_legacy_openai_base
        and not has_compatible
        and not has_cloudru
    )


def _normalize_openai_only_review_models(settings: dict) -> str:
    main_model = _setting_text(settings, "OUROBOROS_MODEL")
    current_models = _parse_model_list(_setting_text(settings, "OUROBOROS_REVIEW_MODELS"))
    migrated_models = [_migrate_openai_model_value(model) for model in current_models]

    if not main_model.startswith("openai::"):
        return _serialize_model_list(migrated_models)

    has_non_openai_models = any(not model.startswith("openai::") for model in migrated_models)
    if not migrated_models or len(migrated_models) < 2 or has_non_openai_models:
        return _serialize_model_list([main_model] * _OPENAI_REVIEW_RUNS)
    return _serialize_model_list(migrated_models)


def has_remote_provider(settings: dict) -> bool:
    """Return True when any supported remote-provider credential is configured."""
    return any(
        str(settings.get(key, "") or "").strip()
        for key in (
            "OPENROUTER_API_KEY",
            "OPENAI_API_KEY",
            "OPENAI_COMPATIBLE_API_KEY",
            "CLOUDRU_FOUNDATION_MODELS_API_KEY",
        )
    )


def has_local_model_source(settings: dict) -> bool:
    """Return True when a local model source has been configured."""
    return bool(str(settings.get("LOCAL_MODEL_SOURCE", "") or "").strip())


def has_local_routing(settings: dict) -> bool:
    """Return True when any model lane is configured to use the local server."""
    return any(
        _truthy_setting(settings.get(k))
        for k in ("USE_LOCAL_MAIN", "USE_LOCAL_CODE", "USE_LOCAL_LIGHT", "USE_LOCAL_FALLBACK")
    )


def has_startup_ready_provider(settings: dict) -> bool:
    """Return True when startup/onboarding should consider runtime configured."""
    return has_remote_provider(settings) or has_local_model_source(settings)


def has_supervisor_provider(settings: dict) -> bool:
    """Return True when the runtime has enough provider config to start supervisor."""
    return has_remote_provider(settings) or has_local_routing(settings)


def apply_runtime_provider_defaults(settings: dict) -> tuple[dict, bool, list[str]]:
    """Auto-fill safe runtime defaults for the agreed provider cases."""
    normalized = dict(settings)

    # Only auto-remap when official OpenAI is the sole remote runtime lane.
    if not _is_official_openai_only_remote(normalized):
        return normalized, False, []

    changed_keys: list[str] = []
    for key in _MODEL_LANE_KEYS:
        raw_current = _setting_text(normalized, key)
        current = _migrate_openai_model_value(raw_current)
        default = _setting_text(SETTINGS_DEFAULTS, key)
        auto_value = _OPENAI_AUTO_DEFAULTS[key]
        next_value = auto_value if current in {"", default} else current
        if next_value != raw_current:
            normalized[key] = next_value
            changed_keys.append(key)

    review_models = _normalize_openai_only_review_models(normalized)
    if review_models != _setting_text(normalized, "OUROBOROS_REVIEW_MODELS"):
        normalized["OUROBOROS_REVIEW_MODELS"] = review_models
        changed_keys.append("OUROBOROS_REVIEW_MODELS")

    return normalized, bool(changed_keys), changed_keys


def setup_remote_if_configured(settings: dict, log) -> None:
    """Set up GitHub remote and migrate credentials if configured."""
    slug = settings.get("GITHUB_REPO", "")
    token = settings.get("GITHUB_TOKEN", "")
    if not slug or not token:
        return
    from supervisor.git_ops import configure_remote, migrate_remote_credentials

    remote_ok, remote_msg = configure_remote(slug, token)
    if not remote_ok:
        log.warning("Remote configuration failed on startup: %s", remote_msg)
        return
    mig_ok, mig_msg = migrate_remote_credentials()
    if not mig_ok:
        log.warning("Credential migration failed on startup: %s", mig_msg)


async def ws_heartbeat_loop(
    has_clients_fn: Callable[[], bool],
    broadcast_fn: Callable[[dict], Awaitable[None]],
    interval_sec: float = 15.0,
) -> None:
    """Keep embedded clients active and give watchdogs a steady liveness signal."""
    while True:
        await asyncio.sleep(interval_sec)
        if not has_clients_fn():
            continue
        await broadcast_fn({
            "type": "heartbeat",
            "ts": datetime.now(timezone.utc).isoformat(),
        })
