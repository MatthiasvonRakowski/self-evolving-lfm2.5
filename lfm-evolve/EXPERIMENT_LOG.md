# Experiment log: five-seed campaign on the H100 box (November 2026)

Box: shared Brev H100 reached with `ssh gpu`, project folder `~/self-evolving-lfm2.5/lfm-evolve`,
everything long-running inside tmux session `run`. Ollama serves the seven executors with
`OLLAMA_MAX_LOADED_MODELS=4 OLLAMA_NUM_PARALLEL=8 OLLAMA_KEEP_ALIVE=-1`; lfm2.5 is served one request
at a time. Optimiser: `qwen3-coder-30b-32k`, local.

Executors (labels as they appear in the tables): lfm2_5_16k, qwen3_1_7b_16k, granite4_1b_16k,
granite4_1b_h_16k, falcon_h1_1_5b_16k, falcon3_1b_16k, rwkv7_1_5b_16k.

## 1. GSM8K optimisation and evaluation (finished 2026-11-14)

- Driver: `run_experiment.py --seeds 42 43 44 45 46 --methods aflow mipro --train-benchmarks gsm8k
  --per-model --parallel 5` with the seven executors; output under `runs/seedN/{train,eval}`.
- The box was restarted on 2026-11-13; the run was resumed in place (AFlow continues from its last
  complete round, see commits 0670fde and e2f2b3d).
- Durations per seed: train 10.4 to 13.9 h, eval 1.2 to 2.0 h.
- `runs/` also holds seed47 to seed51 from an earlier ten-seed attempt. They are kept for later study
  and excluded from the tables with the aggregator's `--seeds` option (commit ffd2673).
- Noted for the paper: granite4_1b MIPRO collapses on GSM8K on seeds 42 and 43 (-0.65, -0.52) with no
  execution errors. Not yet inspected; likely an answer-format breakdown.

## 2. Transfer pass, GSM8K artifacts scored on IFEval and MMLU-Pro (2026-11-14 to 2026-11-16)

One evaluate.py per seed, launched in tmux windows `transfer42..46` with a 30 s stagger:

```
MODELS=$(.venv/bin/python -c 'import json; print(" ".join(json.load(open("runs/driver_state.json"))["args"]["models"]))')
for s in 42 43 44 45 46; do
  tmux new-window -d -c "$PWD" -n transfer$s ".venv/bin/python -u evaluate.py --seed $s --n-test 300 --benchmarks ifeval mmlu_pro --trained-on gsm8k --models $MODELS --artifacts baseline aflow mipro --optimizer_output_dir runs/seed$s/train --output_dir runs/seed$s/eval --resume --concurrency 6 2>&1 | tee -a runs/seed$s/transfer_driver.log"
  sleep 30
done
```

42 cells per seed (7 models x 3 artifacts x 2 benchmarks), 210 in total. Seed 43 finished first
(2026-11-15 morning), the other four were queueing on lfm2.5's single slot and finished by 2026-11-16
morning.

### Incident: console output is not live

The logs showed only LiteLLM stderr warnings for over an hour, which was read as a start-up hang. The
first set of five processes was killed and relaunched; the relaunch showed the same empty logs.
A /proc inspection (py-spy cannot attach on this box, even with sudo) showed the main thread in
`ep_poll` with Ollama sockets open: the processes were working. Cause: `evoagentx/core/logging.py`
replaces `sys.stdout` with a block-buffered `TextIOWrapper` at import, which undoes `python -u`.
Everything evaluate.py prints reaches the log in 8 KB bursts or at exit; stderr is live.

Consequences: about one hour of the pass was lost to the first kill. Progress is judged by the cell
files, never by the log:

```
for s in 42 43 44 45 46; do n=$(ls runs/seed$s/eval/{ifeval,mmlu_pro}/*/*.json 2>/dev/null | wc -l); echo "seed $s: $n/42 cells done, running: $(pgrep -fc "evaluate.py --seed $s ")"; done
```

Optional one-line fix for live logs, not applied: `sys.stdout.reconfigure(line_buffering=True)` after
the imports in evaluate.py.

### Invalid cells and reruns (2026-11-16)

Four IFEval cells exceeded the 2 % execution-error threshold: seed 45 falcon3 baseline (37 errors),
seeds 42 and 46 falcon_h1 baseline (12 each), seed 43 falcon3 aflow (8). They were rerun one at a time
on the idle box (four minutes per cell). The three baselines came back with zero errors: their failures
were Ollama connection errors while five seeds loaded the box. The falcon3 aflow cell reproduced the
same 8 errors on the same prompts, all `{"error":"prediction aborted, token repeat limit reached"}`:
the model degenerates into a token loop under that workflow, Ollama aborts the generation. It stays
excluded under the 2 % rule (reported mean with the 8 prompts scored as failures: 0.233, baseline on
that seed 0.297, in line with the other four seeds). The small GSM8K error cells (falcon3, granite-h,
1 to 5 errors each) are most likely the same loop abort.

```
for job in "45 falcon3-1b-16k baseline" "42 falcon-h1-1.5b-16k baseline" "46 falcon-h1-1.5b-16k baseline" "43 falcon3-1b-16k aflow"; do set -- $job; .venv/bin/python -u evaluate.py --seed $1 --n-test 300 --benchmarks ifeval --trained-on gsm8k --models $2 --artifacts $3 --optimizer_output_dir runs/seed$1/train --output_dir runs/seed$1/eval --concurrency 6 2>&1 | tee -a runs/seed$1/transfer_rerun.log; done
```

