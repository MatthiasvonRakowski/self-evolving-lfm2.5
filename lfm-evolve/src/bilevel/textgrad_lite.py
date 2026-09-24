
import json
import re
from types import ModuleType
from typing import Callable, Dict, List

import numpy as np

from evoagentx.benchmark.benchmark import Benchmark
from evoagentx.core.logging import logger
from evoagentx.models import LiteLLM

from src.bilevel.inner_base import InnerBudget, eval_items, list_prompt_fields

def sample_train_batch(benchmark: Benchmark, k: int, seed, round_index: int, step: int) -> List[dict]:
    train = benchmark._train_data or benchmark._dev_data or []
    if not train:
        return []
    rng = np.random.default_rng([seed, round_index, step])
    idx = rng.permutation(len(train))[:min(k, len(train))]
    return [train[i] for i in idx]

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
                                   optimiser_llm: LiteLLM, tune_items: List[dict] = None,
                                   round_index: int = 0) -> Dict[str, str]:
    field_names = list_prompt_fields(prompt_module)
    if not field_names:
        return {}
    metric_key = getattr(benchmark, "MAIN_METRIC", None)
    accept_items = tune_items or []
    best = {name: getattr(prompt_module, name) for name in field_names}
    best_score, _ = await eval_items(workflow, benchmark, accept_items)

    for step in range(budget.tg_steps):
        batch = sample_train_batch(benchmark, 8, budget.seed, round_index, step)
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
                logger.warning(f"TextGrad-lite: workflow raised on a training example: {e}")

        if crashes:
            logger.warning(
                f"TextGrad-lite: {crashes}/{len(batch)} training examples raised an "
                "execution error; these are code faults, not prompt faults, and are "
                "excluded from the critique."
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
        score, errors = await eval_items(workflow, benchmark, accept_items)
        if errors <= budget.max_error_rate and score > best_score:
            logger.info(f"TextGrad-lite: step {step} accepted ({best_score:.4f} -> {score:.4f})")
            best, best_score = candidate, score
        else:
            logger.info(f"TextGrad-lite: step {step} rejected ({score:.4f} vs {best_score:.4f}, "
                        f"error rate {errors:.1%})")
            for name, value in best.items():
                setattr(prompt_module, name, value)

    return best
