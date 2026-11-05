"""Offline checks of the harness: the third-party patches in src/common.py, the logging setup, the
scorers and the evaluation error gate. No model server is needed:  python -m pytest -q tests
"""
import asyncio
import io
import sys
import types

import pytest
from loguru import logger

import src.common as common  # applies the patches at import

# ---------------------------------------------------------------------------------------------
# The MIPRO crash. EvoAgentX's MiproLMWrapper is a dspy.LM whose `.model` is an LLM object, not a
# provider/model string. DSPy's JSONAdapter -- the adapter ChatAdapter retries with when a reply has
# no [[ ## field ## ]] markers -- calls lm.model.split("/"), which raised
#   AttributeError: 'LiteLLM' object has no attribute 'split'
# and killed the MIPRO arm (runs_smoke, 2026-10-05). src/common.py routes that case to plain JSON
# formatting/parsing instead.

import dspy
from dspy.adapters.chat_adapter import ChatAdapter
from dspy.adapters.json_adapter import JSONAdapter

QA = dspy.Signature("question -> answer")

class _WrappedLLM:
    """Stands in for the EvoAgentX LiteLLM object MiproLMWrapper keeps in `.model`."""

class FakeLM:
    model = _WrappedLLM()

    def __init__(self, *replies):
        self.replies, self.calls = list(replies), []

    def __call__(self, messages=None, **kwargs):
        self.calls.append(kwargs)
        return [self.replies.pop(0)]

def test_unpatched_json_adapter_crashes_on_a_wrapped_lm():
    with pytest.raises(AttributeError, match="split"):
        common._orig_json_adapter_call(JSONAdapter(), FakeLM('{"answer": "42"}'), {}, QA, [], {"question": "6*7?"})

def test_patched_json_adapter_parses_a_json_reply():
    lm = FakeLM('{"answer": "42"}')
    assert JSONAdapter()(lm, {}, QA, [], {"question": "6*7?"}) == [{"answer": "42"}]
    assert "response_format" not in lm.calls[0]

def test_chat_adapter_retry_recovers_a_json_block_reply():
    # The sequence that killed MIPRO: the local model answers in a ```json block, ChatAdapter finds
    # no [[ ## answer ## ]] marker and retries through JSONAdapter.
    lm = FakeLM('```json\n{"answer": "42"}\n```', '```json\n{"answer": "42"}\n```')
    assert ChatAdapter()(lm, {}, QA, [], {"question": "6*7?"}) == [{"answer": "42"}]
    assert len(lm.calls) == 2

# ---------------------------------------------------------------------------------------------
# Logging.

@pytest.fixture
def restore_logger():
    yield
    common.bind_console_logger(sys.__stdout__)

def test_tee_captures_prints_and_loguru_and_survives_rebinding(tmp_path, capsys, restore_logger):
    log = tmp_path / "method.log"
    with common.tee_to_file(str(log)):
        print("printed-inside")
        logger.info("logged-inside")
        # What evoagentx's suppress_logger_info() does on exit: rebind loguru to the current
        # sys.stdout object -- our tee, whose file is about to be closed.
        logger.remove()
        logger.add(sys.stdout, level="INFO")
        sys.stdout.write("\rprogress 1/2\rprogress 2/2\n")
    logger.info("logged-after")  # must neither raise nor print a "Logging error"

    text = log.read_text()
    assert "printed-inside" in text and "logged-inside" in text
    assert "logged-after" not in text
    assert "\nprogress 1/2\nprogress 2/2\n" in text  # tqdm redraws become lines in the file
    out, err = capsys.readouterr()
    assert "Logging error" not in out + err
    assert "logged-after" in out

def test_cost_lines_are_demoted_to_debug(restore_logger):
    sink = io.StringIO()
    logger.remove()
    logger.add(sink, level="INFO")
    # loguru's record["name"] is the module name and record["function"] the code name, so emit the
    # line from a stand-in for evoagentx.models.model_utils.update_cost.
    module = types.ModuleType("evoagentx.models._fake_cost")
    exec("from loguru import logger\n"
         "def update_cost():\n    logger.info('Total cost: $0.000 | Total tokens: 1')\n"
         "def other():\n    logger.info('kept')\n", module.__dict__)
    module.update_cost()
    module.other()
    assert "Total cost" not in sink.getvalue()
    assert "kept" in sink.getvalue()

