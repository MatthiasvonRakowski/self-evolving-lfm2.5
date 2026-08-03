import evoagentx.workflow.operators as operator
import runs.seed45.train.lfm2_5_16k.bilevel.round_9.prompt as prompt_custom
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
        
        # Critique solution1 to catch arithmetic errors before ensemble
        critique_input = (
            f"Problem: {problem}\n\n"
            f"Solution to review:\n{solution1['response']}"
        )
        critique = await self.custom(
            input=critique_input,
            instruction=prompt_custom.CRITIQUE_PROMPT,
        )
        
        # Ensemble: pick the most reliable answer by comparing critique + solution2
        ensemble_input = (
            f"Problem: {problem}\n\n"
            f"Solution 1 (with self-review):\n{critique['response']}\n\n"
            f"Solution 2:\n{solution2['response']}"
        )
        final = await self.custom(
            input=ensemble_input,
            instruction=prompt_custom.ENSEMBLE_PROMPT,
        )
        return final["response"]
