import evoagentx.workflow.operators as operator
import runs.seed45.train.lfm2_5_16k.aflow.round_1.prompt as prompt_custom
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
        # Step 1: Initial solution
        solution = await self.custom(
            input=problem,
            instruction=prompt_custom.SOLVE_MATH_PROMPT,
        )
        initial_answer = solution["response"]

        # Step 2: Review the solution for correctness
        review = await self.custom(
            input=f"Problem: {problem}\nSolution: {initial_answer}",
            instruction=prompt_custom.REVIEW_MATH_PROMPT,
        )
        review_text = review["response"]

        # Step 3: If review finds issues, generate a revised solution
        if "CORRECT" not in review_text.upper():
            revised = await self.custom(
                input=f"Problem: {problem}\nPrevious attempt: {initial_answer}\nReview feedback: {review_text}",
                instruction=prompt_custom.REVISE_MATH_PROMPT,
            )
            return revised["response"]

        return initial_answer
