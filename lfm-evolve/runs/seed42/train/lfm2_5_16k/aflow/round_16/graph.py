import evoagentx.workflow.operators as operator
import runs.seed42.train.lfm2_5_16k.aflow.round_16.prompt as prompt_custom
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
        import asyncio
        solution1, solution2 = await asyncio.gather(
            self.custom(input=problem, instruction=prompt_custom.SOLVE_MATH_PROMPT),
            self.custom(input=problem, instruction=prompt_custom.SOLVE_MATH_PROMPT2),
        )
        reconciled = await self.custom(
            input=f"Problem: {problem}\n\nSolution A:\n{solution1['response']}\n\nSolution B:\n{solution2['response']}",
            instruction=prompt_custom.RECONCILE_PROMPT,
        )
        return reconciled["response"]
