import evoagentx.workflow.operators as operator
import runs.seed44.train.qwen3_1_7b_16k.aflow.round_6.prompt as prompt_custom
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
        # Generate first solution using analytical approach
        solution1 = await self.custom(
            input=problem,
            instruction=prompt_custom.SOLVE_MATH_PROMPT_A,
        )
        # Generate second solution using arithmetic-focused approach
        solution2 = await self.custom(
            input=problem,
            instruction=prompt_custom.SOLVE_MATH_PROMPT_B,
        )
        # Select the best/most consistent answer from both solutions
        final = await self.custom(
            input=f"Problem: {problem}\nSolution 1:\n{solution1['response']}\nSolution 2:\n{solution2['response']}",
            instruction=prompt_custom.SELECT_BEST_PROMPT,
        )
        return final["response"]
