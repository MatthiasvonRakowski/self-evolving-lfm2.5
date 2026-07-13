from pathlib import Path
from typing import Tuple
import json

from src.Optimiser import Optimiser
from evoagentx.optimizers import MiproOptimizer
from evoagentx.models import LiteLLMConfig, LiteLLM
from evoagentx.core.callbacks import suppress_logger_info
from evoagentx.utils.mipro_utils.register_utils import MiproRegistry
from evoagentx.optimizers.engine.registry import OptimizableField
from src.benchmarks import get_benchmark, HAS_GOLD_ANSWERS

# Seed prompt per benchmark. All three benchmarks expose a "problem" key
# holding the fully formatted input (see src/benchmarks/__init__.py), so the
# same {problem} placeholder works everywhere.
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
    """Generic single-prompt program whose prompt MIPRO will optimize.

    MIPRO requires the program to have:
    - __call__(problem) -> (prediction, execution_data)
    - save(path) / load(path) for serialization
    """

    def __init__(self, model: LiteLLM, seed_prompt: str):
        self.model = model
        self.prompt = seed_prompt

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
        prompt = self.prompt.format(problem=problem)
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

        # Build the program
        program = PromptSolverProgram(model=executor_llm, seed_prompt=SEED_PROMPT[self.benchmark_name])

        # Register the prompt parameter for optimization
        registry = MiproRegistry()
        field = OptimizableField(
            name="solver_prompt",
            getter=lambda: program.prompt,
            setter=lambda value: setattr(program, "prompt", value),
        )
        registry.register_field(field)

        # Load benchmark
        benchmark = get_benchmark(self.benchmark_name, seed=self.seed if self.seed is not None else 42)
        has_answers = HAS_GOLD_ANSWERS[self.benchmark_name]

        # Create optimizer
        optimizer = MiproOptimizer(
            registry=registry,
            program=program,
            optimizer_llm=optimiser_llm,
            max_bootstrapped_demos=4 if has_answers else 0,
            max_labeled_demos=4 if has_answers else 0,
            num_threads=1,
            eval_rounds=1,
            num_candidates=6,
            max_steps=10,
            auto=None,
            save_path=str(self.output_dir),
        )

        # Optimize
        print("Optimizing...")
        optimizer.optimize(dataset=benchmark)
        optimizer.restore_best_program()

        # Evaluate after optimization
        print("Evaluating after optimization...")
        with suppress_logger_info():
            results_after = optimizer.evaluate(dataset=benchmark, eval_mode="test")
        print(f"After optimization: {results_after}")

        # Save results
        results_path = Path(self.output_dir) / "mipro_results.json"
        with open(results_path, "w") as f:
            json.dump({
                "after": results_after,
                "seed": self.seed,
                "optimized_prompt": program.prompt,
            }, f, indent=2, default=str)

        print(f"Results saved to {results_path}")
