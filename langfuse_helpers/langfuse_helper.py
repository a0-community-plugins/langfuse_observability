import os
import sys
import random
import logging
import subprocess
from typing import Any

logger = logging.getLogger(__name__)

# Lazy-loaded singleton
_client = None
_client_initialized = False
_install_attempted = False


def _ensure_langfuse_installed():
    """Auto-install langfuse package if not present."""
    global _install_attempted
    if _install_attempted:
        return
    _install_attempted = True
    try:
        import langfuse  # noqa: F401
    except ImportError:
        logger.info("langfuse package not found, installing...")
        try:
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", "langfuse"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            logger.info("langfuse package installed successfully")
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to install langfuse: {e}")

    # Always attempt model compat patch after install check
    _patch_langfuse_models()


def _patch_langfuse_models() -> None:
    """Make 'organization' and 'metadata' Optional in the langfuse Project model.

    langfuse SDK >= 3.14 added required fields (organization, metadata) that
    older self-hosted servers do not return. Patching the Pydantic model to
    default them to None keeps auth_check() working without downgrading the SDK.
    Safe to call multiple times; does nothing if already patched or on failure.
    """
    try:
        import typing
        from pydantic_core import PydanticUndefined
        from langfuse.api.projects.types.project import Project

        needs_rebuild = False
        for field_name in ("organization", "metadata"):
            if field_name not in Project.model_fields:
                continue
            fi = Project.model_fields[field_name]
            if fi.default is PydanticUndefined:
                fi.default = None
                needs_rebuild = True
                # Widen annotation to Optional so Pydantic rebuilds correctly
                if field_name in Project.__annotations__:
                    orig = Project.__annotations__[field_name]
                    Project.__annotations__[field_name] = typing.Optional[orig]

        if needs_rebuild:
            Project.model_rebuild(force=True)
            logger.info(
                "Patched langfuse Project model: 'organization' and 'metadata' "
                "are now Optional for compatibility with older self-hosted servers."
            )
    except ImportError:
        pass  # langfuse not installed yet — will be called again after install
    except Exception as e:
        logger.warning(f"Could not patch langfuse Project model: {e}")


def get_langfuse_config() -> dict[str, Any]:
    """Get Langfuse configuration with plugin config > env var > default precedence."""
    from helpers.plugins import get_plugin_config

    config = get_plugin_config("langfuse_observability", None) or {}
    public_key = config.get("langfuse_public_key") or os.getenv("LANGFUSE_PUBLIC_KEY", "")
    secret_key = config.get("langfuse_secret_key") or os.getenv("LANGFUSE_SECRET_KEY", "")
    host = config.get("langfuse_host") or os.getenv("LANGFUSE_HOST", "https://us.cloud.langfuse.com")
    enabled = config.get("langfuse_enabled", False)
    sample_rate = float(config.get("langfuse_sample_rate", 1.0))

    # Auto-enable if keys are set via env vars but toggle is off
    if not enabled and public_key and secret_key:
        enabled = True

    return {
        "enabled": enabled,
        "public_key": public_key,
        "secret_key": secret_key,
        "host": host,
        "sample_rate": sample_rate,
    }


def get_langfuse_client():
    """Get or create the Langfuse client singleton. Returns None if disabled or not configured."""
    global _client, _client_initialized

    config = get_langfuse_config()

    if not config["enabled"] or not config["public_key"] or not config["secret_key"]:
        _client = None
        _client_initialized = False
        return None

    # Return cached client if already initialized
    if _client_initialized and _client is not None:
        return _client

    _ensure_langfuse_installed()

    try:
        from langfuse import Langfuse

        _client = Langfuse(
            public_key=config["public_key"],
            secret_key=config["secret_key"],
            host=config["host"],
        )
        _client_initialized = True
        logger.info("Langfuse client initialized successfully")
        return _client
    except Exception as e:
        logger.warning(f"Failed to initialize Langfuse client: {e}")
        _client = None
        _client_initialized = False
        return None


def reset_client():
    """Reset the client singleton (call when settings change)."""
    global _client, _client_initialized
    if _client:
        try:
            _client.flush()
        except Exception:
            pass
    _client = None
    _client_initialized = False


def should_sample() -> bool:
    """Check if this interaction should be sampled based on sample_rate."""
    config = get_langfuse_config()
    rate = config.get("sample_rate", 1.0)
    if rate >= 1.0:
        return True
    if rate <= 0.0:
        return False
    return random.random() < rate
