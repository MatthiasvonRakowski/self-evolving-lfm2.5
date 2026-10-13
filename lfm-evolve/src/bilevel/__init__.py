
from types import ModuleType
from typing import Callable, Tuple

from evoagentx.benchmark.benchmark import Benchmark
from evoagentx.core.logging import logger
from evoagentx.models import LiteLLM

from src.bilevel.inner_base import (
    InnerBudget,
    apply_snapshot,
    eval_items,
    inner_splits,
    list_prompt_fields,
    snapshot,
)
from src.bilevel.mipro_inner import run_mipro_inner
from src.bilevel.textgrad_lite import run_textgrad_lite_inner

INNER_MODES = ["mipro", "textgrad", "mipro+textgrad", "none"]

class BrokenWorkflowError(RuntimeError):
    pass

async def run_inner_optimization(workflow: Callable, prompt_module: ModuleType,
                                  benchmark: Benchmark, inner_mode: str, budget: InnerBudget,
                                  optimiser_llm: LiteLLM, has_gold_answers: bool,
                                  tmp_dir: str, round_index: int = 0) -> Tuple[dict, float]:
    field_names = list_prompt_fields(prompt_module)
    baseline_snapshot = snapshot(prompt_module, field_names)
    splits = inner_splits(benchmark, budget, round_index)

    base = await eval_items(workflow, benchmark, splits.select)
    if base.code_error_rate > budget.max_code_error_rate:
        raise BrokenWorkflowError(
            f"workflow raised code errors on {base.code_error_rate:.0%} of the selection split "
            f"(threshold {budget.max_code_error_rate:.0%}): {base.describe()}"
        )
    if base.infra_error_rate > budget.max_infra_error_rate:
        logger.warning(f"[bilevel] too many model-server failures to compare prompt candidates "
                       f"this round; keeping the generated prompts ({base.describe()})")
        return baseline_snapshot, base.score

    if inner_mode == "none" or not field_names:
        return baseline_snapshot, base.score

    best_snapshot, best_score = baseline_snapshot, base.score
    logger.info(f"[bilevel] inner baseline: {base.describe()} "
                f"(demo n={len(splits.demo)}, tune n={len(splits.tune)}, select n={len(splits.select)})")

    async def consider(name: str, candidate: dict) -> None:
        nonlocal best_snapshot, best_score
        apply_snapshot(prompt_module, candidate)
        result = await eval_items(workflow, benchmark, splits.select)
        logger.info(f"[bilevel] inner {name} candidate: {result.describe()}")
        if not result.usable(budget):
            logger.warning(f"[bilevel] rejecting {name} candidate: {result.describe()}")
        elif result.score > best_score:
            best_snapshot, best_score = candidate, result.score
        apply_snapshot(prompt_module, best_snapshot)

    if "mipro" in inner_mode:
        candidate = run_mipro_inner(
            workflow, prompt_module, benchmark, budget, optimiser_llm,
            has_gold_answers=has_gold_answers, tmp_dir=tmp_dir,
            splits=splits, round_index=round_index,
        )
        await consider("MIPRO", candidate)

    if "textgrad" in inner_mode:
        candidate = await run_textgrad_lite_inner(
            workflow, prompt_module, benchmark, budget, optimiser_llm,
            splits=splits, round_index=round_index,
        )
        await consider("TextGrad-lite", candidate)

    apply_snapshot(prompt_module, best_snapshot)
    return best_snapshot, best_score
