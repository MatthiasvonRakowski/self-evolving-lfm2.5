# Experiment audit and fixes

Audit of `lfm-evolve/` covering the harness code, the EvoAgentX internals it depends
on, and the completed runs under `runs/` (seeds 42, 44, 45).

Status: all fixes below are applied to the working tree. Nothing was committed or
pushed, and nothing under `runs/` was modified.

---

## 1. Findings

### 1.1 The baseline and the optimized arms were not answering the same question

`run_experiment.py` hardcoded `--benchmark gsm8k` for **all** training, then evaluated
on **all three** benchmarks. For the IFEval and MMLU-Pro columns that meant:

- `baseline` = `src/aflow_workflow/ifeval/` — a purpose-written instruction-following prompt
- `aflow` / `bilevel` / `mipro` = the **GSM8K-trained** artifact, i.e. "show your reasoning,
  then the final numerical answer prefixed with `####`"

Confirmed in the summaries: `runs/seed44/eval/ifeval/lfm2_5_16k/aflow.json` and the gsm8k
cell both cite `artifact_source: runs/seed44/train/lfm2_5_16k/aflow/round_12` — the same
artifact.

This is why `baseline` won **every** IFEval cell (0.813 vs aflow 0.460): a hand-written
IFEval prompt against a math solver. Only the **GSM8K column was a like-for-like
comparison**. MMLU-Pro and IFEval were cross-task transfer measurements presented as a
method comparison.

### 1.2 Crashes were recorded as successful results

`evaluate.py` swallowed every per-example exception into `prediction = "<error: ...>"`,
scored that string as a normal answer, and wrote `"status": "success"` unconditionally.

Worst case, `runs/seed42/eval/*/qwen3_1_7b_16k/bilevel.json`: **300/300** predictions were
`<error: name 'asyncio' is not defined>`.

Root cause in the evolved workflow itself —
`runs/seed42/train/qwen3_1_7b_16k/bilevel/round_3/graph.py:17` calls `await asyncio.gather(...)`
but never imports `asyncio` (lines 1-5). The optimizer LLM wrote code that cannot run.

It entered the results as real data:

| cell | reported |
|---|---|
| gsm8k | `0.000`, status `success` |
| mmlu_pro | `0.000`, status `success` |
| ifeval | **`0.133`**, status `success` |

The IFEval number is the dangerous one: IFEval scored the *error string* at 13.3%, because
checks like "no commas" or "lowercase" pass trivially on `<error: ...>`. That is a
plausible-looking fabricated number.

Same missing-import bug also in `runs/seed42/train/llama3_2_1b/aflow/round_8/graph.py`.

### 1.3 Ollama timeouts contaminated the qwen3 rows

Sweeping every eval cell for error predictions:

| cell | error rate | reported score |
|---|---|---|
| seed44 ifeval qwen3 **mipro** | 94/300 (31%) | 0.370 |
| seed42 ifeval qwen3 **aflow** | 85/300 (28%) | 0.283 |
| seed42 ifeval qwen3 **baseline** | 51/300 (17%) | 0.553 |
| seed44 ifeval qwen3 **aflow** | 42/300 (14%) | 0.390 |
| seed44 ifeval qwen3 **baseline** | 41/300 (14%) | 0.570 |
| seed44 mmlu_pro qwen3 **mipro** | 62/300 (21%) | 0.423 |

All `litellm.APIConnectionError: litellm.Timeout ... Timeout passed=600.0`. The method
ranking on qwen3/IFEval tracked the timeout rate more than workflow quality — the arm that
generates longest loses. An infrastructure artifact, not a finding.

### 1.4 The inner loop was selecting noise

`bilevel/inner_base.py` had `dev_eval_k = 40`, and every accept/reject in
`bilevel/__init__.py` (`if score > best_score`) was decided on 40 binary examples, where one
example is worth 0.025.

Extracted from the training logs (83 inner-loop episodes):

```
MIPRO beat baseline:      36/80
TextGrad beat baseline:   29/79
MIPRO    mean delta: +0.0113   median +0.0000
TextGrad mean delta: -0.0177   median +0.0000
```

Both mean effects are **smaller than the resolution of a single example**, and both medians
are exactly zero. The loop "improved" something in 47/83 rounds while consuming 4-5x AFlow's
wall time (48-64k s vs 9-13k s).

It was also the *same* 40 examples every time. `inner_base.py` seeded the subsample with the
constant `budget.seed`, and TextGrad's batches used `budget.seed + step` — varying by step
but not by round. Across all 20 outer rounds the arm's entire inner signal came from **one
fixed 40-example dev set and 16 fixed training examples**. That is the mechanism behind the
overfitting and the failure to transfer.

Additionally, `mipro_inner.py` tuned on `capped_view(benchmark, 40, seed)` and then
`bilevel/__init__.py` accepted or rejected on **those same 40** — selection on the tuning set.

### 1.5 The MIPRO arm was optimized through a broken harness

Every `best_program.json` contains `{{problem}}` (doubled braces). During optimization
`MiproOptimiser.py` did:

```python
prompt = self.prompt.format(problem=problem)
```

