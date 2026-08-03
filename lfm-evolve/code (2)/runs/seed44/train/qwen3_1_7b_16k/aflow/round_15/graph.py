import evoagentx.workflow.operators as operator
import runs.seed44.train.qwen3_1_7b_16k.aflow.round_15.prompt as prompt_custom
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
        
        # Stage 2a: Solve using the decomposed structure
        solution = await self.custom(
            input=problem + f"\n\nKey information extracted:\n{decompose['response']}",
            instruction=prompt_custom.SOLVE_WITH_CONTEXT_PROMPT,
        )
        
        # Stage 2b: Alternative solve using step-by-step reasoning independently
        alt_solution = await self.custom(
            input=problem + f"\n\nKey information extracted:\n{decompose['response']}",
            instruction=prompt_custom.ALT_SOLVE_PROMPT,
        )
        
        # Stage 3: Verify by comparing both solutions and confirm correct answer
        verified = await self.custom(
            input=problem + f"\n\nSolution A:\n{solution['response']}\n\nSolution B:\n{alt_solution['response']}",
            instruction=prompt_custom.VERIFY_PROMPT,
        )
        
        # Stage 4: Recheck - independently recompute arithmetic to catch any remaining errors
        recheck = await self.custom(
            input=problem + f"\n\nProposed answer from verification:\n{verified['response']}",
            instruction=prompt_custom.RECHECK_PROMPT,
        )
        
        # Stage 5: Final extraction to ensure clean numeric answer with proper format
        final = await self.custom(
            input=f"Problem: {problem}\n\nVerified and rechecked solution:\n{recheck['response']}",
            instruction=prompt_custom.EXTRACT_PROMPT,
        )
        return final["response"]
