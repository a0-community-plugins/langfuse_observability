import json

from helpers.extension import Extension
from agent import Agent, LoopData


def _strip_provider(model_name: str) -> str:
    if "/" in model_name and not model_name.startswith("ft:"):
        return model_name.split("/", 1)[1]
    return model_name


def _stringify(content) -> str:
    """Convert any MessageContent to a readable string."""
    if isinstance(content, str):
        return content
    if isinstance(content, dict):
        if "raw_content" in content:
            return content.get("preview") or json.dumps(content["raw_content"], default=str, indent=2)
        return json.dumps(content, default=str, indent=2)
    if isinstance(content, list):
        parts = []
        for item in content:
            parts.append(_stringify(item))
        return "\n".join(parts)
    return str(content)


def _format_prompt(system_parts, history_output) -> str:
    """Build a clean, readable markdown-formatted prompt string."""
    sections = []

    if system_parts:
        system_text = "\n\n".join(str(s) for s in system_parts)
        sections.append(f"# System\n\n{system_text}")

    if history_output:
        for msg in history_output:
            role = "Assistant" if msg.get("ai") else "User"
            content = _stringify(msg.get("content", ""))
            if content.strip():
                sections.append(f"# {role}\n\n{content}")

    return "\n\n---\n\n".join(sections)


class LangfuseGenerationStart(Extension):

    async def execute(self, loop_data: LoopData = LoopData(), **kwargs):
        if not loop_data.params_persistent.get("lf_sampled"):
            return

        parent = loop_data.params_temporary.get("lf_iteration_span")
        if not parent:
            parent = loop_data.params_persistent.get("lf_trace")
        if not parent:
            return

        model = self.agent.get_chat_model()
        model_name = getattr(model, "model_name", "unknown") if model else "unknown"
        model_name = _strip_provider(model_name)

        # Build readable formatted prompt string
        prompt_text = _format_prompt(loop_data.system, loop_data.history_output)

        # Get pre-computed input token count
        ctx_window = self.agent.get_data(Agent.DATA_NAME_CTX_WINDOW)
        input_tokens = 0
        if isinstance(ctx_window, dict):
            input_tokens = int(ctx_window.get("tokens", 0))

        generation = parent.start_observation(
            name="main-llm",
            as_type="generation",
            model=model_name,
            input=prompt_text or None,
            metadata={
                "agent_number": self.agent.number,
                "iteration": loop_data.iteration,
            },
        )
        loop_data.params_temporary["lf_generation"] = generation
        loop_data.params_temporary["lf_input_tokens"] = input_tokens
