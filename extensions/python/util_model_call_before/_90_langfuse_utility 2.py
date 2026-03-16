from helpers.extension import Extension
from helpers.tokens import approximate_tokens


def _strip_provider(model_name: str) -> str:
    if "/" in model_name and not model_name.startswith("ft:"):
        return model_name.split("/", 1)[1]
    return model_name


class LangfuseUtilityGeneration(Extension):

    async def execute(self, call_data: dict = {}, **kwargs):
        loop_data = self.agent.loop_data
        if not loop_data or not loop_data.params_persistent.get("lf_sampled"):
            return

        parent = loop_data.params_temporary.get("lf_iteration_span")
        if not parent:
            parent = loop_data.params_persistent.get("lf_trace")
        if not parent:
            return

        # End any previous utility generation that wasn't closed
        prev_gen = loop_data.params_temporary.get("lf_utility_gen")
        if prev_gen:
            try:
                prev_gen.end()
            except Exception:
                pass

        model = call_data.get("model")
        model_name = getattr(model, "model_name", "unknown") if model else "unknown"
        model_name = _strip_provider(model_name)

        system_msg = str(call_data.get("system", ""))
        user_msg = str(call_data.get("message", ""))

        # Build readable formatted prompt string (not JSON)
        parts = []
        if system_msg:
            parts.append(f"# System\n\n{system_msg}")
        if user_msg:
            parts.append(f"# User\n\n{user_msg}")
        prompt_text = "\n\n---\n\n".join(parts)

        # Estimate input tokens
        full_input = system_msg + "\n" + user_msg
        input_tokens = approximate_tokens(full_input) if full_input.strip() else 0

        generation = parent.start_observation(
            name="utility-llm",
            as_type="generation",
            model=model_name,
            input=prompt_text or None,
            metadata={
                "agent_number": self.agent.number,
                "call_type": "utility",
            },
        )
        loop_data.params_temporary["lf_utility_gen"] = generation
        loop_data.params_temporary["lf_utility_input_tokens"] = input_tokens
