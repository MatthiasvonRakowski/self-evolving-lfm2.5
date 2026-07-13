from pathlib import Path
from src.Optimiser import Optimiser
from evoagentx.optimizers import AFlowOptimizer
from evoagentx.models import LiteLLMConfig, LiteLLM
from src.benchmarks import get_benchmark, QUESTION_TYPE


class AFlowOptimiser(Optimiser):
    def __init__(self, seed: int, rounds: int, output_dir: Path,
                 executor_config: LiteLLMConfig, optimiser_config: LiteLLMConfig,
                 graph_path: str = None, benchmark: str = "gsm8k"):
        super().__init__(seed, rounds, output_dir, executor_config, optimiser_config)
        self.benchmark_name = benchmark
        # Each benchmark ships its own seed workflow under src/aflow_workflow/<benchmark>/.
        self.graph_path = graph_path or f"src/aflow_workflow/{benchmark}"

    def run(self):
        print(f"Running AFlow Optimiser on {self.benchmark_name} ...")
        executor_llm = LiteLLM(config=self.executor_config)
        optimiser_llm = LiteLLM(config=self.optimiser_config)

        benchmark = get_benchmark(self.benchmark_name, seed=self.seed if self.seed is not None else 42)
        print(f"train={len(benchmark._train_data)}  dev={len(benchmark._dev_data)}  test={len(benchmark._test_data)}")

        optimizer = AFlowOptimizer(
            graph_path=self.graph_path,
            optimized_path=str(self.output_dir),
            optimizer_llm=optimiser_llm,
            executor_llm=executor_llm,
            validation_rounds=1,
            max_rounds=self.rounds,
            question_type=QUESTION_TYPE[self.benchmark_name],
            operators=["Custom"],
        )
        optimizer.optimize(benchmark)
        optimizer.test(benchmark)
