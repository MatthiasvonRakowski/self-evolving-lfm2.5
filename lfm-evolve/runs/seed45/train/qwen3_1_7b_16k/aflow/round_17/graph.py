import evoagentx.workflow.operators as operator
import runs.seed45.train.qwen3_1_7b_16k.aflow.round_17.prompt as prompt_custom
from evoagentx.models.model_configs import LLMConfig
from evoagentx.benchmark.benchmark import Benchmark
from evoagentx.models.model_utils import create_llm_instance

import re

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

        # Extract final answers using regex to check agreement
        def extract_answer(text):
            matches = re.findall(r'####\s*([\d,.\-]+)', text)
            if matches:
                return matches[-1].replace(',', '').strip()
            return None

        ans1 = extract_answer(solution1['response'])
        ans2 = extract_answer(solution2['response'])

        # If both solutions agree, skip synthesis and go straight to verification
        if ans1 and ans2 and ans1 == ans2:
            combined = solution1['response']
        else:
            # Solutions disagree — use synthesis to resolve
            synth = await self.custom(
                input=f"Problem: {problem}\n\nSolution A:\n{solution1['response']}\n\nSolution B:\n{solution2['response']}",
                instruction=prompt_custom.SYNTHESIZE_MATH_PROMPT,
            )
            combined = synth['response']

        final = await self.custom(
            input=f"Problem: {problem}\n\nProposed solution:\n{combined}",
            instruction=prompt_custom.VERIFY_ARITHMETIC_PROMPT,
        )
        return final["response"]
