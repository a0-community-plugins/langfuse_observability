from helpers.extension import Extension
from helpers.tokens import approximate_tokens


class LangfuseUtilityGenerationEnd(Extension):

    async def execute(self, call_data: dict = {}, response: str = "", **kwargs):
        loop_data = self.agent.loop_data
        if not loop_data or not loop_data.params_persistent.get("lf_sampled"):
            return

        generation = loop_data.params_temporary.get("lf_utility_gen")
        if not generation:
            return

        input_tokens = loop_data.params_temporary.get("lf_utility_input_tokens", 0)
        output_tokens = approximate_tokens(response) if response else 0

        try:
            update_kwargs = {"output": response}
            if input_tokens or output_tokens:
                update_kwargs["usage_details"] = {
                    "input": int(input_tokens),
                    "output": int(output_tokens),
                }
            generation.update(**update_kwargs)
            generation.end()
        except Exception:
            pass

        loop_data.params_temporary.pop("lf_utility_gen", None)
        loop_data.params_temporary.pop("lf_utility_input_tokens", None)
