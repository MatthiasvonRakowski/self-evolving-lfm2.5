import evoagentx.workflow.operators as operator
import runs.seed42.train.lfm2_5_16k.bilevel.round_10.prompt as prompt_custom
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
        # Step 1: Initial solution using step-by-step reasoning
        solution1 = await self.custom(
            input=problem,
            instruction=prompt_custom.SOLVE_MATH_PROMPT,
        )
        initial_response = solution1["response"]

        # Step 2: Second solution using quantity-focused approach
        solution2 = await self.custom(
            input=problem,
            instruction=prompt_custom.SOLVE_MATH_PROMPT_ALT,
        )
        alt_response = solution2["response"]

        # Step 3: Review both solutions and output the best/consensus answer
        review = await self.custom(
            input=f"Problem: {problem}\n\nSolution A:\n{initial_response}\n\nSolution B:\n{alt_response}",
            instruction=prompt_custom.VERIFY_MATH_PROMPT,
        )
        return review["response"]
