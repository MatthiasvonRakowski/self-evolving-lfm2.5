import evoagentx.workflow.operators as operator
import runs.seed44.train.qwen3_1_7b_16k.aflow.round_10.prompt as prompt_custom
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
        # Pass 1: Generate a rough scratchpad with all arithmetic laid out
        scratchpad = await self.custom(
            input=problem,
            instruction=prompt_custom.SCRATCHPAD_PROMPT,
        )
        
        # Pass 2: Use scratchpad as grounding context to produce clean final answer
        solution = await self.custom(
            input=f"Problem: {problem}\n\nRough scratchpad calculations: {scratchpad['response']}",
            instruction=prompt_custom.FINAL_SOLVE_PROMPT,
        )
        return solution["response"]
