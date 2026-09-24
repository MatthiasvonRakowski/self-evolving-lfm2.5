from pathlib import Path
from typing import Tuple
import json

from src.Optimiser import Optimiser
from src.common import PromptPlaceholderError, fill_prompt_template
from evoagentx.optimizers import MiproOptimizer
from evoagentx.models import LiteLLMConfig, LiteLLM
from evoagentx.core.callbacks import suppress_logger_info
from evoagentx.utils.mipro_utils.register_utils import MiproRegistry
from evoagentx.optimizers.engine.registry import OptimizableField
from src.benchmarks import get_benchmark, HAS_GOLD_ANSWERS

SEED_PROMPT = {
    "gsm8k": (
        "Solve the math problem step by step. "
        "Show your reasoning, then give the final numerical answer.\n\n"
        "Problem: {problem}"
    ),
    "mmlu_pro": (
        "Answer the multiple-choice question. Think step by step about each "
        'option, then finish your response with the exact sentence: '
        '"The answer is (X)" where X is the correct option letter.\n\n'
        "{problem}"
    ),
    "ifeval": (
        "Follow every instruction in the prompt exactly, and respond only "
        "with the requested content.\n\n"
        "Prompt: {problem}"
    ),
}

class PromptSolverProgram:

    def __init__(self, model: LiteLLM, seed_prompt: str):
        self.model = model
        self.prompt = seed_prompt
        self.placeholder_failures = 0

    def save(self, path: str):
        with open(path, "w") as f:
            json.dump({"prompt": self.prompt}, f)

    def load(self, path: str):
        with open(path, "r") as f:
            params = json.load(f)
        self.prompt = params["prompt"]

    def __call__(self, problem: str = None, **kwargs) -> Tuple[str, dict]:
        if problem is None:
            problem = kwargs.get("problem")
        try:
            prompt = fill_prompt_template(self.prompt, problem)
        except PromptPlaceholderError as e:
            self.placeholder_failures += 1
            raise
        response = self.model.generate(prompt=prompt)
        solution = response.content
        return solution, {"problem": problem, "solution": solution}

class MiproOptimiser(Optimiser):

    def __init__(self, seed: int, rounds: int, output_dir: Path,
                 executor_config: LiteLLMConfig, optimiser_config: LiteLLMConfig,
                 benchmark: str = "gsm8k"):
        super().__init__(seed, rounds, output_dir, executor_config, optimiser_config)
        self.benchmark_name = benchmark

    def run(self):
        print(f"Running MIPRO Optimiser on {self.benchmark_name} ...")

        executor_llm = LiteLLM(config=self.executor_config)
        optimiser_llm = LiteLLM(config=self.optimiser_config)

        program = PromptSolverProgram(model=executor_llm, seed_prompt=SEED_PROMPT[self.benchmark_name])

        registry = MiproRegistry()
        field = OptimizableField(
            name="solver_prompt",
            getter=lambda: program.prompt,
            setter=lambda value: setattr(program, "prompt", value),
        )
        registry.register_field(field)

        benchmark = get_benchmark(self.benchmark_name, seed=self.seed if self.seed is not None else 42)
        has_answers = HAS_GOLD_ANSWERS[self.benchmark_name]

        optimizer = MiproOptimizer(
            registry=registry,
            program=program,
            optimizer_llm=optimiser_llm,
            max_bootstrapped_demos=4 if has_answers else 0,
            max_labeled_demos=4 if has_answers else 0,
            num_threads=1,
            eval_rounds=1,
            num_candidates=6,
            max_steps=self.rounds if self.rounds else 10,
            auto=None,
            save_path=str(self.output_dir),
        )

        print("Optimizing...")
        optimizer.optimize(dataset=benchmark)
        optimizer.restore_best_program()

        print("Evaluating after optimization...")
        with suppress_logger_info():
            results_after = optimizer.evaluate(dataset=benchmark, eval_mode="test")
        print(f"After optimization (MIPRO-internal metric, not comparable to "
              f"evaluate.py scores): {results_after}")

        if program.placeholder_failures:
            print(f"!!! {program.placeholder_failures} call(s) had no usable problem "
                  f"placeholder in the prompt -- the optimiser was scoring prompts "
                  f"that never contained the question")

        try:
            fill_prompt_template(program.prompt, "probe")
            placeholder_ok = True
        except PromptPlaceholderError as e:
            placeholder_ok = False
            print(f"!!! final MIPRO prompt is unusable: {e}")

        results_path = Path(self.output_dir) / "mipro_results.json"
        with open(results_path, "w") as f:
            json.dump({
                "mipro_internal_metric": results_after,
                "seed": self.seed,
                "benchmark": self.benchmark_name,
                "final_prompt": program.prompt,
                "placeholder_ok": placeholder_ok,
                "placeholder_failures": program.placeholder_failures,
            }, f, indent=2, default=str)

        print(f"Results saved to {results_path}")
