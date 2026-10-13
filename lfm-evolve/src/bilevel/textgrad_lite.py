
import json
import re
from types import ModuleType
from typing import Callable, Dict, List

import numpy as np

from evoagentx.benchmark.benchmark import Benchmark
from evoagentx.core.logging import logger
from evoagentx.models import LiteLLM

from src.bilevel.inner_base import InnerBudget, InnerSplits, eval_items, is_infra_error, list_prompt_fields

def sample_batch(items: List[dict], k: int, seed, round_index: int, step: int) -> List[dict]:
    if not items:
        return []
    rng = np.random.default_rng([seed, round_index, step])
    idx = rng.permutation(len(items))[:min(k, len(items))]
    return [items[i] for i in idx]

def _parse_json_object(text: str) -> dict:
    try:
        return json.loads(text)
    except Exception:
        pass
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except Exception:
            pass
    logger.warning("TextGrad-lite: could not parse a revision JSON object; skipping this step.")
    return {}

async def _critique_and_revise(optimiser_llm: LiteLLM, current_prompts: Dict[str, str],
                                 failing: List[dict]) -> Dict[str, str]:
    lines = [
        "The following prompt constants are instruction text prepended directly "
        "in front of a task input (no template placeholders -- the constant's "
        "text and the input are simply concatenated):"
    ]
    for name, value in current_prompts.items():
        lines.append(f"\n### {name}\n{value}")
    lines.append("\nUsing these prompts, the agent failed on the following examples:")
    for i, t in enumerate(failing, 1):
        lines.append(
            f"\n--- Failing example {i} (score={t['score']}) ---\n"
            f"Input: {str(t['problem'])[:800]}\nOutput: {str(t['prediction'])[:800]}"
        )
    lines.append(
        "\n\nBriefly diagnose why these failures happened, then propose a revised "
        "version of each prompt constant likely to fix them. Respond with ONLY a "
        'JSON object mapping each constant\'s exact name to its full revised '
        'string value, e.g. {"NAME": "revised text"}.'
    )
    response = await optimiser_llm.async_generate(prompt="\n".join(lines), parse_mode="str")
    return _parse_json_object(response.content)

async def run_textgrad_lite_inner(workflow: Callable, prompt_module: ModuleType,
                                   benchmark: Benchmark, budget: InnerBudget,
                                   optimiser_llm: LiteLLM, splits: InnerSplits,
                                   round_index: int = 0) -> Dict[str, str]:
    field_names = list_prompt_fields(prompt_module)
    if not field_names:
        return {}
    metric_key = getattr(benchmark, "MAIN_METRIC", None)
    best = {name: getattr(prompt_module, name) for name in field_names}
    best_result = await eval_items(workflow, benchmark, splits.tune)

    for step in range(budget.tg_steps):
        batch = sample_batch(splits.demo, 8, budget.seed, round_index, step)
        if not batch:
            break

        transcripts = []
        crashes = 0
        for example in batch:
            try:
                prediction = await workflow(example["problem"])
                metrics = benchmark.evaluate(prediction, benchmark.get_label(example))
                score = float(metrics[metric_key]) if metric_key else float(next(iter(metrics.values())))
                transcripts.append({"problem": example["problem"], "prediction": prediction, "score": score})
            except Exception as e:
                crashes += 1
                kind = "model-server" if is_infra_error(e) else "code"
                logger.warning(f"TextGrad-lite: {kind} error on a training example: {e}")

        if crashes:
            logger.warning(
                f"TextGrad-lite: {crashes}/{len(batch)} training examples raised an error; "
                "these are not prompt faults and are excluded from the critique."
            )
        if not transcripts:
            break

        failing = [t for t in transcripts if t["score"] < 1.0]
        if not failing:
            continue

        revised = await _critique_and_revise(optimiser_llm, dict(best), failing[:5])
        candidate = dict(best)
        for name, value in revised.items():
            if name in field_names and isinstance(value, str) and value.strip():
                candidate[name] = value
        if candidate == best:
            continue

        for name, value in candidate.items():
            setattr(prompt_module, name, value)
        result = await eval_items(workflow, benchmark, splits.tune)
        if result.usable(budget) and result.score > best_result.score:
            logger.info(f"TextGrad-lite: step {step} accepted "
                        f"({best_result.score:.4f} -> {result.score:.4f})")
            best, best_result = candidate, result
        else:
            logger.info(f"TextGrad-lite: step {step} rejected ({result.describe()}; "
                        f"best {best_result.score:.4f})")
            for name, value in best.items():
                setattr(prompt_module, name, value)

    return best
