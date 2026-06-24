import evoagentx.workflow.operators as operator
import workflows.run10_seed84.aflow.round_13.prompt as prompt_custom
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
        # Generate first solution using step-by-step reasoning
        solution1 = await self.custom(
            input=problem,
            instruction=prompt_custom.SOLVE_MATH_PROMPT,
        )
        # Generate second solution using equation-based approach
        solution2 = await self.custom(
            input=problem,
            instruction=prompt_custom.SOLVE_MATH_ALT_PROMPT,
        )
        # Synthesize both solutions, pick the most consistent/correct answer
        synthesized = await self.custom(
            input=problem + f"\n\nSolution A:\n{solution1['response']}\n\nSolution B:\n{solution2['response']}",
            instruction=prompt_custom.SYNTHESIZE_MATH_PROMPT,
        )
        # Final verification pass
        verified = await self.custom(
            input=problem + f"\n\nProposed solution:\n{synthesized['response']}",
            instruction=prompt_custom.VERIFY_MATH_PROMPT,
        )
        return verified["response"]
