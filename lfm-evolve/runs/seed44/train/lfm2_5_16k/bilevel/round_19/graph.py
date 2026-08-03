import evoagentx.workflow.operators as operator
import runs.seed44.train.lfm2_5_16k.bilevel.round_19.prompt as prompt_custom
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
        import asyncio
        
        # Step 1: Generate 3 independent solutions concurrently
        tasks = [
            self.custom(input=problem, instruction=prompt_custom.SOLVE_MATH_PROMPT),
            self.custom(input=problem, instruction=prompt_custom.SOLVE_MATH_PROMPT),
            self.custom(input=problem, instruction=prompt_custom.SOLVE_MATH_PROMPT),
        ]
        results = await asyncio.gather(*tasks)
        
        sol1 = results[0]["response"]
        sol2 = results[1]["response"]
        sol3 = results[2]["response"]
        
        # Step 2: Consensus voting - pick the majority answer
        consensus = await self.custom(
            input=f"Problem: {problem}\n\nSolution A:\n{sol1}\n\nSolution B:\n{sol2}\n\nSolution C:\n{sol3}",
            instruction=prompt_custom.CONSENSUS_MATH_PROMPT,
        )
        return consensus["response"]
