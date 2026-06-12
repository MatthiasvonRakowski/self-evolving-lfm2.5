from pathlib import Path

from src.Optimiser import Optimiser

from evoagentx.optimizers import AFlowOptimizer
from evoagentx.models import LiteLLMConfig, LiteLLM 
from evoagentx.benchmark import AFlowGSM8K 

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
        
        gsm8k = AFlowGSM8K()

        optimizer = AFlowOptimizer(
            graph_path=self.graph_path,
            optimized_path=str(self.output_dir),
            optimizer_llm=optimiser_llm,
            executor_llm=executor_llm,
            validation_rounds=1,
            max_rounds=self.rounds,
            question_type="math",
            operators=["Custom", "ScEnsemble", "Programmer"],
        )

        optimizer.optimize(gsm8k)
        optimizer.test(gsm8k)
