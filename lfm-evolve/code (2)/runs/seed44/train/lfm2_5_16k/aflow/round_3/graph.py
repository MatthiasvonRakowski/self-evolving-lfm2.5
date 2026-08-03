import evoagentx.workflow.operators as operator
import runs.seed44.train.lfm2_5_16k.aflow.round_3.prompt as prompt_custom
from evoagentx.models.model_configs import LLMConfig
from evoagentx.benchmark.benchmark import Benchmark
from evoagentx.models.model_utils import create_llm_instance

class Workflow:
    def __init__(self, name: str, llm_config: LLMConfig, benchmark: Benchmark | None = None):
        self.name = name
        self.llm = create_llm_instance(llm_config)
        self.benchmark = benchmark
        self.custom = operator.Custom(self.llm)

    def _extract_answer(self, text: str) -> str:
        """Extract the answer after '#### '"""
        for line in reversed(text.strip().split('\n')):
            if '####' in line:
                return line.split('####')[-1].strip()
        return ""

    async def __call__(self, problem: str, **kwargs) -> str:
        solution = await self.custom(
            input=problem,
            instruction=prompt_custom.SOLVE_MATH_PROMPT,
        )
        
        verified = await self.custom(
            input=f"Problem: {problem}\n\nProposed Solution:\n{solution['response']}",
            instruction=prompt_custom.VERIFY_MATH_PROMPT,
        )
        
        ans_initial = self._extract_answer(solution['response'])
        ans_verified = self._extract_answer(verified['response'])
        
        if ans_initial and ans_verified and ans_initial != ans_verified:
            arbitrated = await self.custom(
                input=f"Problem: {problem}\n\nSolution A:\n{solution['response']}\n\nSolution B:\n{verified['response']}",
                instruction=prompt_custom.ARBITRATE_MATH_PROMPT,
            )
            return arbitrated['response']
        
        return verified['response']
