import evoagentx.workflow.operators as operator
import runs.seed44.train.qwen3_1_7b_16k.bilevel.round_2.prompt as prompt_custom
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
        solution = await self.custom(
            input=problem,
            instruction=prompt_custom.SOLVE_MATH_PROMPT,
        )
        reviewed = await self.custom(
            input=problem + f"\n\nPrevious solution:\n{solution['response']}",
            instruction=prompt_custom.REVIEW_MATH_PROMPT,
        )
        return reviewed["response"]