# ---------------------------------------------------------------------------------------------
# Harness pieces.

from evaluate import ERROR_PREFIX, run_predictions, summarise_records
from src.benchmarks.mmlu_pro import MMLUPro
from src.bilevel.inner_base import persist_prompt_module

class FakeBenchmark:
    name = "fake"
    MAIN_METRIC = "acc"

    def get_test_data(self):
        return [{"id": 1, "problem": "a", "answer": "A"}, {"id": 2, "problem": "b", "answer": "B"}]

    def get_id(self, example):
        return example["id"]

    def get_label(self, example):
        return example["answer"]

    def evaluate(self, prediction, label):
        return {"acc": 1.0 if prediction == label else 0.0}

def test_run_predictions_turns_exceptions_into_error_records():
    async def predict(problem):
        if problem == "b":
            raise RuntimeError("kaboom")
        return "A"

    records = asyncio.run(run_predictions(predict, FakeBenchmark(), concurrency=2))
    assert records[0] == {"id": 1, "prediction": "A", "metrics": {"acc": 1.0}, "execution_error": False}
    assert records[1]["execution_error"] is True
    assert records[1]["prediction"].startswith(ERROR_PREFIX) and "kaboom" in records[1]["prediction"]

def test_summarise_records_counts_errors_and_parse_failures():
    records = [
        {"id": 1, "prediction": "ok", "metrics": {"acc": 1.0, "parse_failed": 0.0}, "execution_error": False},
        {"id": 2, "prediction": f"{ERROR_PREFIX} boom>", "metrics": {"acc": 0.0, "parse_failed": 1.0},
         "execution_error": True},
        None,
    ]
    assert summarise_records(records, "acc") == {
        "mean_score": 0.5, "n_errors": 1, "error_rate": 0.5, "parse_failures": 1}

def test_executor_config_bounds_runaway_calls():
    cfg = common.executor_config("some-model")
    assert cfg.model == "ollama_chat/some-model"
    assert cfg.timeout == common.EXECUTOR_TIMEOUT_S
    assert cfg.max_tokens == common.EXECUTOR_MAX_TOKENS

def test_fill_prompt_template_accepts_both_placeholders_and_rejects_none():
    assert common.fill_prompt_template("Q: {problem}", "x") == "Q: x"
    assert common.fill_prompt_template("Q: {{problem}}", "x") == "Q: x"
    with pytest.raises(common.PromptPlaceholderError):
        common.fill_prompt_template("no placeholder", "x")

def test_mmlu_pro_extraction_does_not_guess():
    assert MMLUPro.extract_answer("... so The answer is (C).") == "C"
    assert MMLUPro.extract_answer("Answer: B.") == "B"
    assert MMLUPro.extract_answer("A student buys 3 pens. I am not sure.") is None

def test_persist_prompt_module_keeps_the_rest_of_the_file(tmp_path):
    (tmp_path / "prompt.py").write_text(
        'import math  # helper the generator added\n'
        'A_PROMPT = "old text here"\n'
        'B_PROMPT = "keep me please"\n')
    persist_prompt_module(str(tmp_path), {"A_PROMPT": "new text here"})
    text = (tmp_path / "prompt.py").read_text()
    assert "import math  # helper the generator added" in text
    assert "A_PROMPT = 'new text here'" in text
    assert 'B_PROMPT = "keep me please"' in text

def test_vendored_ifeval_checker_scores_instructions():
    from src.benchmarks.ifeval_lib.utils import InputExample, test_instruction_following_strict
    inp = InputExample(key=1, instruction_id_list=["change_case:english_lowercase"], prompt="say hi", kwargs=[{}])
    assert test_instruction_following_strict(inp, "hello there").follow_all_instructions
    assert not test_instruction_following_strict(inp, "Hello There").follow_all_instructions

