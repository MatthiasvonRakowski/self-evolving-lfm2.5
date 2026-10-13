
import importlib
import json
import os
import sys
from typing import List

import numpy as np

from evoagentx.core.logging import logger
from evoagentx.optimizers import AFlowOptimizer
from evoagentx.utils.aflow_utils.graph_utils import GraphUtils

TEST_RESULTS_FILENAME = "test_results.json"


class FreshImportGraphUtils(GraphUtils):
    """GraphUtils whose load_graph imports what is on disk, not what Python has cached.

    EvoAgentX loads `<root>.round_N.graph` with __import__, which hands back the module already in
    sys.modules. AFlow retries a round up to three times when the optimiser's reply does not give a
    usable graph (write the files, import, fail, ask again): the files are rewritten, but the import
    returns the first attempt's module, so every retry dies with the first attempt's error even when
    the new reply is fine. Seen in runs_smoke_v2 (bilevel round 2, 2026-10-13): attempt 2 had a
    correct <graph> block and still failed with "module ... has no attribute 'Workflow'", and the
    round was lost. Dropping the round's modules before importing makes the retry see the new files.
    """

    def load_graph(self, round_number: int, workflows_path: str):
        package = workflows_path.replace("\\", ".").replace("/", ".") + f".round_{round_number}"
        for name in [n for n in sys.modules if n == package or n.startswith(package + ".")]:
            del sys.modules[name]
        importlib.invalidate_caches()
        return super().load_graph(round_number, workflows_path)


class TestIsolatedAFlowOptimizer(AFlowOptimizer):

    def init_module(self, **kwargs):
        super().init_module(**kwargs)
        self.graph_utils = FreshImportGraphUtils(self.root_path)

    async def _run_test(self, test_rounds: List[int]):
        logger.info("Running test evaluation (isolated from results.json) ...")

        graph_path = self.root_path
        test_path = os.path.join(graph_path, TEST_RESULTS_FILENAME)
        data = []
        if os.path.exists(test_path):
            try:
                with open(test_path) as f:
                    data = json.load(f)
            except Exception:
                data = []

        scores = []
        for round in test_rounds:
            logger.info(f"Running test for round {round}...")
            self.graph = self.graph_utils.load_graph(round, graph_path)
            score, avg_cost, total_cost = await self.evaluation_utils.evaluate_graph_test_async(self)
            scores.append(score)
            data.append(self.data_utils.create_result_data(round, score, avg_cost, total_cost))
            logger.info(f"Test round {round} score: {score}, avg_cost: {avg_cost}, total_cost: {total_cost}")

            tmp = test_path + ".tmp"
            with open(tmp, "w") as f:
                json.dump(data, f, indent=2, default=str)
            os.replace(tmp, test_path)

        return float(np.mean(scores)) if scores else 0.0

def write_best_round(output_dir, optimizer) -> int:
    best_round = optimizer._load_best_round()
    payload = {
        "best_round": best_round,
        "selected_on": "validation",
        "validation_rounds": optimizer.validation_rounds,
    }
    path = os.path.join(str(output_dir), "best_round.json")
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(payload, f, indent=2)
    os.replace(tmp, path)
    return best_round
