"""Bilevel optimizer: inner prompt-optimization loop invoked between AFlow
writing a round's files and scoring it (see src/BilevelOptimiser.py).

Composes the inner steps with an explicit keep-or-rollback check on a dev
subsample after each step, rather than trusting either inner optimizer's own
internal "best" tracking -- notably, MiproOptimizer.restore_best_program()
is a no-op in the installed EvoAgentX version, so relying on its post-search
state directly would silently accept whatever the last-tried candidate was.
"""

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
    """Runs the configured inner optimiser(s) against `prompt_module` in
    place, keeping only steps that beat the running best on a dev subsample.
    Returns (best_snapshot, best_dev_score); `prompt_module`'s attributes are
    left set to `best_snapshot` on return."""
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
            apply_snapshot(prompt_module, best_snapshot)  # roll back

    if "textgrad" in inner_mode:
        apply_snapshot(prompt_module, best_snapshot)  # refine from the current best
        candidate = await run_textgrad_lite_inner(workflow, prompt_module, benchmark, budget, optimiser_llm)
        apply_snapshot(prompt_module, candidate)
        score = await eval_dev_subsample(workflow, benchmark, budget.dev_eval_k, budget.seed)
        logger.info(f"[bilevel] inner TextGrad-lite candidate dev score: {score:.4f}")
        if score > best_score:
            best_snapshot, best_score = candidate, score
        else:
            apply_snapshot(prompt_module, best_snapshot)  # roll back

    apply_snapshot(prompt_module, best_snapshot)
    return best_snapshot, best_score
