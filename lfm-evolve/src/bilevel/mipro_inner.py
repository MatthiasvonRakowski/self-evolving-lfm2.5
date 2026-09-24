
import os
from types import ModuleType
from typing import Callable, Dict, Tuple

from evoagentx.benchmark.benchmark import Benchmark
from evoagentx.core.callbacks import suppress_logger_info
from evoagentx.core.logging import logger
from evoagentx.models import LiteLLM
from evoagentx.optimizers import MiproOptimizer
from evoagentx.optimizers.engine.registry import OptimizableField
from evoagentx.utils.mipro_utils.register_utils import MiproRegistry

from src.bilevel.inner_base import InnerBudget, capped_view, list_prompt_fields, run_async, snapshot

class InnerMiproError(RuntimeError):
    pass

class WorkflowPromptProgram:

    def __init__(self, workflow: Callable, prompt_module: ModuleType, field_names: list):
        self.workflow = workflow
        self.prompt_module = prompt_module
        self.field_names = field_names

    def save(self, path: str):
        import json
        with open(path, "w") as f:
            json.dump(snapshot(self.prompt_module, self.field_names), f)

    def load(self, path: str):
        import json
        with open(path) as f:
            params = json.load(f)
        for name, value in params.items():
            setattr(self.prompt_module, name, value)

    def __call__(self, problem: str = None, **kwargs) -> Tuple[str, dict]:
        if problem is None:
            problem = kwargs.get("problem")
        output = run_async(self.workflow(problem))
        return output, {"problem": problem, "output": output}

def run_mipro_inner(workflow: Callable, prompt_module: ModuleType, benchmark: Benchmark,
                     budget: InnerBudget, optimiser_llm: LiteLLM, has_gold_answers: bool,
                     tmp_dir: str, tune_items: list = None,
                     round_index: int = 0) -> Dict[str, str]:
    field_names = list_prompt_fields(prompt_module)
    if not field_names:
        return {}

    program = WorkflowPromptProgram(workflow, prompt_module, field_names)
    registry = MiproRegistry()
    for name in field_names:
        registry.register_field(OptimizableField(
            name=name,
            getter=lambda n=name: getattr(prompt_module, n),
            setter=lambda value, n=name: setattr(prompt_module, n, value),
        ))

    inner_benchmark = capped_view(benchmark, tune_items or [], budget, round_index)
    os.makedirs(tmp_dir, exist_ok=True)

    try:
        optimizer = MiproOptimizer(
            registry=registry,
            program=program,
            optimizer_llm=optimiser_llm,
            max_bootstrapped_demos=4 if has_gold_answers else 0,
            max_labeled_demos=4 if has_gold_answers else 0,
            num_threads=1,
            eval_rounds=1,
            num_candidates=budget.mipro_candidates,
            max_steps=budget.mipro_steps,
            auto=None,
            save_path=tmp_dir,
            requires_permission_to_run=False,
        )
        with suppress_logger_info():
            optimizer.optimize(dataset=inner_benchmark)
    except Exception as e:
        logger.warning(
            f"Inner MIPRO search failed, keeping current prompt state: "
            f"{type(e).__name__}: {e}",
            exc_info=True,
        )
        _MIPRO_FAILURES.append(f"round {round_index}: {type(e).__name__}: {e}")

    return snapshot(prompt_module, field_names)

_MIPRO_FAILURES: list = []

def mipro_failure_count() -> int:
    return len(_MIPRO_FAILURES)

def mipro_failures() -> list:
    return list(_MIPRO_FAILURES)
