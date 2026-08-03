
from types import ModuleType
from typing import Callable, Tuple

from evoagentx.benchmark.benchmark import Benchmark
from evoagentx.core.logging import logger
from evoagentx.models import LiteLLM

from src.bilevel.inner_base import (
    InnerBudget,
    apply_snapshot,
    eval_dev_subsample,
    list_prompt_fields,
    snapshot,
)
from src.bilevel.mipro_inner import run_mipro_inner
from src.bilevel.textgrad_lite import run_textgrad_lite_inner

INNER_MODES = ["mipro", "textgrad", "mipro+textgrad", "none"]

async def run_inner_optimization(workflow: Callable, prompt_module: ModuleType,
                                  benchmark: Benchmark, inner_mode: str, budget: InnerBudget,
                                  optimiser_llm: LiteLLM, has_gold_answers: bool,
                                  tmp_dir: str) -> Tuple[dict, float]:
    field_names = list_prompt_fields(prompt_module)
    baseline_snapshot = snapshot(prompt_module, field_names)

    if inner_mode == "none" or not field_names:
        score = await eval_dev_subsample(workflow, benchmark, budget.dev_eval_k, budget.seed)
        return baseline_snapshot, score

    best_snapshot = baseline_snapshot
    best_score = await eval_dev_subsample(workflow, benchmark, budget.dev_eval_k, budget.seed)
    logger.info(f"[bilevel] inner baseline dev score: {best_score:.4f}")

    if "mipro" in inner_mode:
        candidate = run_mipro_inner(
            workflow, prompt_module, benchmark, budget, optimiser_llm,
            has_gold_answers=has_gold_answers, tmp_dir=tmp_dir,
        )
        apply_snapshot(prompt_module, candidate)
        score = await eval_dev_subsample(workflow, benchmark, budget.dev_eval_k, budget.seed)
        logger.info(f"[bilevel] inner MIPRO candidate dev score: {score:.4f}")
        if score > best_score:
            best_snapshot, best_score = candidate, score
        else:
            apply_snapshot(prompt_module, best_snapshot)

    if "textgrad" in inner_mode:
        apply_snapshot(prompt_module, best_snapshot)
        candidate = await run_textgrad_lite_inner(workflow, prompt_module, benchmark, budget, optimiser_llm)
        apply_snapshot(prompt_module, candidate)
        score = await eval_dev_subsample(workflow, benchmark, budget.dev_eval_k, budget.seed)
        logger.info(f"[bilevel] inner TextGrad-lite candidate dev score: {score:.4f}")
        if score > best_score:
            best_snapshot, best_score = candidate, score
        else:
            apply_snapshot(prompt_module, best_snapshot)

    apply_snapshot(prompt_module, best_snapshot)
    return best_snapshot, best_score
