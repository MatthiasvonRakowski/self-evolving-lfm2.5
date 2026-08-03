
QUESTION_TYPE = {"gsm8k": "math", "mmlu_pro": "qa", "ifeval": "qa"}

HAS_GOLD_ANSWERS = {"gsm8k": True, "mmlu_pro": True, "ifeval": False}

BENCHMARK_NAMES = ["gsm8k", "mmlu_pro", "ifeval"]

def get_benchmark(name: str, seed: int = 42, **split_kwargs):
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
