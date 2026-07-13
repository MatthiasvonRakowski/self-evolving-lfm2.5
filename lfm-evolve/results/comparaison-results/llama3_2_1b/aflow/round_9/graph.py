import evoagentx.workflow.operators as operator
import output2.llama3_2_1b.aflow.round_9.prompt as prompt_custom
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
        # Step 1: Initial solution with careful arithmetic
        solution = await self.custom(
            input=problem,
            instruction=prompt_custom.SOLVE_MATH_PROMPT,
        )
        initial = solution["response"]

        # Step 2: Review and verify the solution
        review = await self.custom(
            input=f"Problem: {problem}\n\nInitial Solution:\n{initial}",
            instruction=prompt_custom.REVIEW_MATH_PROMPT,
        )
        return review["response"]
