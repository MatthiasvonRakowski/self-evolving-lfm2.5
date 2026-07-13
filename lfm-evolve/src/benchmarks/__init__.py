"""Benchmark registry for this repo's optimisers and evaluate.py.

Convention: every example dict carries a "problem" key holding the fully
formatted input text, so a single collate func / MIPRO input key / seed-graph
signature works across all benchmarks.
"""

# AFlow's optimizer prompt is parameterised by question type.
QUESTION_TYPE = {"gsm8k": "math", "mmlu_pro": "qa", "ifeval": "qa"}

# IFEval has no gold answers, so anything that needs labelled examples
# (MIPRO's bootstrapped few-shot demos, TextGrad's use_answers loss) must be
# disabled for it.
HAS_GOLD_ANSWERS = {"gsm8k": True, "mmlu_pro": True, "ifeval": False}

BENCHMARK_NAMES = ["gsm8k", "mmlu_pro", "ifeval"]


def get_benchmark(name: str, seed: int = 42, **split_kwargs):
    """Instantiate a benchmark by name. Imports lazily: ifeval pulls in
    lm_eval's checkers (nltk download on first use) and gsm8k/mmlu_pro may
    download data."""
    if name == "gsm8k":
        from src.benchmarks.gsm8k_eval import GSM8KEval
        return GSM8KEval(seed=seed, **split_kwargs)
    if name == "mmlu_pro":
        from src.benchmarks.mmlu_pro import MMLUPro
        return MMLUPro(seed=seed, **split_kwargs)
    if name == "ifeval":
        from src.benchmarks.ifeval import IFEval
        return IFEval(seed=seed, **split_kwargs)
    raise ValueError(f"Unknown benchmark: {name}. Available: {BENCHMARK_NAMES}")
