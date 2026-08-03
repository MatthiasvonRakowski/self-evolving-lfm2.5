import evoagentx.workflow.operators as operator
import workflows.run10_seed85.aflow.round_23.prompt as prompt_custom
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
        # Step 1: Decompose the problem into key quantities and relationships
        decomposition = await self.custom(
            input=problem,
            instruction=prompt_custom.DECOMPOSE_PROMPT,
        )
        
        # Step 2: Solve using the decomposed structure for more accurate arithmetic
        solution = await self.custom(
            input=problem + "\n\nKey quantities and relationships identified:\n" + decomposition["response"],
            instruction=prompt_custom.SOLVE_WITH_DECOMP_PROMPT,
        )
        return solution["response"]
