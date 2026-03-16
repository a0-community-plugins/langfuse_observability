import os
import sys

_PLUGIN_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if _PLUGIN_ROOT not in sys.path:
    sys.path.append(_PLUGIN_ROOT)

from helpers.extension import Extension
from langfuse_helpers.langfuse_helper import get_langfuse_client


class LangfuseInit(Extension):

    def execute(self, **kwargs):
        get_langfuse_client()
