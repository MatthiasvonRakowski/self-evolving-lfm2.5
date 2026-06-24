import evoagentx.workflow.operators as operator
import workflows.run10_seed84.aflow.round_15.prompt as prompt_custom
from evoagentx.models.model_configs import LLMConfig
from evoagentx.benchmark.benchmark import Benchmark
from evoagentx.models.model_utils import create_llm_instance

import asyncio

class Workflow:
    def __init__(self, name: str, llm_config: LLMConfig, benchmark: Benchmark | None = None):
        self.name = name
        self.llm = create_llm_instance(llm_config)
        self.benchmark = benchmark
        self.custom = operator.Custom(self.llm)

    async def __call__(self, problem: str, **kwargs) -> str:
        # Generate two independent solutions in parallel
        sol1, sol2 = await asyncio.gather(
            self.custom(input=problem, instruction=prompt_custom.SOLVE_MATH_PROMPT_A),
            self.custom(input=problem, instruction=prompt_custom.SOLVE_MATH_PROMPT_B),
        )
        # Aggregate: pick the most consistent answer
        combined_input = (
            f"Problem: {problem}\n\n"
            f"Solution 1:\n{sol1['response']}\n\n"
            f"Solution 2:\n{sol2['response']}"
        )
        final = await self.custom(
            input=combined_input,
            instruction=prompt_custom.AGGREGATE_PROMPT,
        )
        return final["response"]
