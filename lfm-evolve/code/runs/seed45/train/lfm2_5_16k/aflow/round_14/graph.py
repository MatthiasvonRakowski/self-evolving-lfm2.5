import evoagentx.workflow.operators as operator
import runs.seed45.train.lfm2_5_16k.aflow.round_14.prompt as prompt_custom
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

        # Step 3: Review both solutions and pick the better one
        review = await self.custom(
            input=f"Problem: {problem}\nSolution A: {answer1}\nSolution B: {answer2}",
            instruction=prompt_custom.REVIEW_MATH_PROMPT,
        )
        review_text = review["response"]

        # Step 4: If review finds issues, generate a revised solution
        if "CORRECT" not in review_text.upper():
            revised = await self.custom(
                input=f"Problem: {problem}\nSolution A: {answer1}\nSolution B: {answer2}\nReview feedback: {review_text}",
                instruction=prompt_custom.REVISE_MATH_PROMPT,
            )
            return revised["response"]

        # Return whichever solution review preferred
        if "PREFER B" in review_text.upper():
            return answer2
        return answer1