# ---------------------------------------------------------------------------------------------
# AFlow round retries. EvoAgentX rewrites round_N/graph.py and imports it again on each retry, but
# __import__ returns the module cached by the failed first attempt, so the retry can never succeed
# (runs_smoke_v2 bilevel round 2, 2026-10-13). src/aflow_base.py drops the cached modules first.

def test_fresh_import_graph_utils_reloads_a_rewritten_round(tmp_path, monkeypatch):
    from evoagentx.utils.aflow_utils.graph_utils import GraphUtils
    from src.aflow_base import FreshImportGraphUtils

    root = tmp_path / "wf_retry_pkg"
    rnd = root / "round_1"
    rnd.mkdir(parents=True)
    (root / "__init__.py").write_text("")
    (rnd / "__init__.py").write_text("")
    (rnd / "graph.py").write_text("# the optimiser's reply had no <graph> block\n")
    monkeypatch.syspath_prepend(str(tmp_path))
    try:
        with pytest.raises(AttributeError):
            GraphUtils(str(root)).load_graph(1, "wf_retry_pkg")
        (rnd / "graph.py").write_text("class Workflow:\n    pass\n")      # the retry's good reply
        with pytest.raises(AttributeError):                                # stock EvoAgentX: still the cached module
            GraphUtils(str(root)).load_graph(1, "wf_retry_pkg")
        assert FreshImportGraphUtils(str(root)).load_graph(1, "wf_retry_pkg").__name__ == "Workflow"
    finally:
        for name in [n for n in sys.modules if n.startswith("wf_retry_pkg")]:
            del sys.modules[name]

# ---------------------------------------------------------------------------------------------
# Usage accounting. Records come from EvoAgentX's per-call cost hook, not from litellm callbacks
# (which lost every MIPRO call and the TextGrad optimiser calls, 2026-10-13); litellm's loop-bound
# async logging worker is bypassed so closing an event loop per call no longer spills tracebacks.

def test_usage_is_recorded_from_the_evoagentx_cost_hook(tmp_path, monkeypatch):
    from evoagentx.models.model_utils import Cost
    log = tmp_path / "usage.jsonl"
    monkeypatch.setenv("LLM_USAGE_LOG", str(log))

    llm = common.LiteLLM(config=common.executor_config("lfm2.5-16k"))
    llm._update_cost(Cost(input_tokens=12, output_tokens=5, input_cost=0.0, output_cost=0.0))
    common.record_usage("anthropic/claude-sonnet-4-5", 1000, 100, 0.0)   # litellm gave no price: fallback

    summary = common.summarize_usage(str(log))
    assert summary["by_model"]["lfm2.5-16k"] == {"calls": 1, "prompt_tokens": 12, "completion_tokens": 5}
    assert summary["local"]["calls"] == 1 and summary["local"]["cost_usd"] == 0.0
    assert summary["anthropic"]["calls"] == 1
    assert abs(summary["anthropic"]["cost_usd"] - (1000 * 3e-6 + 100 * 15e-6)) < 1e-12

def test_litellm_async_logging_handler_is_dropped_not_scheduled():
    from litellm.litellm_core_utils.logging_worker import GLOBAL_LOGGING_WORKER

    async def handler():
        pass

    coro = handler()
    GLOBAL_LOGGING_WORKER.ensure_initialized_and_enqueue(async_coroutine=coro)  # stock: needs a running loop
    assert coro.cr_frame is None                                                 # closed, nothing left pending
    assert GLOBAL_LOGGING_WORKER._worker_task is None

# ---------------------------------------------------------------------------------------------
# run_experiment.py --per-model runs one main.py / evaluate.py per executor model on the same seed, so
# run_summary.json and eval_summary.json have several writers. src/summary_io.py patches one cell
# under an inter-process lock instead of dumping a whole in-memory copy (which lost the other
# processes' cells).

def _summary_writer(args):
    path, label, n = args
    from src.summary_io import set_cell
    for i in range(n):
        set_cell(path, ["gsm8k", label, f"method{i}"], {"status": "success", "i": i})