### Aggregation

```
.venv/bin/python aggregate_results.py --base-dir runs --seeds 42 43 44 45 46
```

Writes `runs/FINAL_RESULTS.md`, `runs/final_results.json`, `runs/final_results.csv`. Paired McNemar
tests per seed x model, Holm-corrected.

After the reruns (aggregated 2026-11-16): IFEval baselines n=5 for all seven models, one invalid cell
left (seed 43 falcon3 aflow). Transfer means, IFEval prompt-strict accuracy, baseline / aflow / mipro:
falcon3 0.292 / 0.257 (n=4) / 0.225; falcon_h1 0.653 / 0.471 / 0.557; granite4_1b 0.409 / 0.278 / 0.435;
granite4_1b_h 0.646 / 0.533 / 0.559; lfm2.5 0.737 / 0.715 / 0.648; qwen3 0.611 / 0.520 / 0.509;
rwkv7 0.242 / 0.229 / 0.191.

## 3. Findings so far (five seeds)

- IFEval: negative transfer. Both AFlow and MIPRO score below the baseline on average for every model;
  29 of the 33 significant paired differences are negative. Interpretation: math-tuned workflows and
  prompts carry a GSM8K answer trailer into instruction-following tasks and break their constraints.
- MMLU-Pro (strict scoring): mixed. MIPRO gains for lfm2.5 (+0.05), qwen3 (+0.07) and falcon_h1 (+0.04);
  AFlow gains for qwen3; the granite family loses, granite4_1b AFlow collapses to 0.06.
- MMLU-Pro parse failures are high in every column, baselines included (12 % to 61 % of answers get no
  letter). The unparsed answers are almost all real answers in a form the scorer rejects: a
  GSM8K-style `#### F` line or `\boxed{I}`. In transfer mode the baseline is the GSM8K seed workflow,
  whose prompt asks for `####`, so the format conflict is inside the harness and affects all three
  columns. The strict MMLU-Pro score therefore mixes format compliance with reasoning.
- Re-score (2026-11-16, `rescore_mmlu_pro.py`, output `runs/MMLU_PRO_RESCORED.md/.csv`; the strict
  re-score reproduces the stored metric on every record). Lenient = strict plus `#### X` and
  `\boxed{X}`. Lenient accuracy, baseline / aflow / mipro: falcon3 0.130 / 0.108 / 0.112;
  falcon_h1 0.429 / 0.415 / 0.437; granite4_1b 0.285 / 0.258 / 0.206 (±0.10); granite4_1b_h
  0.259 / 0.229 / 0.219; lfm2.5 0.403 / 0.404 / 0.413; qwen3 0.411 / 0.451 / 0.430;
  rwkv7 0.171 / 0.187 / 0.151. Significant paired differences fall from 27 (strict: aflow 5 up / 6
  down, mipro 11 up / 5 down) to 10 (lenient: aflow 2 up / 2 down, mipro 1 up / 5 down).
  Reading: with the answer format controlled, GSM8K artifacts transfer roughly neutrally to MMLU-Pro.
  MIPRO's strict gains on lfm2.5, qwen3 and falcon_h1 were format effects (its prompt raises the
  strict parse rate, e.g. lfm2.5 0.72 -> 0.84, while lenient accuracy moves by about 0.01). The
  granite4_1b AFlow "collapse" (0.062 strict) is 0.258 lenient against a 0.285 baseline. What
  remains: qwen3 AFlow up on two seeds, and granite4_1b MIPRO down by about 0.2 on seeds 42 and 43,
  the same two seeds whose MIPRO program collapsed on GSM8K, so that program is genuinely damaged.
  rwkv7 and falcon3 give no recognisable letter on a third to a half of the questions under any
  parser; their accuracies are near the 0.10 chance level.

## 4. Open items

1. Done 2026-11-16: reruns folded in, IFEval n=5 everywhere, one cell left invalid (see above).
2. Done 2026-11-16: re-score written and run locally on a copy of the cell files (pulled with tar over
   ssh; rsync is not installed on the box). Rerun on the box or after any cell changes with
   `.venv/bin/python rescore_mmlu_pro.py --base-dir runs --seeds 42 43 44 45 46`.
3. Bilevel: not run in the campaign. Plan: back up `runs/driver_state.json`, read the GSM8K settings
   back from its `args`, time one cell (`--seeds 42 --models lfm2.5-16k --methods bilevel
   --train-benchmarks gsm8k --base-dir runs`, same `--rounds` and `--validation_rounds`), then choose
   the grid. Needs the optimiser model on the GPU, so not alongside other runs. The driver's final
   aggregation covers only the seeds it was given; rerun the aggregate command with all five after.
4. Inspect the granite4_1b MIPRO collapse on GSM8K (parse count, one wrong prediction, the optimised
   prompt in `runs/seed42/train/gsm8k/granite4_1b_16k/mipro/best_program.json`).
5. Paper: report strict MMLU-Pro with parse rates (and lenient if the script is written), one sentence
   each on bilevel not run and seeds 47 to 51 not completed, fix the abstract's "up to 20 rounds" to
   what ran, keep "non-Transformer" as the umbrella term.
