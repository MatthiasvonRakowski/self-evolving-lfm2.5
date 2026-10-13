from pathlib import Path
from src.Optimiser import Optimiser
from src.aflow_base import TestIsolatedAFlowOptimizer, write_best_round
from evoagentx.models import LiteLLMConfig, LiteLLM
from src.benchmarks import get_benchmark, QUESTION_TYPE

class AFlowOptimiser(Optimiser):
    def __init__(self, seed: int, rounds: int, output_dir: Path,
                 executor_config: LiteLLMConfig, optimiser_config: LiteLLMConfig,
                 graph_path: str = None, benchmark: str = "gsm8k",
                 validation_rounds: int = 3, check_convergence: bool = True,
                 internal_test: bool = True):
        super().__init__(seed, rounds, output_dir, executor_config, optimiser_config)
        self.benchmark_name = benchmark
        self.graph_path = graph_path or f"src/aflow_workflow/{benchmark}"
        self.validation_rounds = validation_rounds
        # EvoAgentX stops early once the validation score has converged; `rounds` is then a maximum.
        self.check_convergence = check_convergence
        # AFlow's own test pass scores the selected round on the test split (eval_rounds x 300 calls).
        # evaluate.py does the same on the same split, so it is optional.
        self.internal_test = internal_test

    def run(self):
        print(f"Running AFlow Optimiser on {self.benchmark_name} ...")
        executor_llm = LiteLLM(config=self.executor_config)
        optimiser_llm = LiteLLM(config=self.optimiser_config)

        benchmark = get_benchmark(self.benchmark_name, seed=self.seed if self.seed is not None else 42)
        print(f"train={len(benchmark._train_data)}  dev={len(benchmark._dev_data)}  test={len(benchmark._test_data)}")

        optimizer = TestIsolatedAFlowOptimizer(
            graph_path=self.graph_path,
            optimized_path=str(self.output_dir),
            optimizer_llm=optimiser_llm,
            executor_llm=executor_llm,
            validation_rounds=self.validation_rounds,
            max_rounds=self.rounds,
            check_convergence=self.check_convergence,
            question_type=QUESTION_TYPE[self.benchmark_name],
            operators=["Custom"],
        )
        optimizer.optimize(benchmark)

        best_round = write_best_round(self.output_dir, optimizer)
        print(f"Best round (validation only): {best_round}")

        if self.internal_test:
            optimizer.test(benchmark)
        else:
            print("Skipping AFlow's own test pass (evaluate.py scores the selected round).")
