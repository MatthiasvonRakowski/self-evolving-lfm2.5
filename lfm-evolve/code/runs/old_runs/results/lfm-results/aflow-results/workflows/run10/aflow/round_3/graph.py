import evoagentx.workflow.operators as operator
import workflows.run10.aflow.round_3.prompt as prompt_custom
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
            input=f"Problem: {problem}\n\nInitial Solution:\n{solution['response']}",
            instruction=prompt_custom.REVIEW_MATH_PROMPT,
        )
        final = await self.custom(
            input=f"Problem: {problem}\n\nAttempt 1:\n{solution['response']}\n\nAttempt 2 (reviewed):\n{reviewed['response']}",
            instruction=prompt_custom.FINALIZE_MATH_PROMPT,
        )
        return final["response"]
