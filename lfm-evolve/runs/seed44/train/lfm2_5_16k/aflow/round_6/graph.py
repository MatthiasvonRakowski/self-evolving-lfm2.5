import evoagentx.workflow.operators as operator
import runs.seed44.train.lfm2_5_16k.aflow.round_6.prompt as prompt_custom
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
        solution = await self.custom(
            input=problem,
            instruction=prompt_custom.SOLVE_MATH_PROMPT,
        )
        
        verified = await self.custom(
            input=f"Problem: {problem}\n\nProposed Solution:\n{solution['response']}",
            instruction=prompt_custom.VERIFY_MATH_PROMPT,
        )
        
        # Extract final answers from both steps to check for disagreement
        sol_text = solution['response']
        ver_text = verified['response']
        
        def extract_answer(text):
            for line in reversed(text.strip().split('\n')):
                if '####' in line:
                    return line.split('####')[-1].strip()
            return None
        
        sol_ans = extract_answer(sol_text)
        ver_ans = extract_answer(ver_text)
        
        # If answers disagree or verification couldn't extract an answer, use arbiter
        if sol_ans is not None and ver_ans is not None and sol_ans != ver_ans:
            arbiter = await self.custom(
                input=f"Problem: {problem}\n\nAttempt 1:\n{sol_text}\n\nAttempt 2:\n{ver_text}",
                instruction=prompt_custom.ARBITER_MATH_PROMPT,
            )
            return arbiter['response']
        
        return verified['response']
