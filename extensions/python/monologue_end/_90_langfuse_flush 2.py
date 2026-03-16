import os
import sys

_PLUGIN_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if _PLUGIN_ROOT not in sys.path:
    sys.path.append(_PLUGIN_ROOT)

from helpers.extension import Extension
from langfuse_helpers.langfuse_helper import get_langfuse_client
from agent import LoopData


class LangfuseFlush(Extension):

    async def execute(self, loop_data: LoopData = LoopData(), **kwargs):
        if not loop_data.params_persistent.get("lf_sampled"):
            return

        client = get_langfuse_client()
        if not client:
            return

        trace = loop_data.params_persistent.get("lf_trace")
        if trace:
            try:
                trace.update(
                    output=loop_data.last_response[:2000] if loop_data.last_response else "",
                )
                trace.end()
            except Exception:
                pass

        try:
            client.flush()
        except Exception:
            pass

        loop_data.params_persistent.pop("lf_trace", None)
        loop_data.params_persistent.pop("lf_root_trace", None)
        loop_data.params_persistent.pop("lf_sampled", None)
