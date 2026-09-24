
import asyncio
import copy
import threading
from dataclasses import dataclass
from types import ModuleType
from typing import Any, Callable, Dict, List, Tuple

import numpy as np

from evoagentx.benchmark.benchmark import Benchmark

@dataclass
class InnerBudget:

    mipro_candidates: int = 4
    mipro_steps: int = 4
    tg_steps: int = 2
    dev_eval_k: int = 100
    seed: int = 42
    select_frac: float = 0.5
    max_error_rate: float = 0.05

def list_prompt_fields(prompt_module: ModuleType) -> List[str]:
    return sorted(
        name for name, value in vars(prompt_module).items()
        if isinstance(value, str) and not name.startswith("_")
    )

def snapshot(prompt_module: ModuleType, fields: List[str]) -> Dict[str, str]:
    return {name: getattr(prompt_module, name) for name in fields}

def apply_snapshot(prompt_module: ModuleType, snap: Dict[str, str]) -> None:
    for name, value in snap.items():
        setattr(prompt_module, name, value)

def persist_prompt_module(directory: str, snap: Dict[str, str]) -> None:
    import ast
    import os

    path = os.path.join(directory, "prompt.py")
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as f:
                existing = f.read()
            tree = ast.parse(existing)
            non_string_nodes = [
                node for node in tree.body
                if not (
                    isinstance(node, ast.Assign)
                    and isinstance(getattr(node, "value", None), ast.Constant)
                    and isinstance(node.value.value, str)
                )
            ]
            if non_string_nodes:
                from evoagentx.core.logging import logger
                logger.warning(
                    f"[bilevel] {path} holds more than string constants "
                    f"({len(non_string_nodes)} other top-level statement(s)); "
                    "leaving it untouched rather than overwriting it."
                )
                return
        except SyntaxError:
            pass

    lines = [f"{name} = {value!r}\n" for name, value in snap.items()]
    with open(path, "w", encoding="utf-8") as f:
        f.writelines(lines)

def _subsample(items: List[dict], k: int, rng) -> List[dict]:
    if not items:
        return []
    idx = rng.permutation(len(items))[:min(k, len(items))]
    return [items[i] for i in idx]

def dev_split(benchmark: Benchmark, budget: "InnerBudget", round_index: int = 0):
    rng = np.random.default_rng([budget.seed, round_index])
    dev = benchmark._dev_data or benchmark._test_data or []
    drawn = _subsample(dev, budget.dev_eval_k, rng)
    if len(drawn) < 2:
        return drawn, drawn
    n_select = max(1, int(round(len(drawn) * budget.select_frac)))
    return drawn[n_select:], drawn[:n_select]

def capped_view(benchmark: Benchmark, items: List[dict], budget: "InnerBudget",
                 round_index: int = 0) -> Benchmark:
    view = copy.copy(benchmark)
    rng = np.random.default_rng([budget.seed, round_index, 1])
    train = benchmark._train_data or []
    if train:
        view._train_data = _subsample(train, budget.dev_eval_k, rng)
    view._dev_data = list(items)
    view._test_data = view._dev_data
    return view

async def eval_items(workflow: Callable, benchmark: Benchmark, items: List[dict],
                      max_concurrent: int = 6) -> Tuple[float, float]:
    if not items:
        return 0.0, 0.0
    semaphore = asyncio.Semaphore(max_concurrent)
    scores: List[float] = [0.0] * len(items)
    errors: List[int] = [0] * len(items)

    async def run_one(i, example):
        async with semaphore:
            try:
                scores[i] = float(await benchmark.async_evaluate(workflow, example))
            except Exception as e:
                errors[i] = 1
                _record_error(e)

    await asyncio.gather(*(run_one(i, ex) for i, ex in enumerate(items)))
    return float(np.mean(scores)), sum(errors) / len(items)

_seen_errors: Dict[str, int] = {}

def _record_error(exc: Exception) -> None:
    key = f"{type(exc).__name__}: {exc}"[:200]
    _seen_errors[key] = _seen_errors.get(key, 0) + 1
    if _seen_errors[key] == 1:
        from evoagentx.core.logging import logger
        logger.warning(f"[bilevel] workflow execution error (first occurrence): {key}")

def format_error_summary() -> str:
    if not _seen_errors:
        return "none"
    return "; ".join(f"{k} (x{v})" for k, v in sorted(_seen_errors.items(), key=lambda kv: -kv[1])[:3])

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
