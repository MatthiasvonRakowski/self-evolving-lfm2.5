import evoagentx.workflow.operators as operator
import output2.llama3_2_1b.aflow.round_10.prompt as prompt_custom
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
        from collections import Counter

        # Step 1: Generate three independent solutions
        sol1 = await self.custom(
            input=problem,
            instruction=prompt_custom.SOLVE_MATH_PROMPT,
        )
        sol2 = await self.custom(
            input=problem,
            instruction=prompt_custom.SOLVE_MATH_PROMPT_ALT,
        )
        sol3 = await self.custom(
            input=problem,
            instruction=prompt_custom.SOLVE_MATH_PROMPT,
        )

        answers = []
        responses = [sol1["response"], sol2["response"], sol3["response"]]

        def extract_answer(text):
            match = re.search(r'####\s*([\d,\.]+)', text)
            if match:
                return match.group(1).replace(',', '').strip()
            return None

        for r in responses:
            ans = extract_answer(r)
            if ans:
                answers.append(ans)

        # Step 2: Majority voting
        if len(answers) >= 2:
            counter = Counter(answers)
            majority_ans, count = counter.most_common(1)[0]
            if count >= 2:
                # Find response with majority answer
                for r in responses:
                    if extract_answer(r) == majority_ans:
                        return r

        # Step 3: If no majority, do a review of all three solutions
        combined = "\n\n".join([f"Solution {i+1}:\n{r}" for i, r in enumerate(responses)])
        review = await self.custom(
            input=f"Problem: {problem}\n\nThree solution attempts:\n{combined}",
            instruction=prompt_custom.REVIEW_MATH_PROMPT,
        )
        return review["response"]
