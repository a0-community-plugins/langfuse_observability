import os
import sys

_PLUGIN_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if _PLUGIN_ROOT not in sys.path:
    sys.path.append(_PLUGIN_ROOT)

from helpers.extension import Extension
from langfuse_helpers.langfuse_helper import get_langfuse_client, should_sample
from langfuse import LangfuseOtelSpanAttributes
from agents import Agent, LoopData


class LangfuseTraceStart(Extension):

    async def execute(self, loop_data: LoopData = LoopData(), **kwargs):
        client = get_langfuse_client()
        if not client:
            return

        if not should_sample():
            loop_data.params_persistent["lf_sampled"] = False
            return
        loop_data.params_persistent["lf_sampled"] = True

        agent = self.agent
        context_id = str(agent.context.id) if agent.context else "unknown"

        # Check for parent agent (subordinate nesting)
        superior = agent.get_data(Agent.DATA_NAME_SUPERIOR)
        if superior and hasattr(superior, "loop_data"):
            parent_span = superior.loop_data.params_temporary.get("lf_tool_span")
            if not parent_span:
                parent_span = superior.loop_data.params_temporary.get("lf_iteration_span")
            if not parent_span:
                parent_span = superior.loop_data.params_persistent.get("lf_trace")

            if parent_span:
                span = parent_span.start_observation(
                    name=f"agent-{agent.number}-monologue",
                    as_type="span",
                    metadata={"agent_number": agent.number},
                )
                loop_data.params_persistent["lf_trace"] = span
                loop_data.params_persistent["lf_root_trace"] = (
                    superior.loop_data.params_persistent.get("lf_root_trace")
                    or superior.loop_data.params_persistent.get("lf_trace")
                )
                return

        # Top-level agent: create a root observation (becomes a new trace in v4)
        user_msg = ""
        if loop_data.user_message:
            user_msg = str(loop_data.user_message.content)

        root_span = client.start_observation(
            name=f"agent-{agent.number}-monologue",
            as_type="span",
            input=user_msg,
            metadata={"agent_number": agent.number},
        )
        # Set trace-level session_id via the underlying OTel span attribute
        if hasattr(root_span, "_otel_span"):
            root_span._otel_span.set_attribute(
                LangfuseOtelSpanAttributes.TRACE_SESSION_ID, context_id
            )
        loop_data.params_persistent["lf_trace"] = root_span
        loop_data.params_persistent["lf_root_trace"] = root_span
        loop_data.params_persistent["lf_trace_id"] = root_span.trace_id
