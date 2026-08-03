import evoagentx.workflow.operators as operator
import runs.seed45.train.qwen3_1_7b_16k.aflow.round_9.prompt as prompt_custom
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
        # First independent solution: arithmetic-focused
        solution_a = await self.custom(
            input=problem,
            instruction=prompt_custom.SOLVE_MATH_PROMPT_A,
        )
        # Second independent solution: logical/narrative-focused
        solution_b = await self.custom(
            input=problem,
            instruction=prompt_custom.SOLVE_MATH_PROMPT_B,
        )
        # Synthesize: pick the most consistent/correct answer
        synthesis = await self.custom(
            input=f"Problem: {problem}\nSolution 1:\n{solution_a['response']}\nSolution 2:\n{solution_b['response']}",
            instruction=prompt_custom.SYNTHESIZE_PROMPT,
        )
        return synthesis["response"]
