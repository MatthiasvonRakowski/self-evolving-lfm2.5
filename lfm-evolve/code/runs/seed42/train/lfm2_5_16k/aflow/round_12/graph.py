import evoagentx.workflow.operators as operator
import runs.seed42.train.lfm2_5_16k.aflow.round_12.prompt as prompt_custom
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
        solution = await self.custom(
            input=problem,
            instruction=prompt_custom.SOLVE_MATH_PROMPT,
        )
        verified = await self.custom(
            input=problem + f"\n\nPrevious solution:\n{solution['response']}",
            instruction=prompt_custom.VERIFY_MATH_PROMPT,
        )
        
        # Check if verification found disagreement - if so, do a final arbitration
        disagreement_keywords = ["disagree", "discrepancy", "error", "incorrect", "wrong", "differ", "mismatch"]
        verify_text = verified['response'].lower()
        has_disagreement = any(kw in verify_text for kw in disagreement_keywords)
        
        if has_disagreement:
            final = await self.custom(
                input=problem + f"\n\nAttempt 1:\n{solution['response']}\n\nAttempt 2 (with review):\n{verified['response']}",
                instruction=prompt_custom.ARBITRATE_MATH_PROMPT,
            )
            return final["response"]
        
        return verified["response"]
