from helpers.extension import Extension
from helpers.tokens import approximate_tokens
from agent import LoopData


class LangfuseGenerationEnd(Extension):

    async def execute(self, loop_data: LoopData = LoopData(), **kwargs):
        if not loop_data.params_persistent.get("lf_sampled"):
            return

        generation = loop_data.params_temporary.get("lf_generation")
        if not generation:
            return

        response_text = loop_data.last_response or ""
        input_tokens = loop_data.params_temporary.get("lf_input_tokens", 0)
        output_tokens = approximate_tokens(response_text) if response_text else 0

        try:
            update_kwargs = {"output": response_text}
            if input_tokens or output_tokens:
                update_kwargs["usage_details"] = {
                    "input": int(input_tokens),
                    "output": int(output_tokens),
                }
            generation.update(**update_kwargs)
            generation.end()
        except Exception:
            pass
