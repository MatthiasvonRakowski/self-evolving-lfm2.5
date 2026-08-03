import evoagentx.workflow.operators as operator
import runs.seed45.train.lfm2_5_16k.bilevel.round_4.prompt as prompt_custom
from evoagentx.models.model_configs import LLMConfig
from evoagentx.benchmark.benchmark import Benchmark
from evoagentx.models.model_utils import create_llm_instance

class Workflow:
    def __init__(self, name: str, llm_config: LLMConfig, benchmark: Benchmark | None = None):
        self.name = name
        self.llm = create_llm_instance(llm_config)
        self.benchmark = benchmark
        self.custom = operator.Custom(self.llm)

    async def __call__(self, problem: str, **kwargs) -> str:
        initial = await self.custom(
            input=problem,
            instruction=prompt_custom.SOLVE_MATH_PROMPT,
        )
        reviewed = await self.custom(
            input=f"Problem: {problem}\n\nPrevious solution:\n{initial['response']}",
            instruction=prompt_custom.REVIEW_MATH_PROMPT,
        )
        return reviewed["response"]
