import evoagentx.workflow.operators as operator
import runs.seed45.train.lfm2_5_16k.bilevel.round_10.prompt as prompt_custom
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
        # Generate first solution using step-by-step arithmetic approach
        solution1 = await self.custom(
            input=problem,
            instruction=prompt_custom.SOLVE_MATH_PROMPT_A,
        )
        
        # Generate second solution using equation/variable approach
        solution2 = await self.custom(
            input=problem,
            instruction=prompt_custom.SOLVE_MATH_PROMPT_B,
        )
        
        # Ensemble: pick the most reliable answer by comparing both solutions
        ensemble_input = (
            f"Problem: {problem}\n\n"
            f"Solution 1:\n{solution1['response']}\n\n"
            f"Solution 2:\n{solution2['response']}"
        )
        final = await self.custom(
            input=ensemble_input,
            instruction=prompt_custom.ENSEMBLE_PROMPT,
        )
        return final["response"]
