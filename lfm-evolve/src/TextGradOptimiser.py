from pathlib import Path
from src.Optimiser import Optimiser
from evoagentx.optimizers import TextGradOptimizer
from evoagentx.models import LiteLLMConfig, LiteLLM
from evoagentx.workflow import SequentialWorkFlowGraph
from evoagentx.agents import AgentManager
from evoagentx.evaluators import Evaluator
from evoagentx.prompts import StringTemplate
from src.benchmarks import get_benchmark, HAS_GOLD_ANSWERS

# Seed instruction per benchmark. All three benchmarks share the "problem" ->
# "answer" input/output convention (see src/benchmarks/__init__.py), so a
# single graph shape works everywhere and only the wording changes.
BENCHMARK_GRAPH_CONFIG = {
    "gsm8k": {
        "goal": "Answer the math question. The answer should be a number.",
        "instruction": "Solve the math problem step by step. Show your reasoning, "
                        "then give the final numerical answer.",
    },
    "mmlu_pro": {
        "goal": "Answer the multiple-choice question by selecting the correct option letter.",
        "instruction": "Think step by step about each option, then finish your response "
                        'with the exact sentence: "The answer is (X)" where X is the '
                        "correct option letter.",
    },
    "ifeval": {
        "goal": "Follow every instruction in the prompt precisely when producing the response.",
        "instruction": "Carefully follow every instruction in the prompt exactly, and "
                        "respond only with the requested content.",
    },
}

def build_graph_dict(benchmark_name: str) -> dict:
    cfg = BENCHMARK_GRAPH_CONFIG[benchmark_name]
    return {
        "goal": cfg["goal"],
        "tasks": [
            {
                "name": "answer_generate",
                "description": "Generate a response to the input problem.",
                "inputs": [
                    {"name": "problem", "type": "str", "required": True,
                     "description": "The formatted input problem/prompt."}
                ],
                "outputs": [
                    {"name": "answer", "type": "str", "required": True,
                     "description": "The generated response."}
                ],
                "prompt_template": StringTemplate(instruction=cfg["instruction"]),
                "parse_mode": "str",
            }
        ],
    }


def collate_func(example: dict) -> dict:
    return {"problem": example["problem"]}


class TextGradOptimiser(Optimiser):
    def __init__(self, seed: int, rounds: int, output_dir: Path,
                 executor_config: LiteLLMConfig, optimiser_config: LiteLLMConfig,
                 num_workers: int = 1, batch_size: int = 3, benchmark: str = "gsm8k"):
        super().__init__(seed, rounds, output_dir, executor_config, optimiser_config)
        self.num_workers = num_workers
        self.batch_size = batch_size
        self.benchmark_name = benchmark

    def run(self):
        print(f"Running TextGrad Optimiser on {self.benchmark_name} ...")

        executor_llm = LiteLLM(config=self.executor_config)
        optimiser_llm = LiteLLM(config=self.optimiser_config)

        workflow_graph = SequentialWorkFlowGraph.from_dict(build_graph_dict(self.benchmark_name))

        agent_manager = AgentManager()
        agent_manager.add_agents_from_workflow(workflow_graph, executor_llm.config)

        evaluator = Evaluator(
            llm=executor_llm,
            agent_manager=agent_manager,
            collate_func=collate_func,
            num_workers=self.num_workers,
            verbose=True,
        )

        benchmark = get_benchmark(self.benchmark_name, seed=self.seed if self.seed is not None else 42)
        use_answers = HAS_GOLD_ANSWERS[self.benchmark_name]

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

        optimizer.optimize(dataset=benchmark, use_answers=use_answers)

        results_after = optimizer.evaluate(dataset=benchmark, eval_mode="test")
        print(f"After optimization: {results_after}")
