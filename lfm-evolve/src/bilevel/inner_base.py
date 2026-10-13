
import ast
import asyncio
import copy
import os
import threading
from collections import Counter
from dataclasses import dataclass, field
from types import ModuleType
from typing import Any, Callable, Dict, List

import numpy as np

from evoagentx.benchmark.benchmark import Benchmark
from evoagentx.core.logging import logger

@dataclass
class InnerBudget:

    mipro_candidates: int = 4
    mipro_steps: int = 4
    tg_steps: int = 2
    tune_k: int = 80
    select_k: int = 100
    seed: int = 42
    max_code_error_rate: float = 0.05
    max_infra_error_rate: float = 0.20

def list_prompt_fields(prompt_module: ModuleType) -> List[str]:
    return sorted(
        name for name, value in vars(prompt_module).items()
        if isinstance(value, str)
        and not name.startswith("_")
        and name.isupper()
        and any(c.isspace() for c in value.strip())
    )

def snapshot(prompt_module: ModuleType, fields: List[str]) -> Dict[str, str]:
    return {name: getattr(prompt_module, name) for name in fields}

def apply_snapshot(prompt_module: ModuleType, snap: Dict[str, str]) -> None:
    for name, value in snap.items():
        setattr(prompt_module, name, value)

def persist_prompt_module(directory: str, snap: Dict[str, str]) -> None:
    path = os.path.join(directory, "prompt.py")
    source = ""
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            source = f.read()

    try:
        tree = ast.parse(source)
    except SyntaxError as e:
        logger.warning(f"[bilevel] {path} does not parse ({e}); rewriting it from the snapshot.")
        tree, source = ast.parse(""), ""

    lines = source.splitlines(keepends=True)
    edits = []
    for node in tree.body:
        if (isinstance(node, ast.Assign) and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name)
                and node.targets[0].id in snap and node.col_offset == 0):
            name = node.targets[0].id
            edits.append((node.lineno, node.end_lineno, f"{name} = {snap[name]!r}\n"))

    for start, end, text in sorted(edits, reverse=True):
        lines[start - 1:end] = [text]

    written = {text.split(" = ", 1)[0] for _, _, text in edits}
    missing = [name for name in snap if name not in written]
    if missing:
        if lines and not lines[-1].endswith("\n"):
            lines[-1] += "\n"
        lines += [f"{name} = {snap[name]!r}\n" for name in missing]

    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.writelines(lines)
    os.replace(tmp, path)

def _subsample(items: List[dict], k: int, rng) -> List[dict]:
    if not items:
        return []
    idx = rng.permutation(len(items))[:min(k, len(items))]
    return [items[i] for i in idx]

@dataclass
class InnerSplits:
    demo: List[dict]
    tune: List[dict]
    select: List[dict]

def inner_splits(benchmark: Benchmark, budget: InnerBudget, round_index: int = 0) -> InnerSplits:
    train = benchmark._train_data or []
    dev = benchmark._dev_data or []
    if not train or not dev:
        raise ValueError(
            f"{type(benchmark).__name__} needs both train and dev data for the inner loop "
            f"(train={len(train)}, dev={len(dev)}); the test split is never used here."
        )
    rng = np.random.default_rng([budget.seed, round_index])
    pool = _subsample(train, budget.tune_k, rng)
    half = len(pool) // 2
    demo, tune = (pool[:half], pool[half:]) if half else (pool, pool)
    select = _subsample(dev, budget.select_k, rng)
    return InnerSplits(demo=demo, tune=tune, select=select)

def capped_view(benchmark: Benchmark, train_items: List[dict], dev_items: List[dict]) -> Benchmark:
    view = copy.copy(benchmark)
    view._train_data = list(train_items)
    view._dev_data = list(dev_items)
    view._test_data = view._dev_data
    return view

_INFRA_ERROR_NAMES = {
    "Timeout", "APITimeoutError", "APIConnectionError", "ServiceUnavailableError",
    "RateLimitError", "InternalServerError", "BadGatewayError", "APIError",
}
_INFRA_ERROR_MODULES = {"litellm", "openai", "anthropic", "httpx", "httpcore", "aiohttp"}
_INFRA_ERROR_MARKERS = ("litellm.Timeout", "APIConnectionError", "Connection refused", "timed out")

def is_infra_error(exc: BaseException) -> bool:
    if isinstance(exc, (asyncio.TimeoutError, TimeoutError, ConnectionError)):
        return True
    for cls in type(exc).__mro__:
        if cls.__name__ in _INFRA_ERROR_NAMES:
            return True
        if cls.__module__.split(".")[0] in _INFRA_ERROR_MODULES:
            return True
    text = str(exc)
    return any(marker in text for marker in _INFRA_ERROR_MARKERS)

@dataclass
class EvalResult:
    score: float
    n: int
    n_code_errors: int = 0
    n_infra_errors: int = 0
    error_kinds: Counter = field(default_factory=Counter)

    @property
    def code_error_rate(self) -> float:
        return self.n_code_errors / self.n if self.n else 0.0

    @property
    def infra_error_rate(self) -> float:
        return self.n_infra_errors / self.n if self.n else 0.0

    def usable(self, budget: InnerBudget) -> bool:
        return (self.code_error_rate <= budget.max_code_error_rate
                and self.infra_error_rate <= budget.max_infra_error_rate)

    def describe(self) -> str:
        kinds = "; ".join(f"{k} (x{v})" for k, v in self.error_kinds.most_common(3)) or "none"
        return (f"score {self.score:.4f} on n={self.n - self.n_infra_errors}/{self.n}, "
                f"code errors {self.code_error_rate:.0%}, infra errors "
                f"{self.infra_error_rate:.0%} [{kinds}]")

async def eval_items(workflow: Callable, benchmark: Benchmark, items: List[dict],
                      max_concurrent: int = 6) -> EvalResult:
    if not items:
        return EvalResult(score=0.0, n=0)
    semaphore = asyncio.Semaphore(max_concurrent)
    scores: List[float] = [0.0] * len(items)
    outcome: List[str] = ["ok"] * len(items)
    kinds: Counter = Counter()

    async def run_one(i, example):
        async with semaphore:
            try:
                scores[i] = float(await benchmark.async_evaluate(workflow, example))
            except Exception as e:
                outcome[i] = "infra" if is_infra_error(e) else "code"
                kinds[f"{type(e).__name__}: {e}"[:160]] += 1

    await asyncio.gather(*(run_one(i, ex) for i, ex in enumerate(items)))
    scored = [s for s, o in zip(scores, outcome) if o != "infra"]
    return EvalResult(
        score=float(np.mean(scored)) if scored else 0.0,
        n=len(items),
        n_code_errors=outcome.count("code"),
        n_infra_errors=outcome.count("infra"),
        error_kinds=kinds,
    )

class _BackgroundLoop:

    _loop: Any = None
    _lock = threading.Lock()

    @classmethod
    def get(cls):
        with cls._lock:
            if cls._loop is None:
                loop = asyncio.new_event_loop()
                threading.Thread(target=loop.run_forever, daemon=True).start()
                cls._loop = loop
            return cls._loop

def run_async(coro) -> Any:
    future = asyncio.run_coroutine_threadsafe(coro, _BackgroundLoop.get())
    return future.result()
