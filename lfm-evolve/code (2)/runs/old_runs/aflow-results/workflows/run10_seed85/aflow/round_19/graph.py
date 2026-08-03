import evoagentx.workflow.operators as operator
import workflows.run10_seed85.aflow.round_19.prompt as prompt_custom
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
        initial = solution1["response"]

        verified = await self.custom(
            input=f"Problem: {problem}\n\nProposed Solution:\n{initial}",
            instruction=prompt_custom.VERIFY_MATH_PROMPT,
        )
        verified_answer = verified["response"]

        solution2 = await self.custom(
            input=problem,
            instruction=prompt_custom.SOLVE_MATH_ALT_PROMPT,
        )
        alt_answer = solution2["response"]

        # Extract numerical answers to highlight disagreements explicitly
        import re
        def extract_answer(text):
            matches = re.findall(r'####\s*([\d,.\-]+)', text)
            return matches[-1].replace(',', '') if matches else "unknown"

        ans_a = extract_answer(verified_answer)
        ans_b = extract_answer(alt_answer)
        agreement_note = f"\n[NOTE: Solution A gives {ans_a}, Solution B gives {ans_b}. {'They AGREE.' if ans_a == ans_b else 'They DISAGREE — extra care needed!'}]"

        final = await self.custom(
            input=f"Problem: {problem}\n\nSolution A:\n{verified_answer}\n\nSolution B:\n{alt_answer}{agreement_note}",
            instruction=prompt_custom.RECONCILE_PROMPT,
        )
        return final["response"]
