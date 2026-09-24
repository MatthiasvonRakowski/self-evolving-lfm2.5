
from types import ModuleType
from typing import Callable, Tuple

from evoagentx.benchmark.benchmark import Benchmark
from evoagentx.core.logging import logger
from evoagentx.models import LiteLLM

from src.bilevel.inner_base import (
    InnerBudget,
    apply_snapshot,
    dev_split,
    eval_items,
    format_error_summary,
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
    tune_items, select_items = dev_split(benchmark, budget, round_index)

    base_score, base_errors = await eval_items(workflow, benchmark, select_items)
    if base_errors > budget.max_error_rate:
        raise BrokenWorkflowError(
            f"workflow failed to execute on {base_errors:.0%} of the selection split "
            f"(threshold {budget.max_error_rate:.0%}): {format_error_summary()}"
        )

    if inner_mode == "none" or not field_names:
        return baseline_snapshot, base_score

    best_snapshot, best_score = baseline_snapshot, base_score
    logger.info(f"[bilevel] inner baseline dev score: {best_score:.4f} "
                f"(select n={len(select_items)}, tune n={len(tune_items)})")

    async def consider(name: str, candidate: dict) -> None:
        nonlocal best_snapshot, best_score
        apply_snapshot(prompt_module, candidate)
        score, errors = await eval_items(workflow, benchmark, select_items)
        logger.info(f"[bilevel] inner {name} candidate dev score: {score:.4f} "
                    f"(error rate {errors:.1%})")
        if errors > budget.max_error_rate:
            logger.warning(f"[bilevel] rejecting {name} candidate: error rate {errors:.1%}")
        elif score > best_score:
            best_snapshot, best_score = candidate, score
        apply_snapshot(prompt_module, best_snapshot)

    if "mipro" in inner_mode:
        candidate = run_mipro_inner(
            workflow, prompt_module, benchmark, budget, optimiser_llm,
            has_gold_answers=has_gold_answers, tmp_dir=tmp_dir,
            tune_items=tune_items, round_index=round_index,
        )
        await consider("MIPRO", candidate)

    if "textgrad" in inner_mode:
        candidate = await run_textgrad_lite_inner(
            workflow, prompt_module, benchmark, budget, optimiser_llm,
            tune_items=tune_items, round_index=round_index,
        )
        await consider("TextGrad-lite", candidate)

    apply_snapshot(prompt_module, best_snapshot)
    return best_snapshot, best_score
