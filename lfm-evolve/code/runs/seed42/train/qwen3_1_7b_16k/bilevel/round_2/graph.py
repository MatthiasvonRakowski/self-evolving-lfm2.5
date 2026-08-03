import evoagentx.workflow.operators as operator
import runs.seed42.train.qwen3_1_7b_16k.bilevel.round_2.prompt as prompt_custom
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
        solution1 = await self.custom(
            input=problem,
            instruction=prompt_custom.SOLVE_MATH_PROMPT,
        )
        solution2 = await self.custom(
            input=problem,
            instruction=prompt_custom.SOLVE_MATH_ALT_PROMPT,
        )
        
        # Extract final answers from both solutions
        resp1 = solution1["response"]
        resp2 = solution2["response"]
        
        def extract_answer(text):
            import re
            matches = re.findall(r'####\s*(-?[\d,]+\.?\d*)', text)
            if matches:
                return matches[-1].replace(',', '')
            return None
        
        ans1 = extract_answer(resp1)
        ans2 = extract_answer(resp2)
        
        # If both agree, high confidence - return first response
        if ans1 and ans2 and ans1 == ans2:
            return resp1
        
        # If they disagree, do a tiebreaker with full context from both solutions
        tiebreak_input = (
            f"Original Problem: {problem}\n\n"
            f"Solution A (answer: {ans1}):\n{resp1}\n\n"
            f"Solution B (answer: {ans2}):\n{resp2}\n\n"
            f"Re-solve the problem independently from scratch."
        )
        solution3 = await self.custom(
            input=tiebreak_input,
            instruction=prompt_custom.TIEBREAK_PROMPT,
        )
        return solution3["response"]
