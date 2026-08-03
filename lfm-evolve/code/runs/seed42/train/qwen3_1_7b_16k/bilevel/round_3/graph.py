import evoagentx.workflow.operators as operator
import runs.seed42.train.qwen3_1_7b_16k.bilevel.round_3.prompt as prompt_custom
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
        import re
        
        solution1, solution2, solution3 = await asyncio.gather(
            self.custom(input=problem, instruction=prompt_custom.SOLVE_MATH_PROMPT),
            self.custom(input=problem, instruction=prompt_custom.SOLVE_MATH_ALT_PROMPT),
            self.custom(input=problem, instruction=prompt_custom.SOLVE_MATH_VERIFY_PROMPT),
        )
        
        resp1 = solution1["response"]
        resp2 = solution2["response"]
        resp3 = solution3["response"]
        
        def extract_answer(text):
            matches = re.findall(r'####\s*(-?[\d,]+\.?\d*)', text)
            if matches:
                return matches[-1].replace(',', '')
            return None
        
        ans1 = extract_answer(resp1)
        ans2 = extract_answer(resp2)
        ans3 = extract_answer(resp3)
        
        # Majority voting among three solutions
        answers = [ans1, ans2, ans3]
        resps = [resp1, resp2, resp3]
        
        from collections import Counter
        valid = [(a, r) for a, r in zip(answers, resps) if a is not None]
        
        if valid:
            counts = Counter(a for a, r in valid)
            majority_ans, majority_count = counts.most_common(1)[0]
            if majority_count >= 2:
                # Return the response corresponding to the majority answer
                for a, r in valid:
                    if a == majority_ans:
                        return r
        
        # No majority: tiebreaker with context from all three solutions
        tiebreak_input = (
            f"Original Problem: {problem}\n\n"
            f"Solution A (answer: {ans1}):\n{resp1}\n\n"
            f"Solution B (answer: {ans2}):\n{resp2}\n\n"
            f"Solution C (answer: {ans3}):\n{resp3}\n\n"
            f"Re-solve the problem independently from scratch."
        )
        solution_tb = await self.custom(
            input=tiebreak_input,
            instruction=prompt_custom.TIEBREAK_PROMPT,
        )
        return solution_tb["response"]
