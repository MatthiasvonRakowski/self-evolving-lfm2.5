import evoagentx.workflow.operators as operator
import runs.seed45.train.qwen3_1_7b_16k.aflow.round_18.prompt as prompt_custom
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
        solution1 = await self.custom(
            input=problem,
            instruction=prompt_custom.SOLVE_MATH_PROMPT,
        )
        solution2 = await self.custom(
            input=problem,
            instruction=prompt_custom.SOLVE_MATH_ALT_PROMPT,
        )
        solution3 = await self.custom(
            input=problem,
            instruction=prompt_custom.SOLVE_MATH_STEP_PROMPT,
        )

        def extract_answer(text):
            matches = re.findall(r'####\s*([^\n]+)', text)
            return matches[-1].strip() if matches else None

        ans1 = extract_answer(solution1['response'])
        ans2 = extract_answer(solution2['response'])
        ans3 = extract_answer(solution3['response'])

        majority_solution = None
        if ans1 and ans2 and ans1 == ans2:
            majority_solution = solution1['response']
        elif ans1 and ans3 and ans1 == ans3:
            majority_solution = solution1['response']
        elif ans2 and ans3 and ans2 == ans3:
            majority_solution = solution2['response']

        if majority_solution:
            synthesis_input = f"Problem: {problem}\n\nProposed solution:\n{majority_solution}"
            synthesis_text = majority_solution
        else:
            synthesized = await self.custom(
                input=f"Problem: {problem}\n\nSolution A:\n{solution1['response']}\n\nSolution B:\n{solution2['response']}\n\nSolution C:\n{solution3['response']}",
                instruction=prompt_custom.SYNTHESIZE_MATH_PROMPT,
            )
            synthesis_text = synthesized['response']

        final = await self.custom(
            input=f"Problem: {problem}\n\nProposed solution:\n{synthesis_text}",
            instruction=prompt_custom.VERIFY_ARITHMETIC_PROMPT,
        )
        return final["response"]
