"""Shared helpers for the bilevel inner loop: prompt-constant introspection,
snapshot/restore, dev-subsample scoring, and a sync<->async bridge.

Convention: a round's prompt.py is a flat module of top-level string
constants (e.g. SOLVE_MATH_PROMPT). The AFlow-generated graph.py reads them
off the `prompt_custom` module *at call time*, so mutating those attributes
in place (via setattr) immediately changes what the next call to the
workflow sees -- no disk round-trip needed per candidate.
"""

import asyncio
import copy
import threading
from dataclasses import dataclass
from types import ModuleType
from typing import Any, Callable, Dict, List

import numpy as np

from evoagentx.benchmark.benchmark import Benchmark


@dataclass
class InnerBudget:
    """Budgets for the inner prompt-optimization loop, kept small by default
    since every outer AFlow round triggers a full inner search."""

    mipro_candidates: int = 4
    mipro_steps: int = 4
    tg_steps: int = 2
    dev_eval_k: int = 40
    seed: int = 42


def list_prompt_fields(prompt_module: ModuleType) -> List[str]:
    """Names of all top-level string constants in a round's prompt module."""
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
    """Rewrite round_N/prompt.py on disk so the inner-optimized prompt
    constants survive re-imports (later rounds' experience sampling,
    evaluate.py's artifact loader, etc). Uses repr() so multi-line /
    quote-containing text round-trips safely."""
    import os
    lines = [f"{name} = {value!r}\n" for name, value in snap.items()]
    with open(os.path.join(directory, "prompt.py"), "w", encoding="utf-8") as f:
        f.writelines(lines)


def capped_view(benchmark: Benchmark, k: int, seed: int) -> Benchmark:
    """A shallow-copied view of `benchmark` whose train/dev data are capped
    to `k` seeded-random examples each, so inner-loop scoring stays cheap.
    Shares the original benchmark's class/methods (evaluate, get_input_keys,
    async_evaluate, ...) via copy.copy."""
    view = copy.copy(benchmark)
    rng = np.random.default_rng(seed)
    train = benchmark._train_data or []
    dev = benchmark._dev_data or benchmark._test_data or []
    if train:
        idx = rng.permutation(len(train))[:min(k, len(train))]
        view._train_data = [train[i] for i in idx]
    if dev:
        idx = rng.permutation(len(dev))[:min(k, len(dev))]
        view._dev_data = [dev[i] for i in idx]
    view._test_data = view._dev_data
    return view


async def eval_dev_subsample(workflow: Callable, benchmark: Benchmark, k: int,
                              seed: int, max_concurrent: int = 6) -> float:
    """Mean benchmark score of `workflow` over a capped, seeded dev sample."""
    view = capped_view(benchmark, k, seed)
    data = view._dev_data
    if not data:
        return 0.0
    semaphore = asyncio.Semaphore(max_concurrent)

    async def run_one(example):
        async with semaphore:
            try:
                return await benchmark.async_evaluate(workflow, example)
            except Exception:
                return 0.0

    scores = await asyncio.gather(*(run_one(ex) for ex in data))
    return float(np.mean(scores)) if scores else 0.0


def run_async(coro) -> Any:
    """Run an async coroutine to completion from sync code, regardless of
    whether the calling thread already has a running event loop (MIPRO's
    internal search calls the wrapped program synchronously, but we're
    invoked from inside AFlowOptimizer's own event loop)."""
    box: Dict[str, Any] = {}

    def runner():
        try:
            box["result"] = asyncio.run(coro)
        except Exception as e:
            box["error"] = e

    thread = threading.Thread(target=runner)
    thread.start()
    thread.join()
    if "error" in box:
        raise box["error"]
    return box["result"]
