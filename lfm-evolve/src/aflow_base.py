
import json
import os
from typing import List

import numpy as np

from evoagentx.core.logging import logger
from evoagentx.optimizers import AFlowOptimizer

TEST_RESULTS_FILENAME = "test_results.json"

class TestIsolatedAFlowOptimizer(AFlowOptimizer):

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
