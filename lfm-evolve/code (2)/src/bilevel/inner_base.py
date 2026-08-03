
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

    mipro_candidates: int = 4
    mipro_steps: int = 4
    tg_steps: int = 2
    dev_eval_k: int = 40
    seed: int = 42

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
    import os
    lines = [f"{name} = {value!r}\n" for name, value in snap.items()]
    with open(os.path.join(directory, "prompt.py"), "w", encoding="utf-8") as f:
        f.writelines(lines)

def capped_view(benchmark: Benchmark, k: int, seed: int) -> Benchmark:
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
