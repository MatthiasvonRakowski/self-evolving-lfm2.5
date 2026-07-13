import json
import os
import re
from typing import Any, Callable, Optional

import numpy as np
from evoagentx.benchmark.benchmark import Benchmark
from evoagentx.core.logging import logger

LETTERS = "ABCDEFGHIJ"

# Official MMLU-Pro extraction pattern first, then progressively laxer fallbacks
# (small models often skip the requested sentence).
ANSWER_PATTERNS = [
    re.compile(r"answer is \(?([A-J])\)?", re.IGNORECASE),
    re.compile(r"[Aa]nswer:?\s*\(?([A-J])\)?"),
    re.compile(r"\b([A-J])\b"),
]


class MMLUPro(Benchmark):
    """MMLU-Pro (TIGER-Lab/MMLU-Pro): 10-option multiple choice across 14
    categories. Train = full HF validation split (70 examples, 5/category);
    dev/test = disjoint category-stratified seeded samples of the HF test
    split. Every example dict gets a "problem" key with the formatted
    question+options text.
    """

    MAIN_METRIC = "acc"

    def __init__(self, path: str = None, mode: str = "all", n_dev: int = 100,
                 n_test: int = 300, seed: int = 42, **kwargs):
        self.n_dev = n_dev
        self.n_test = n_test
        self.seed = seed
        path = os.path.expanduser(path or "~/.evoagentx/data/mmlu_pro")
        super().__init__(name=type(self).__name__, path=path, mode=mode, **kwargs)

    # -- data ---------------------------------------------------------------
    def _download_and_cache(self):
        from datasets import load_dataset
        logger.info("Downloading TIGER-Lab/MMLU-Pro from HuggingFace ...")
        ds = load_dataset("TIGER-Lab/MMLU-Pro")
        os.makedirs(self.path, exist_ok=True)
        for split in ("validation", "test"):
            file_path = os.path.join(self.path, f"{split}.jsonl")
            with open(file_path, "w") as f:
                for row in ds[split]:
                    f.write(json.dumps(dict(row)) + "\n")
            logger.info(f"Cached MMLU-Pro {split} split to {file_path}")

    def _read_split(self, split: str) -> list:
        file_path = os.path.join(self.path, f"{split}.jsonl")
        if not os.path.exists(file_path):
            self._download_and_cache()
        with open(file_path) as f:
            data = [json.loads(line) for line in f if line.strip()]
        for ex in data:
            ex["problem"] = self.format_question(ex)
        return data

    def _load_data(self):
        validation = self._read_split("validation")
        test = self._read_split("test")

        # Category-stratified selection: shuffle each category with a seeded
        # RNG, then take examples round-robin across categories so dev and
        # test are disjoint and cover all 14 categories evenly.
        rng = np.random.default_rng(self.seed)
        by_category = {}
        for ex in test:
            by_category.setdefault(ex["category"], []).append(ex)
        for items in by_category.values():
            rng.shuffle(items)
        interleaved = []
        for i in range(max(len(v) for v in by_category.values())):
            for cat in sorted(by_category):
                if i < len(by_category[cat]):
                    interleaved.append(by_category[cat][i])

        self._train_data = validation
        self._dev_data = interleaved[:self.n_dev]
        self._test_data = interleaved[self.n_dev:self.n_dev + self.n_test]

    # -- formatting / extraction --------------------------------------------
    @staticmethod
    def format_question(example: dict) -> str:
        options = example["options"]
        lines = [f"Question: {example['question']}", "Options:"]
        lines += [f"{LETTERS[i]}. {opt}" for i, opt in enumerate(options)]
        lines.append("")
        lines.append('Think step by step, then finish your response with: '
                     '"The answer is (X)" where X is the correct option letter.')
        return "\n".join(lines)

    @staticmethod
    def extract_answer(text: str) -> Optional[str]:
        text = str(text)
        for pattern in ANSWER_PATTERNS:
            matches = pattern.findall(text)
            if matches:
                return matches[-1].upper()
        return None

    # -- Benchmark interface ------------------------------------------------
    def _get_id(self, example: Any) -> Any:
        return example["question_id"]

    def _get_label(self, example: Any) -> Any:
        return example["answer"]  # letter "A".."J"

    def evaluate(self, prediction: Any, label: Any) -> dict:
        predicted = self.extract_answer(prediction)
        return {"acc": 1.0 if predicted == str(label).upper() else 0.0}

    async def async_evaluate(self, graph: Callable, example: Any) -> float:
        # AFlow-style evaluation: run the workflow on the formatted problem.
        output = await graph(example["problem"])
        return self.evaluate(output, self._get_label(example))["acc"]

    def get_input_keys(self):
        return ["problem"]
