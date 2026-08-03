import evoagentx.workflow.operators as operator
import runs.seed42.train.llama3_2_1b.aflow.round_8.prompt as prompt_custom
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
        # Generate two independent solutions in parallel
        solution1, solution2 = await asyncio.gather(
            self.custom(input=problem, instruction=prompt_custom.SOLVE_MATH_PROMPT),
            self.custom(input=problem, instruction=prompt_custom.SOLVE_MATH_PROMPT),
        )
        
        ans1 = solution1["response"]
        ans2 = solution2["response"]
        
        # If both solutions agree, return directly; otherwise use selector
        import re
        def extract_final(text):
            match = re.search(r'####\s*(\S+)', text)
            return match.group(1).strip() if match else None
        
        num1 = extract_final(ans1)
        num2 = extract_final(ans2)
        
        if num1 is not None and num1 == num2:
            return ans1
        
        # Solutions differ - use a selector to pick the better one
        combined = f"Solution 1:\n{ans1}\n\nSolution 2:\n{ans2}"
        selected = await self.custom(
            input=combined,
            instruction=prompt_custom.SELECT_BEST_PROMPT,
        )
        return selected["response"]
