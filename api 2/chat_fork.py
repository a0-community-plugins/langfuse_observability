import os
import sys

_PLUGIN_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PLUGIN_ROOT not in sys.path:
    sys.path.append(_PLUGIN_ROOT)

from helpers.api import ApiHandler, Input, Output, Request, Response
from langfuse_helpers.fork_helper import fork_context
from agent import AgentContext


class ChatFork(ApiHandler):
    async def process(self, input: Input, request: Request) -> Output:
        context_id = input.get("context_id", "")
        if not context_id:
            return {"success": False, "error": "context_id is required"}

        # Get source context
        source = AgentContext.get(context_id)
        if not source:
            return {"success": False, "error": f"Context {context_id} not found"}

        # Optional: fork at a specific log position
        fork_at_log_no = input.get("fork_at_log_no", None)
        if fork_at_log_no is not None:
            fork_at_log_no = int(fork_at_log_no)

        try:
            new_context = fork_context(source, fork_at_log_no=fork_at_log_no)
        except Exception as e:
            return {"success": False, "error": f"Fork failed: {e}"}

        # Notify other tabs about the new context
        from helpers.state_monitor_integration import mark_dirty_all
        mark_dirty_all(reason="api.chat_fork.ChatFork")

        return {
            "success": True,
            "context_id": new_context.id,
            "name": new_context.name,
        }
