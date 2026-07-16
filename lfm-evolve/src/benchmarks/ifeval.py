import json
import os
from typing import Any, Callable

import numpy as np
from evoagentx.benchmark.benchmark import Benchmark
from evoagentx.core.logging import logger

# lm_eval's port of the official IFEval checkers (needs langdetect +
# immutabledict; nltk downloads punkt_tab on first import).
from lm_eval.tasks.ifeval.utils import (
    InputExample,
    test_instruction_following_loose,
    test_instruction_following_strict,
)


class IFEval(Benchmark):
    """IFEval (google/IFEval): 541 prompts with verifiable instructions,
    scored by rule-based checkers (no gold answers). Splits are a seeded
    disjoint permutation of the single HF split. Every example dict gets a
    "problem" key aliasing the prompt.

    evaluate() returns only the primary metric (prompt-level strict accuracy)
    because EvoAgentX's MIPRO/TextGrad selection averages multi-key metric
    dicts. evaluate_full() returns all four official metrics.
    """

    MAIN_METRIC = "prompt_strict_acc"

    def __init__(self, path: str = None, mode: str = "all", n_train: int = 100,
                 n_dev: int = 141, n_test: int = 300, seed: int = 42, **kwargs):
        self.n_train = n_train
        self.n_dev = n_dev
        self.n_test = n_test
        self.seed = seed
        path = os.path.expanduser(path or "~/.evoagentx/data/ifeval")
        super().__init__(name=type(self).__name__, path=path, mode=mode, **kwargs)

    # -- data ---------------------------------------------------------------
    def _read_data(self) -> list:
        file_path = os.path.join(self.path, "ifeval.jsonl")
        if not os.path.exists(file_path):
            from src.common import hf_load_dataset
            logger.info("Downloading google/IFEval from HuggingFace ...")
            ds = hf_load_dataset("google/IFEval")["train"]
            os.makedirs(self.path, exist_ok=True)
            with open(file_path, "w") as f:
                for row in ds:
                    f.write(json.dumps(dict(row)) + "\n")
            logger.info(f"Cached IFEval to {file_path}")
        with open(file_path) as f:
            data = [json.loads(line) for line in f if line.strip()]
        for ex in data:
            ex["problem"] = ex["prompt"]
        return data

    def _load_data(self):
        data = self._read_data()
        rng = np.random.default_rng(self.seed)
        order = rng.permutation(len(data))
        shuffled = [data[i] for i in order]
        a, b = self.n_train, self.n_train + self.n_dev
        self._train_data = shuffled[:a]
        self._dev_data = shuffled[a:b]
        self._test_data = shuffled[b:b + self.n_test]

    # -- Benchmark interface ------------------------------------------------
    def _get_id(self, example: Any) -> Any:
        return example["key"]

    def _get_label(self, example: Any) -> Any:
        return {
            "key": example["key"],
            "prompt": example["prompt"],
            "instruction_id_list": example["instruction_id_list"],
            "kwargs": example["kwargs"],
        }

    def _check(self, prediction: Any, label: dict):
        inp = InputExample(
            key=label["key"],
            instruction_id_list=label["instruction_id_list"],
            prompt=label["prompt"],
            kwargs=label["kwargs"],
        )
        response = "" if prediction is None else str(prediction)
        out_strict = test_instruction_following_strict(inp, response)
        out_loose = test_instruction_following_loose(inp, response)
        return out_strict, out_loose

    def evaluate(self, prediction: Any, label: Any) -> dict:
        out_strict, _ = self._check(prediction, label)
        return {"prompt_strict_acc": float(out_strict.follow_all_instructions)}

    def evaluate_full(self, prediction: Any, label: Any) -> dict:
        out_strict, out_loose = self._check(prediction, label)
        return {
            "prompt_strict_acc": float(out_strict.follow_all_instructions),
            "inst_strict_acc": float(np.mean(out_strict.follow_instruction_list)),
            "prompt_loose_acc": float(out_loose.follow_all_instructions),
            "inst_loose_acc": float(np.mean(out_loose.follow_instruction_list)),
        }

    async def async_evaluate(self, graph: Callable, example: Any) -> float:
        output = await graph(example["problem"])
        return self.evaluate(output, self._get_label(example))["prompt_strict_acc"]

    def get_input_keys(self):
        return ["problem"]
