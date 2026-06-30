from pathlib import Path
from typing import Any, Tuple
import json
import numpy as np
from pathlib import Path

from src.Optimiser import Optimiser
from evoagentx.optimizers import MiproOptimizer
from evoagentx.models import LiteLLMConfig, LiteLLM
from evoagentx.benchmark import GSM8K
from evoagentx.core.callbacks import suppress_logger_info
from evoagentx.utils.mipro_utils.register_utils import MiproRegistry
from evoagentx.optimizers.engine.registry import OptimizableField

class GSM8KSplitsMipro(GSM8K):
    """Split GSM8K data into train/test for MIPRO optimization."""

    def __init__(self, seed: int = 42):
        self.split_seed = seed
        super().__init__()

    def _load_data(self):
        super()._load_data()
        np.random.seed(self.split_seed)
        permutation = np.random.permutation(len(self._test_data))
        full_test = self._test_data
        self._train_data = [full_test[idx] for idx in permutation[:100]]
        self._dev_data   = [full_test[idx] for idx in permutation[100:200]]   # populate DEV
        self._test_data  = [full_test[idx] for idx in permutation[200:400]]

    def get_input_keys(self):
        return ["problem"]

    def evaluate(self, prediction: Any, label: Any) -> dict:
        return super().evaluate(prediction, label)


class MathSolverProgram:
    """Simple math solver program whose prompt MIPRO will optimize.

    MIPRO requires the program to have:
    - __call__(problem) -> (prediction, execution_data)
    - save(path) / load(path) for serialization
    """

    def __init__(self, model: LiteLLM):
        self.model = model
        self.prompt = (
            "Solve the math problem step by step. "
            "Show your reasoning, then give the final numerical answer.\n\n"
            "Problem: {problem}"
        )

    def save(self, path: str):
        params = {"prompt": self.prompt}
        with open(path, "w") as f:
            json.dump(params, f)

    def load(self, path: str):
        with open(path, "r") as f:
            params = json.load(f)
        self.prompt = params["prompt"]

    def __call__(self, problem: str) -> Tuple[str, dict]:
        prompt = self.prompt.format(problem=problem)
        response = self.model.generate(prompt=prompt)
        solution = response.content
        return solution, {"problem": problem, "solution": solution}


class MiproOptimiser(Optimiser):

    def __init__(self, seed: int, rounds: int, output_dir: Path,
                 executor_config: LiteLLMConfig, optimiser_config: LiteLLMConfig):
        super().__init__(seed, rounds, output_dir, executor_config, optimiser_config)

    def run(self):
        print("Running MIPRO Optimiser...")

        executor_llm = LiteLLM(config=self.executor_config)
        optimiser_llm = LiteLLM(config=self.optimiser_config)

        # Build the program
        program = MathSolverProgram(model=executor_llm)

        # Register the prompt parameter for optimization
        registry = MiproRegistry()
        field = OptimizableField(
            name="math_solver_prompt",
            getter=lambda: program.prompt,
            setter=lambda value: setattr(program, "prompt", value),
        )
        registry.register_field(field)

        # Load benchmark
        benchmark = GSM8KSplitsMipro(seed=self.seed)

        # Create optimizer
        optimizer = MiproOptimizer(
            registry=registry,
            program=program,
            optimizer_llm=optimiser_llm,
            max_bootstrapped_demos=4,
            max_labeled_demos=4,
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