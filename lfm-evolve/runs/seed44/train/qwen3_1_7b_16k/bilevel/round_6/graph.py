import evoagentx.workflow.operators as operator
import runs.seed44.train.qwen3_1_7b_16k.bilevel.round_6.prompt as prompt_custom
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
        # Generate two solutions using different prompting strategies in parallel
        sol_a, sol_b = await asyncio.gather(
            self.custom(input=problem, instruction=prompt_custom.SOLVE_MATH_ALGEBRAIC_PROMPT),
            self.custom(input=problem, instruction=prompt_custom.SOLVE_MATH_VERBAL_PROMPT),
        )
        # Synthesize: pick the answer both agree on, or the more carefully reasoned one
        synthesis = await self.custom(
            input=f"Problem: {problem}\n\nSolution A:\n{sol_a['response']}\n\nSolution B:\n{sol_b['response']}",
            instruction=prompt_custom.ENSEMBLE_PICK_PROMPT,
        )
        return synthesis["response"]
