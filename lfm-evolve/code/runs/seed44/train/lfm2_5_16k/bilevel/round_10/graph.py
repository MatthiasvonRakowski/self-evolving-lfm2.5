import evoagentx.workflow.operators as operator
import runs.seed44.train.lfm2_5_16k.bilevel.round_10.prompt as prompt_custom
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
        # Step 1: First solution approach
        solution1 = await self.custom(
            input=problem,
            instruction=prompt_custom.SOLVE_MATH_PROMPT,
        )
        answer1 = solution1["response"]

        # Step 2: Second solution using alternative prompt
        solution2 = await self.custom(
            input=problem,
            instruction=prompt_custom.SOLVE_MATH_ALT_PROMPT,
        )
        answer2 = solution2["response"]

        # Step 3: Review both solutions and synthesize the best answer
        review = await self.custom(
            input=f"Problem: {problem}\n\nSolution A:\n{answer1}\n\nSolution B:\n{answer2}",
            instruction=prompt_custom.REVIEW_MATH_PROMPT,
        )
        return review["response"]
