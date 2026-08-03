import evoagentx.workflow.operators as operator
import runs.seed42.train.lfm2_5_16k.aflow.round_6.prompt as prompt_custom
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
        # Generate three independent solutions
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

        # Extract answers prefixed with "#### "
        import re
        def extract_answer(text):
            matches = re.findall(r'####\s*([\d,.\-]+)', text)
            if matches:
                return matches[-1].strip().replace(',', '')
            return None

        answers = [
            extract_answer(sol1['response']),
            extract_answer(sol2['response']),
            extract_answer(sol3['response']),
        ]

        # Majority voting
        from collections import Counter
        valid_answers = [a for a in answers if a is not None]
        if valid_answers:
            most_common = Counter(valid_answers).most_common(1)[0][0]
            # Find the solution that matches the majority answer
            for sol in [sol1, sol2, sol3]:
                if extract_answer(sol['response']) == most_common:
                    best_solution = sol['response']
                    break
            else:
                best_solution = sol1['response']
        else:
            best_solution = sol1['response']

        # Final verification pass with the best solution
        verified = await self.custom(
            input=problem + f"\n\nBest candidate solution:\n{best_solution}",
            instruction=prompt_custom.VERIFY_MATH_PROMPT,
        )
        return verified["response"]
