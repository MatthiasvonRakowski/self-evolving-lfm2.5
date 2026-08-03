import evoagentx.workflow.operators as operator
import runs.seed42.train.qwen3_1_7b_16k.aflow.round_15.prompt as prompt_custom
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
        initial_response = solution["response"]

        # Step 2: Review and verify the solution
        review = await self.custom(
            input=f"Problem: {problem}\n\nProposed Solution:\n{initial_response}",
            instruction=prompt_custom.REVIEW_MATH_PROMPT,
        )
        review_response = review["response"]

        # Step 3: Final reconciliation — if answers differ, do independent re-solve
        final = await self.custom(
            input=f"Problem: {problem}\n\nAttempt 1:\n{initial_response}\n\nAttempt 2 (Review):\n{review_response}",
            instruction=prompt_custom.RECONCILE_MATH_PROMPT,
        )
        return final["response"]
