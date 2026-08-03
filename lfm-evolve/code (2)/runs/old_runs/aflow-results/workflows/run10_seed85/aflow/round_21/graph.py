import evoagentx.workflow.operators as operator
import workflows.run10_seed85.aflow.round_21.prompt as prompt_custom
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
        solution1 = await self.custom(
            input=problem,
            instruction=prompt_custom.SOLVE_MATH_PROMPT,
        )
        initial = solution1["response"]

        verified = await self.custom(
            input=f"Problem: {problem}\n\nProposed Solution:\n{initial}",
            instruction=prompt_custom.VERIFY_MATH_PROMPT,
        )
        verified_answer = verified["response"]

        solution2 = await self.custom(
            input=problem,
            instruction=prompt_custom.SOLVE_MATH_ALT_PROMPT,
        )
        alt_answer = solution2["response"]

        solution3 = await self.custom(
            input=problem,
            instruction=prompt_custom.SOLVE_MATH_THIRD_PROMPT,
        )
        third_answer = solution3["response"]

        final = await self.custom(
            input=f"Problem: {problem}\n\nSolution A:\n{verified_answer}\n\nSolution B:\n{alt_answer}\n\nSolution C:\n{third_answer}",
            instruction=prompt_custom.RECONCILE_PROMPT,
        )
        return final["response"]
