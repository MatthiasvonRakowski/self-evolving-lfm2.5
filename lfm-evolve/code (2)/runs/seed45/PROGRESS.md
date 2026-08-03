# Experiment Progress

- Driver started: 2026-07-18T21:39:24
- Last updated: 2026-07-22T09:43:27
- Current: seed=45 stage=train
- Live log: `tail -f runs/seed45/train_driver.log`

## Training (status / elapsed / Claude cost)

| seed | model | aflow | textgrad | mipro | bilevel |
|---|---|---|---|---|---|
| 45 | lfm2_5_16k | success / 9213s | failed / 736s | success / 3779s | success / 58736s |
| 45 | qwen3_1_7b_16k | success / 80846s | success / 51288s | success / 13943s | running |

**Totals so far:** training wall time 60.7h, Claude cost $0.00

## Evaluation (cells done / total, failures)

| seed | done | failed | total |
|---|---|---|---|
| 45 | 0 | 0 | 30 |
