import evoagentx.workflow.operators as operator
import runs.seed45.train.qwen3_1_7b_16k.bilevel.round_2.prompt as prompt_custom
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
        # Step 1: Initial solution with careful step-by-step reasoning
        initial = await self.custom(
            input=problem,
            instruction=prompt_custom.SOLVE_MATH_PROMPT,
        )
        initial_solution = initial["response"]

        # Step 2: Review and verify the solution
        review = await self.custom(
            input=f"Problem: {problem}\n\nProposed Solution:\n{initial_solution}",
            instruction=prompt_custom.REVIEW_MATH_PROMPT,
        )
        review_solution = review["response"]

        # Step 3: Final answer extraction and confirmation
        final = await self.custom(
            input=f"Problem: {problem}\n\nSolution A:\n{initial_solution}\n\nSolution B (Verified):\n{review_solution}",
            instruction=prompt_custom.FINAL_ANSWER_PROMPT,
        )
        return final["response"]
