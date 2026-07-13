"""Bilevel optimizer: AFlow topology search (outer) with an inner
MIPRO+TextGrad-lite prompt-optimization loop run on every candidate
topology before it's scored (see APEX, arXiv 2606.15363, on why prompt- and
topology-level self-improvement should co-evolve rather than be optimized in
isolation).

The hook point is AFlowOptimizer._evaluate_and_save_optimization_results,
which normally writes graph.py/prompt.py for a round and evaluates it
immediately. BilevelAFlowOptimizer overrides it to run the inner loop
between those two steps, so the round's recorded score -- and therefore the
top-round sampling used to propose new topologies, and the convergence
check -- are all computed after inner optimization, not raw/seed-prompt
performance.
"""

import os
import sys
from pathlib import Path
from typing import Any

from evoagentx.core.logging import logger
from evoagentx.models import LiteLLMConfig, LiteLLM
from evoagentx.optimizers import AFlowOptimizer

from src.Optimiser import Optimiser
from src.benchmarks import get_benchmark, QUESTION_TYPE, HAS_GOLD_ANSWERS
from src.bilevel import run_inner_optimization
from src.bilevel.inner_base import InnerBudget, persist_prompt_module


class BilevelAFlowOptimizer(AFlowOptimizer):
    # Extra fields on top of AFlowOptimizer's own (it's a pydantic BaseModule,
    # so new fields just need a type annotation + default to be constructor-
    # settable like any other field).
    bilevel_inner_mode: str = "mipro+textgrad"
    bilevel_budget: Any = None
    bilevel_has_gold_answers: bool = True

    async def _evaluate_and_save_optimization_results(self, directory, response, sample, data, validation_n):
        # -- unchanged from AFlowOptimizer: write this round's files, load its graph --
        self.graph_utils.write_graph_files(directory, response)
        experience = self.experience_utils.create_experience_data(sample, response["modification"])
        self.graph = self.graph_utils.load_graph(self.round + 1, self.root_path)

        # -- NEW: inner prompt optimization, before this round gets scored --
        prompt_module_name = self.graph.__module__.rsplit(".", 1)[0] + ".prompt"
        prompt_module = sys.modules[prompt_module_name]
        workflow = self.graph(name=self.benchmark.name, llm_config=self.executor_llm.config, benchmark=self.benchmark)

        budget = self.bilevel_budget or InnerBudget()
        best_snapshot, inner_score = await run_inner_optimization(
            workflow=workflow,
            prompt_module=prompt_module,
            benchmark=self.benchmark,
            inner_mode=self.bilevel_inner_mode,
            budget=budget,
            optimiser_llm=self.optimizer_llm,
            has_gold_answers=self.bilevel_has_gold_answers,
            tmp_dir=os.path.join(directory, "_inner_mipro_tmp"),
        )
        if best_snapshot:
            persist_prompt_module(directory, best_snapshot)
        logger.info(f"[bilevel] round {self.round + 1} inner-optimized dev-subsample score: {inner_score:.4f}")

        # -- unchanged from AFlowOptimizer: score the (now inner-optimized) round --
        avg_score = await self.evaluation_utils.evaluate_graph_async(self, validation_n, data, initial=False)
        self.experience_utils.update_experience(directory, experience, avg_score)
        return avg_score


class BilevelOptimiser(Optimiser):
    def __init__(self, seed: int, rounds: int, output_dir: Path,
                 executor_config: LiteLLMConfig, optimiser_config: LiteLLMConfig,
                 graph_path: str = None, benchmark: str = "gsm8k",
                 inner: str = "mipro+textgrad", inner_budget: InnerBudget = None):
        super().__init__(seed, rounds, output_dir, executor_config, optimiser_config)
        self.benchmark_name = benchmark
        self.graph_path = graph_path or f"src/aflow_workflow/{benchmark}"
        self.inner = inner
        self.inner_budget = inner_budget or InnerBudget(seed=seed if seed is not None else 42)

    def run(self):
        print(f"Running Bilevel Optimiser on {self.benchmark_name} (inner={self.inner}) ...")
        executor_llm = LiteLLM(config=self.executor_config)
        optimiser_llm = LiteLLM(config=self.optimiser_config)

        benchmark = get_benchmark(self.benchmark_name, seed=self.seed if self.seed is not None else 42)
        print(f"train={len(benchmark._train_data)}  dev={len(benchmark._dev_data)}  test={len(benchmark._test_data)}")

        optimizer = BilevelAFlowOptimizer(
            graph_path=self.graph_path,
            optimized_path=str(self.output_dir),
            optimizer_llm=optimiser_llm,
            executor_llm=executor_llm,
            validation_rounds=1,
            max_rounds=self.rounds,
            question_type=QUESTION_TYPE[self.benchmark_name],
            operators=["Custom"],
            bilevel_inner_mode=self.inner,
            bilevel_budget=self.inner_budget,
            bilevel_has_gold_answers=HAS_GOLD_ANSWERS[self.benchmark_name],
        )
        optimizer.optimize(benchmark)
        optimizer.test(benchmark)
