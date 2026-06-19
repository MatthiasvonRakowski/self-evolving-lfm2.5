from pathlib import Path
import numpy as np
from src.Optimiser import Optimiser
from evoagentx.optimizers import AFlowOptimizer
from evoagentx.models import LiteLLMConfig, LiteLLM
from evoagentx.benchmark import AFlowGSM8K


class AFlowGSM8KDev(AFlowGSM8K):
    def _load_data(self):
        super()._load_data()
        np.random.seed(42)
        pool = self._train_data or self._dev_data   # prefer the train split as the source
        n = min(400, len(pool))
        idx = np.random.permutation(len(pool))[:n]
        self._dev_data = [pool[i] for i in idx]
        # leave self._test_data alone — that's your honest final score


class AFlowOptimiser(Optimiser):
    def __init__(self, seed: int, rounds: int, output_dir: Path,
                 executor_config: LiteLLMConfig, optimiser_config: LiteLLMConfig,
                 graph_path: str):
        super().__init__(seed, rounds, output_dir, executor_config, optimiser_config)
        self.graph_path = graph_path

    def run(self):
        print("Running AFlow Optimiser...")
        executor_llm = LiteLLM(config=self.executor_config)
        optimiser_llm = LiteLLM(config=self.optimiser_config)

        gsm8k = AFlowGSM8KDev()
        print(f"dev={len(gsm8k._dev_data)}  test={len(gsm8k._test_data)}")  # expect: dev=20  test=1055

        optimizer = AFlowOptimizer(
            graph_path=self.graph_path,
            optimized_path=str(self.output_dir),
            optimizer_llm=optimiser_llm,
            executor_llm=executor_llm,
            validation_rounds=1,
            max_rounds=self.rounds,
            question_type="math",
            operators=["Custom"],
        )
        optimizer.optimize(gsm8k)
        optimizer.test(gsm8k)
