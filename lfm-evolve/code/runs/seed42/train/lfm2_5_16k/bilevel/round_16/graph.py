import evoagentx.workflow.operators as operator
import runs.seed42.train.lfm2_5_16k.bilevel.round_16.prompt as prompt_custom
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
        # Step 1: Decompose the problem into clear sub-questions
        decomposition = await self.custom(
            input=problem,
            instruction=prompt_custom.DECOMPOSE_MATH_PROMPT,
        )
        decomposed = decomposition["response"]

        # Step 2a: Solve using the decomposed structure as a guide
        solution_a = await self.custom(
            input=f"Original Problem: {problem}\n\nProblem Breakdown:\n{decomposed}",
            instruction=prompt_custom.SOLVE_MATH_PROMPT,
        )
        response_a = solution_a["response"]

        # Step 2b: Solve independently using direct arithmetic reasoning
        solution_b = await self.custom(
            input=problem,
            instruction=prompt_custom.SOLVE_DIRECT_PROMPT,
        )
        response_b = solution_b["response"]

        # Step 3: Compare both solutions and verify the correct answer
        review = await self.custom(
            input=f"Problem: {problem}\n\nSolution A:\n{response_a}\n\nSolution B:\n{response_b}",
            instruction=prompt_custom.VERIFY_ENSEMBLE_PROMPT,
        )
        return review["response"]
