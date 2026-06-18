import evoagentx.workflow.operators as operator
import workflows.run10_seed85.aflow.round_4.prompt as prompt_custom
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

        # Extract #### answers to detect disagreement
        import re
        def extract_answer(text):
            matches = re.findall(r'####\s*([\d,.\-]+)', text)
            return matches[-1].strip().replace(',', '') if matches else None

        ans_a = extract_answer(verified_answer)
        ans_b = extract_answer(alt_answer)

        # If answers disagree, run a deep analysis step first
        if ans_a is not None and ans_b is not None and ans_a != ans_b:
            deep = await self.custom(
                input=f"Problem: {problem}\n\nSolution A (answer={ans_a}):\n{verified_answer}\n\nSolution B (answer={ans_b}):\n{alt_answer}",
                instruction=prompt_custom.DEEP_ANALYSIS_PROMPT,
            )
            reconcile_input = f"Problem: {problem}\n\nSolution A:\n{verified_answer}\n\nSolution B:\n{alt_answer}\n\nDeep Analysis:\n{deep['response']}"
        else:
            reconcile_input = f"Problem: {problem}\n\nSolution A:\n{verified_answer}\n\nSolution B:\n{alt_answer}"

        final = await self.custom(
            input=reconcile_input,
            instruction=prompt_custom.RECONCILE_PROMPT,
        )
        return final["response"]
