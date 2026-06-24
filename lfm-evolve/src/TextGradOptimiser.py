from pathlib import Path
from src.Optimiser import Optimiser
from evoagentx.optimizers import TextGradOptimizer
from evoagentx.models import LiteLLMConfig, LiteLLM
from evoagentx.benchmark import GSM8K   # was: MATH
from evoagentx.benchmark import MATH
from evoagentx.workflow import SequentialWorkFlowGraph
from evoagentx.agents import AgentManager
from evoagentx.evaluators import Evaluator
from evoagentx.prompts import StringTemplate
import numpy as np

MATH_GRAPH = {
    "goal": "Answer the math question. The answer should be a number.",
    "tasks": [
        {
            "name": "answer_generate",
            "description": "Answer generation for math problems.",
            "inputs": [
                {"name": "problem", "type": "str", "required": True,
                 "description": "The math problem to solve."}
            ],
            "outputs": [
                {"name": "answer", "type": "str", "required": True,
                 "description": "The generated answer."}
            ],
            "prompt_template": StringTemplate(
                instruction="Solve the math problem step by step. "
                "Show your reasoning, then give the final numerical answer."
            ),
            "parse_mode": "str",
        }
    ],
}


def collate_func(example: dict) -> dict:
    return {"problem": example["question"]}


class GSM8KSplits(GSM8K):                # was: (MATH)
    def __init__(self, seed: int = 42):
        self.split_seed = seed
        super().__init__()

    def _load_data(self):
        super()._load_data()
        np.random.seed(self.split_seed)
        permutation = np.random.permutation(len(self._test_data))
        full_test = self._test_data
        self._train_data = [full_test[idx] for idx in permutation[:10]]
        self._dev_data   = [full_test[idx] for idx in permutation[10:60]]
        self._test_data  = [full_test[idx] for idx in permutation[60:160]]


class TextGradOptimiser(Optimiser):
    def __init__(self, seed: int, rounds: int, output_dir: Path,
                 executor_config: LiteLLMConfig, optimiser_config: LiteLLMConfig, num_workers: int = 1,
                 batch_size: int = 3):
        super().__init__(seed, rounds, output_dir, executor_config, optimiser_config)
        self.num_workers = num_workers
        self.batch_size = batch_size

    def run(self):
        print("Running TextGrad Optimiser...")

        executor_llm = LiteLLM(config=self.executor_config)
        optimiser_llm = LiteLLM(config=self.optimiser_config)

        workflow_graph = SequentialWorkFlowGraph.from_dict(MATH_GRAPH)

        agent_manager = AgentManager()
        agent_manager.add_agents_from_workflow(workflow_graph, executor_llm.config)

        evaluator = Evaluator(
            llm=executor_llm,
            agent_manager=agent_manager,
            collate_func=collate_func,
            num_workers=self.num_workers,
            verbose=True,
        )

        benchmark = GSM8KSplits(seed=self.seed)

        optimizer = TextGradOptimizer(
            graph=workflow_graph,
            optimize_mode="system_prompt",
            executor_llm=executor_llm,
            optimizer_llm=optimiser_llm,
            batch_size=self.batch_size,
            max_steps=self.rounds,
            evaluator=evaluator,
            eval_every_n_steps=1,
            eval_rounds=1,
            save_path=str(self.output_dir),
            save_interval=1,
            rollback=True,
            constraints=[],
        )
        results_before = optimizer.evaluate(dataset=benchmark, eval_mode="test")
        print(f"Before optimization: {results_before}")

        optimizer.optimize(dataset=benchmark)

        results_after = optimizer.evaluate(dataset=benchmark, eval_mode="test")
        print(f"After optimization: {results_after}")
