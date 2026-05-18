# Strategy Seed Stability Sweep

- Benchmark file: `experiments/benchmark_sets/autotune_stratified_30.csv`
- Strategies: `cem,contextual_cem`
- Seeds: `7`
- Budget: trials=8, steps=8, limit=5

## Strategy Aggregate

| Strategy | Runs | Avg mean | Avg std | Avg min | Avg max | Improved mean | Wins | Errors |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| cem | 1 | 2.8478 | 0.0000 | 2.8478 | 2.8478 | 5.0000 | 0.5 | 0 |
| contextual_cem | 1 | 3.4144 | 0.0000 | 3.4144 | 3.4144 | 5.0000 | 4.5 | 0 |

## Per-Benchmark Aggregate

| Benchmark | Best strategy | Best mean | Margin | cem mean | contextual_cem mean |
| --- | --- | ---: | ---: | ---: | ---: |
| `benchmark://tensorflow-v0/1985` | contextual_cem | 3.7822 | 2.3474 | 1.4348 | 3.7822 |
| `benchmark://tensorflow-v0/2` | contextual_cem | 6.0326 | 0.2438 | 5.7888 | 6.0326 |
| `benchmark://opencv-v0/100` | contextual_cem | 1.4388 | 0.2135 | 1.2253 | 1.4388 |
| `benchmark://tensorflow-v0/50` | contextual_cem | 0.9866 | 0.0288 | 0.9579 | 0.9866 |
| `benchmark://tensorflow-v0/5` | cem,contextual_cem | 4.8320 | 0.0000 | 4.8320 | 4.8320 |

## Individual Runs

| Strategy | Seed | Avg improvement | Improved | Min | Max | Errors |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| cem | 7 | 2.8478 | 5 | 0.9579 | 5.7888 | 0 |
| contextual_cem | 7 | 3.4144 | 5 | 0.9866 | 6.0326 | 0 |
