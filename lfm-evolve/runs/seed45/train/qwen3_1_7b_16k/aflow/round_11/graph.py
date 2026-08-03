import evoagentx.workflow.operators as operator
import runs.seed45.train.qwen3_1_7b_16k.aflow.round_11.prompt as prompt_custom
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
        # Step 1: Rephrase the problem to extract key information clearly
        rephrased = await self.custom(
            input=problem,
            instruction=prompt_custom.REPHRASE_PROMPT,
        )
        # Step 2: Solve using the original + rephrased problem for better context
        solution = await self.custom(
            input=f"Original problem: {problem}\nClarified version: {rephrased['response']}",
            instruction=prompt_custom.SOLVE_MATH_PROMPT,
        )
        return solution["response"]