`str.format` turns `{{problem}}` into the literal text `{problem}` — **the question was never
substituted**. At eval time `evaluate.py` special-cased `{{problem}}` with `.replace()`, so it
worked there. MIPRO was searched under a harness that fed the model no question, then scored
under one that did.

Corroborating: 5 of 7 `best_program.json` files end with

```
Example 2:\nInputs:\n\n\nOutputs:\n\n\nExample 3:\nInputs:\n\n\nOutputs:\n...
```

Four **empty** few-shot demos — `max_bootstrapped_demos=4` silently produced nothing. And
`mipro_results.json` recorded `after: 3.0` for one run and `0.67` for another; a solve rate of
3.0 is on no scale, so that field was unusable.

### 1.6 Best-round selection was not reproducible

`_load_best_round()` was called, then `optimizer.test(benchmark)`. Upstream,
`aflow_optimizer.py:295` **appends test-set scores into the same `results.json`**, and
`data_utils.py:197` ranks rounds by `df.groupby("round")["score"].mean()` over everything in
that file.

So once `test()` has run, the ranking blends dev and test scores. On a resumed run — and
**13 of 14 runs show duplicate round numbering**, so nearly all were resumed —
`_get_optimization_sample()` picks which round to mutate from that contaminated ranking.
Test-set performance was steering the search on resume.

The recorded picks themselves are mostly fine: `best_round.json` matches the dev-only argmax
in **11 of 12** runs. The exception is `seed42/qwen3/bilevel` (recorded 3, dev argmax 6) — the
interrupted run, which is exactly the crashed cell from 1.2.

Related: `validation_rounds=1` meant each round got a **single** dev pass, and the best of 20
was selected from it. The repeated per-round entries in `results.json` are not
re-validations; they are the 3 test scores from `eval_rounds=3`. The ~12-15 point gap between
the selected round's dev score and its test scores is a dev-to-test generalization gap.

### 1.7 MMLU-Pro scoring had a loose fallback

`benchmarks/mmlu_pro.py` used `re.compile(r"\b([A-J])\b")` as a third pattern and returned
`matches[-1]` — the last standalone capital letter anywhere in the response, including the
article "A" at the start of a sentence. It awarded credit on a coin flip instead of recording
a parse failure. Because the arms differ in how well they hold the output format, this biased
the comparison in the same direction as the format damage being measured.

### 1.8 Smaller issues

- `bilevel/inner_base.py` `persist_prompt_module` rewrote `prompt.py` as `name = repr(value)`
  lines, silently destroying any import, comment, or helper the generator had put there.
- `bilevel/inner_base.py` `list_prompt_fields` grabbed *every* module-level string, so a
  non-prompt constant would become an optimization target.
- `bilevel/mipro_inner.py` had a bare `except Exception` → `logger.warning`. If inner MIPRO
  failed every round, bilevel silently degraded to "AFlow + TextGrad-lite". (Latent; it never
  fired in these runs.)
- `evaluate.py` had hardcoded fallback artifact paths into `results/lfm-results/...` and
  `results/comparaison-results/...` — a *different, older* experiment. Only passing
  `--artifacts_from_output` kept you off them.
- `common.py` bucketed cost with `str(model).startswith("anthropic/")`, but LiteLLM reports
  `claude-sonnet-4-6` without the prefix, so every Claude call counted as local and the
  optimizer cost printed as **$0.00**. The real spend was already in the usage jsonl:
  **$6.24 over 388 calls**.
- `common.py` hardcodes `ANTHROPIC_API_BASE` and monkeypatches `LiteLLM.init_model` to null
  out `litellm.api_base`. It works, but it will break silently on a LiteLLM upgrade.

### 1.9 Repo hygiene (not code)

- `lfm-evolve/code/` and `lfm-evolve/code (2)/` are **byte-identical copies** of the top-level
  code *and* `runs/` (`diff -rq` returns nothing). Three copies of the same 2.9 MB jsonl files
  are committed.
- 48 MB of archives tracked in git: `code.zip` (21 M), `code.tar.gz` (18 M), four
  `seed*_results.tar.gz`. The pack is 81 MB for a project whose source is ~50 KB.
- `results/` (untracked, 265 MB) is a full second clone of this repo; `results/lfm-backup/` is
  a third clone inside it.
- `main` is 1 commit ahead of `origin/main`, unpushed.
- Secrets are clean: both `.env` files hold `ANTHROPIC_API_KEY`, are covered by
  `.gitignore:151`, never appear in `git log --all`, and no `sk-ant-` string is in history.

---

## 2. Fixes applied

13 files modified, 2 added.

### The comparison itself

- **`run_experiment.py`, `main.py`** — benchmark is now a training dimension. `--benchmarks`
  trains each one separately into `<out>/<benchmark>/<model>/<method>/`, and eval resolves
  each benchmark against its own artifact. The hardcoded `--benchmark gsm8k` is gone.
- **`evaluate.py`** — artifact resolution prefers the new per-benchmark layout and **falls
  back to the existing layout**, so current runs still evaluate. Added `--trained-on`, which
  marks cells as transfer and scores `baseline` with the *training* benchmark's seed workflow,
  so a transfer cell is no longer compared against a purpose-written baseline for a task the
  other arms never saw.

