from typing import Any, Callable

import numpy as np
from evoagentx.benchmark import GSM8K


class GSM8KEval(GSM8K):
    """GSM8K with the repo-wide "problem" key convention and an AFlow-style
    async_evaluate, used by evaluate.py (and the bilevel optimiser) so all
    benchmarks share one interface. Train/dev are seeded samples of the HF
    train split; test is a seeded sample of the HF test split.
    """

    MAIN_METRIC = "solve_rate"

    def __init__(self, n_train: int = 100, n_dev: int = 100, n_test: int = 300,
                 seed: int = 42, **kwargs):
        self.n_train = n_train
        self.n_dev = n_dev
        self.n_test = n_test
        self.seed = seed
        super().__init__(**kwargs)

    def _load_data(self):
        super()._load_data()
        for ex in (self._train_data or []) + (self._test_data or []):
            ex["problem"] = ex["question"]
        rng = np.random.default_rng(self.seed)
        train_order = rng.permutation(len(self._train_data))
        a, b = self.n_train, self.n_train + self.n_dev
        self._dev_data = [self._train_data[i] for i in train_order[a:b]]
        self._train_data = [self._train_data[i] for i in train_order[:a]]
        test_order = rng.permutation(len(self._test_data))
        self._test_data = [self._test_data[i] for i in test_order[:self.n_test]]

    async def async_evaluate(self, graph: Callable, example: Any) -> float:
        output = await graph(example["problem"])
        metrics = self.evaluate(output, self._get_label(example))
        return metrics["solve_rate"]

    def get_input_keys(self):
        return ["problem"]
