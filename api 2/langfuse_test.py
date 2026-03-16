import os
import sys

_PLUGIN_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PLUGIN_ROOT not in sys.path:
    sys.path.append(_PLUGIN_ROOT)

from helpers.api import ApiHandler, Request, Response
from helpers.plugins import get_plugin_config


# Matches the core PASSWORD_PLACEHOLDER pattern
_SECRET_PLACEHOLDER = "***"


class LangfuseTest(ApiHandler):

    async def process(self, input: dict, request: Request) -> dict | Response:
        public_key = input.get("public_key", "")
        secret_key = input.get("secret_key", "")
        host = input.get("host", "https://us.cloud.langfuse.com")

        # If frontend sent the masked placeholder, use the real stored key
        if secret_key == _SECRET_PLACEHOLDER:
            config = get_plugin_config("a0_community_plugins__langfuse_observability", None) or {}
            secret_key = config.get("langfuse_secret_key", "")

        if not public_key or not secret_key:
            return {"success": False, "error": "Public key and secret key are required"}

        try:
            from langfuse_helpers.langfuse_helper import _ensure_langfuse_installed
            _ensure_langfuse_installed()
            from langfuse import Langfuse

            client = Langfuse(
                public_key=public_key,
                secret_key=secret_key,
                host=host,
            )
            result = client.auth_check()
            client.flush()
            return {"success": result, "error": "" if result else "Authentication failed"}
        except ImportError:
            return {"success": False, "error": "langfuse package not installed. Could not auto-install."}
        except Exception as e:
            return {"success": False, "error": str(e)}
