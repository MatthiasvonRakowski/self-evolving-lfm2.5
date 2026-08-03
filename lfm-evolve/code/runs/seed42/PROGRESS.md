# Experiment Progress

- Driver started: 2026-07-18T01:00:57
- Last updated: 2026-07-21T23:05:11
- Current: seed=42 stage=train
- Live log: `tail -f runs/seed42/train_driver.log`

## Training (status / elapsed / Claude cost)

| seed | model | aflow | textgrad | mipro | bilevel |
|---|---|---|---|---|---|
| 42 | lfm2_5_16k | success / 11376s | failed / 798s | success / 4010s | success / 55078s |
| 42 | qwen3_1_7b_16k | success / 51476s | success / 41419s | success / 14130s | running |

**Totals so far:** training wall time 49.5h, Claude cost $0.00

## Evaluation (cells done / total, failures)

| seed | done | failed | total |
|---|---|---|---|
| 42 | 0 | 0 | 30 |
