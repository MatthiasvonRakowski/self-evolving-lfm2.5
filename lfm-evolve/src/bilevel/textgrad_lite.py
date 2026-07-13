"""Inner TextGrad-lite step: a small purpose-built refinement loop for the
bilevel optimizer.

EvoAgentX's real TextGradOptimizer is hard-coupled to SequentialWorkFlowGraph
/ CustomizeAgent and cannot run against an arbitrary AFlow-generated Workflow
class, so this reimplements the spirit of it directly: sample a batch of
training examples, run the workflow, have the optimiser LLM critique the
failing transcripts and propose revised prompt constants, apply them, and
let the caller decide whether to keep or roll back based on a dev-subsample
check.
"""

import json
import re
from types import ModuleType
from typing import Callable, Dict, List

import numpy as np

from evoagentx.benchmark.benchmark import Benchmark
from evoagentx.core.logging import logger
from evoagentx.models import LiteLLM

from src.bilevel.inner_base import InnerBudget, list_prompt_fields


def sample_train_batch(benchmark: Benchmark, k: int, seed: int) -> List[dict]:
    train = benchmark._train_data or benchmark._dev_data or []
    if not train:
        return []
    rng = np.random.default_rng(seed)
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
                                   optimiser_llm: LiteLLM) -> Dict[str, str]:
    """Runs the inner TextGrad-lite loop in place on `prompt_module`'s
    attributes and returns the resulting {field_name: value} snapshot."""
    field_names = list_prompt_fields(prompt_module)
    if not field_names:
        return {}
    metric_key = getattr(benchmark, "MAIN_METRIC", None)

    for step in range(budget.tg_steps):
        batch = sample_train_batch(benchmark, k=8, seed=budget.seed + step)
        if not batch:
            break

        transcripts = []
        for example in batch:
            try:
                prediction = await workflow(example["problem"])
                metrics = benchmark.evaluate(prediction, benchmark.get_label(example))
                score = float(metrics[metric_key]) if metric_key else float(next(iter(metrics.values())))
            except Exception as e:
                prediction, score = f"<error: {e}>", 0.0
            transcripts.append({"problem": example["problem"], "prediction": prediction, "score": score})

        failing = [t for t in transcripts if t["score"] < 1.0]
        if not failing:
            continue  # batch already solved by the current prompts

        current = {name: getattr(prompt_module, name) for name in field_names}
        revised = await _critique_and_revise(optimiser_llm, current, failing[:5])
        for name, value in revised.items():
            if name in field_names and isinstance(value, str) and value.strip():
                setattr(prompt_module, name, value)

    return {name: getattr(prompt_module, name) for name in field_names}
