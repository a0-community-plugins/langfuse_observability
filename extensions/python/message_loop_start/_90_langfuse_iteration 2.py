from helpers.extension import Extension
from agent import LoopData


class LangfuseIterationStart(Extension):

    async def execute(self, loop_data: LoopData = LoopData(), **kwargs):
        if not loop_data.params_persistent.get("lf_sampled"):
            return

        trace = loop_data.params_persistent.get("lf_trace")
        if not trace:
            return

        span = trace.start_observation(
            name=f"iteration-{loop_data.iteration}",
            as_type="span",
            metadata={"iteration": loop_data.iteration},
        )
        loop_data.params_temporary["lf_iteration_span"] = span
