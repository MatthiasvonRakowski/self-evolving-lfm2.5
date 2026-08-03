import evoagentx.workflow.operators as operator
import runs.seed45.train.lfm2_5_16k.aflow.round_10.prompt as prompt_custom
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

        def extract_answer(text: str) -> str:
            match = re.search(r'####\s*([\d,.\-]+)', text)
            if match:
                return match.group(1).replace(',', '').strip()
            return ""

        # Step 1a: First solution
        sol1 = await self.custom(
            input=problem,
            instruction=prompt_custom.SOLVE_MATH_PROMPT,
        )
        answer1 = sol1["response"]

        # Step 1b: Second independent solution
        sol2 = await self.custom(
            input=problem,
            instruction=prompt_custom.SOLVE_MATH_PROMPT_ALT,
        )
        answer2 = sol2["response"]

        num1 = extract_answer(answer1)
        num2 = extract_answer(answer2)

        # Step 2: If both solutions agree, return the first one directly
        if num1 and num2 and num1 == num2:
            return answer1

        # Step 3: Generate a third solution for majority voting
        sol3 = await self.custom(
            input=problem,
            instruction=prompt_custom.SOLVE_MATH_PROMPT_THIRD,
        )
        answer3 = sol3["response"]
        num3 = extract_answer(answer3)

        # Majority vote among three solutions
        if num3 and num1 and num3 == num1:
            return answer1
        if num3 and num2 and num3 == num2:
            return answer2

        # Step 4: No majority found — review all three solutions
        review = await self.custom(
            input=f"Problem: {problem}\nSolution A: {answer1}\nSolution B: {answer2}\nSolution C: {answer3}",
            instruction=prompt_custom.REVIEW_MATH_PROMPT,
        )
        review_text = review["response"]

        # Step 5: If review finds issues, generate a revised solution
        if "CORRECT" not in review_text.upper():
            revised = await self.custom(
                input=f"Problem: {problem}\nSolution A: {answer1}\nSolution B: {answer2}\nSolution C: {answer3}\nReview feedback: {review_text}",
                instruction=prompt_custom.REVISE_MATH_PROMPT,
            )
            return revised["response"]

        return answer1
