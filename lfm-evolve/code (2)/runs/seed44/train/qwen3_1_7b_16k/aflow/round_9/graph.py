import evoagentx.workflow.operators as operator
import runs.seed44.train.qwen3_1_7b_16k.aflow.round_9.prompt as prompt_custom
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
        # Stage 1: Decompose and extract key information
        decompose = await self.custom(
            input=problem,
            instruction=prompt_custom.DECOMPOSE_PROMPT,
        )
        
        # Stage 2: Solve using the decomposed structure
        solution = await self.custom(
            input=problem + f"\n\nKey information extracted:\n{decompose['response']}",
            instruction=prompt_custom.SOLVE_WITH_CONTEXT_PROMPT,
        )
        
        # Stage 3: Verify and correct the solution by re-solving independently
        verified = await self.custom(
            input=problem + f"\n\nProposed solution to check:\n{solution['response']}",
            instruction=prompt_custom.VERIFY_PROMPT,
        )
        return verified["response"]