### Crashes can no longer pass as results

- **`evaluate.py`** — records carry `execution_error`; cells get `error_rate`, `n_errors`,
  `parse_failures`, and status `invalid` above `--max-error-rate` (default 2%). `summary.md`
  renders invalid cells and transfer warnings.
- **`src/bilevel/inner_base.py`** — `eval_items` returns `(score, error_rate)` instead of
  swallowing exceptions into 0.0.
- **`src/BilevelOptimiser.py`** — a candidate graph that will not execute raises
  `BrokenWorkflowError` and scores 0 explicitly rather than being ranked.
- **`aggregate_results.py`** — excludes invalid cells and lists them.

### The inner loop

- `dev_eval_k` 40 → 100; `dev_split` returns **disjoint tune/select halves**, seeded by
  `(seed, round_index)` so each outer round draws fresh examples. MIPRO and TextGrad only see
  the tuning half; accept/reject uses the selection half.
- **`textgrad_lite.py`** — each step is scored and **reverted if worse**; crash transcripts are
  excluded from the critique instead of being sent to Claude as prompt failures.
- **`mipro_inner.py`** — tunes on the tuning split; MIPRO failures are recorded and reported.

### Other

- **`src/common.py`** — `fill_prompt_template` (shared by MIPRO optimization and eval, so they
  cannot diverge) and `is_anthropic_model` for cost bucketing.
- **`src/MiproOptimiser.py`** — uses the shared filler; `mipro_results.json` renames `after` →
  `mipro_internal_metric` and records `placeholder_ok`.
- **`src/aflow_base.py`** *(new)* — `TestIsolatedAFlowOptimizer` writes test scores to
  `test_results.json` so they cannot enter round selection on resume. `validation_rounds` is a
  parameter, default 3.
- **`src/benchmarks/mmlu_pro.py`** — dropped the bare `\b([A-J])\b` fallback; added
  `parse_failed`.
- **`rescore_results.py`** *(new)* — re-scores existing eval JSONs without touching them.

---

## 3. Verification

Run against the real data in `runs/`, not fixtures.

| check | result |
|---|---|
| `str.format` on all 7 real MIPRO artifacts | problem text inserted: **False** on all 7; `fill_prompt_template`: True on all 7 |
| Claude cost from real usage logs | **$6.24 / 388 calls** (was $0.00) |
| MMLU-Pro extraction | 9/9 cases, incl. "A student buys…" → `None` not `A` |
| tune/select splits | disjoint; 8/50 overlap across rounds; reproducible per round |
| broken graph in inner loop | `BrokenWorkflowError`, not a 0.0 score |
| `rescore_results.py` on `runs/` | 62 cells, **16 invalid**, `runs/` unmodified |
| aggregator with gating | `qwen3/bilevel` gsm8k: `0.5889 ± 0.5100 (n=3)` → `0.8833 ± 0.0094 (n=2)` |

All modules compile and import; the driver emits the expected commands.

That last row is the headline: the crashed cell was dragging a real 0.88 result down to 0.59
with a ±0.51 standard deviation.

---

## 4. Not fixed

1. **TextGrad fails on lfm2.5** (`failed / 798s` on seed 42, `failed / 736s` on seed 45,
   absent from seed 44, `unavailable` in all 8 eval cells). Root cause not diagnosed — it
   needs a live run to reproduce. As it stands the arm has no lfm2.5 data and is not
   comparable.
2. **The 600s Ollama timeouts.** Now *detected* (most of the 16 invalid cells), but the
   timeout itself is unchanged: the right fix depends on whether you want a longer timeout or
   a shorter generation cap for qwen3, and that choice changes what the numbers mean.
3. **Repo hygiene** (section 1.9) — untouched, since it does not affect results.

---

## 5. Consequences for re-running

A fresh `run_experiment.py` now trains 3 benchmarks instead of 1, so training cost rises
roughly 3x from the previous ~55h/seed. To keep the old scope:

```bash
python run_experiment.py --train-benchmarks gsm8k
```

Existing artifacts still resolve through the fallback layout, so the current `runs/` can be
re-evaluated without retraining:

```bash
python evaluate.py --trained-on gsm8k --optimizer_output_dir runs/seed44/train \
                   --output_dir <somewhere-new>
```

To inspect the existing results under the error gate without touching them:

```bash
python rescore_results.py --base-dir runs --output-dir rescored --trained-on gsm8k
```

---

## 6. Suggested order of work

1. Re-run the MIPRO arm — its search never saw the questions (1.5), so those numbers cannot
   be interpreted at all.
2. Decide the qwen3 timeout policy, then re-run the 16 invalid cells (1.3).
3. Diagnose or drop TextGrad on lfm2.5 (section 4.1).
4. Re-run bilevel with the disjoint, resampled splits and compare against the old numbers —
   this is the direct test of whether the contribution survives the fix (1.4).
5. Present GSM8K as the in-domain comparison and MMLU-Pro / IFEval as transfer, or retrain
   per benchmark for a full in-domain table (1.1).