def test_summary_cells_survive_concurrent_writers(tmp_path):
    import json
    import multiprocessing
    path = str(tmp_path / "run_summary.json")
    labels = [f"model{k}" for k in range(4)]
    with multiprocessing.get_context("fork").Pool(4) as pool:
        pool.map(_summary_writer, [(path, label, 25) for label in labels])
    data = json.load(open(path))
    assert sorted(data["gsm8k"]) == labels
    assert all(len(data["gsm8k"][label]) == 25 for label in labels)
    assert not [name for name in tmp_path.iterdir() if ".tmp." in name.name]


def test_logs_folder_precreated_before_textgrad_import():
    """EvoAgentX deletes ./logs at import unless it already existed; two parallel main.py processes then race
    on the rmtree (smoke run on the H100 box, 2026-11-04). src/common.py creates it up front."""
    import os
    assert os.path.isdir(common.TEXTGRAD_LOGS_DIR)
    # the import that performs the deletion must still succeed with the folder in place
    from evoagentx.optimizers import TextGradOptimizer  # noqa: F401
    assert os.path.isdir(common.TEXTGRAD_LOGS_DIR)


def test_replicas_spread_seeds_over_copies():
    """--replicas: seed i of a model with R copies is served by copy i % R (base model = copy 0); other
    models are untouched; a bare N applies to every model; unknown names are rejected."""
    import run_experiment as rx
    replicas = rx.parse_replicas(["lfm2.5-16k=3"], ["lfm2.5-16k", "qwen3-1.7b-16k"])
    assert replicas == {"lfm2.5-16k": 3}
    jobs = rx.plan_jobs([42, 43, 44, 45], ["lfm2.5-16k", "qwen3-1.7b-16k"], True, replicas)
    assert [j[:3] for j in jobs][:4] == [(s, ["lfm2.5-16k"], "lfm2_5_16k") for s in (42, 43, 44, 45)]
    assert [j[3] for j in jobs if j[1] == ["lfm2.5-16k"]] == [
        {}, {"lfm2.5-16k": "lfm2.5-16k-r1"}, {"lfm2.5-16k": "lfm2.5-16k-r2"}, {}]
    assert all(j[3] == {} for j in jobs if j[1] == ["qwen3-1.7b-16k"])
    # without --per-model the seed's job carries every model, copies assigned per model
    joint = rx.plan_jobs([42, 43], ["lfm2.5-16k", "qwen3-1.7b-16k"], False, replicas)
    assert joint == [(42, ["lfm2.5-16k", "qwen3-1.7b-16k"], None, {}),
                     (43, ["lfm2.5-16k", "qwen3-1.7b-16k"], None, {"lfm2.5-16k": "lfm2.5-16k-r1"})]
    assert rx.parse_replicas(["2"], ["a", "b"]) == {"a": 2, "b": 2}
    assert rx.parse_replicas(["1"], ["a"]) == {}
    with pytest.raises(SystemExit):
        rx.parse_replicas(["zzz=2"], ["a"])


def test_served_copy_changes_only_the_ollama_name(monkeypatch):
    """LFM_EXECUTOR_SERVE (set per job by the driver) redirects the executor calls to a copy; labels,
    directories and summaries keep the base model name."""
    monkeypatch.setenv("LFM_EXECUTOR_SERVE", "lfm2.5-16k=lfm2.5-16k-r2")
    assert common.served_model_id("lfm2.5-16k") == "ollama_chat/lfm2.5-16k-r2"
    assert common.served_model_id("ollama_chat/lfm2.5-16k") == "ollama_chat/lfm2.5-16k-r2"
    assert common.executor_config("lfm2.5-16k").model == "ollama_chat/lfm2.5-16k-r2"
    assert common.served_model_id("qwen3-1.7b-16k") == "ollama_chat/qwen3-1.7b-16k"
    assert common.model_label("lfm2.5-16k") == "lfm2_5_16k"
    monkeypatch.delenv("LFM_EXECUTOR_SERVE")
    assert common.executor_config("lfm2.5-16k").model == "ollama_chat/lfm2.5-16k"
