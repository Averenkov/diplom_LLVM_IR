# Strategy Seed Stability Sweep

- Benchmark file: `experiments/benchmark_sets/autotune_stratified_30.csv`
- Strategies: `contextual_cem`
- Seeds: `7,11`
- Budget: trials=12, steps=8, limit=10
- Objective: `total_ir_insts` (minimize)

## Strategy Aggregate

| Strategy | Runs | Avg mean | Avg std | Avg min | Avg max | Improved mean | Oz beaten mean | Avg best vs Oz | Wins | Errors | Oz errors |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| contextual_cem | 2 | 1094.3000 | 223.4457 | 936.3000 | 1252.3000 | 10.0000 | 0.0000 | -2547.7000 | 20 | 1 | 0 |

## Per-Benchmark Aggregate

| Benchmark | Best strategy | Best mean | Margin | contextual_cem mean |
| --- | --- | ---: | ---: | ---: |
| `benchmark://chstone-v0/aes` | contextual_cem | 1906.5000 | 0.0000 | 1906.5000 |
| `benchmark://opencv-v0/100` | contextual_cem | 237.0000 | 0.0000 | 237.0000 |
| `benchmark://opencv-v0/3` | contextual_cem | 136.5000 | 0.0000 | 136.5000 |
| `benchmark://opencv-v0/4` | contextual_cem | 46.0000 | 0.0000 | 46.0000 |
| `benchmark://tensorflow-v0/1500` | contextual_cem | 219.5000 | 0.0000 | 219.5000 |
| `benchmark://tensorflow-v0/1985` | contextual_cem | 6317.5000 | 0.0000 | 6317.5000 |
| `benchmark://tensorflow-v0/2` | contextual_cem | 904.5000 | 0.0000 | 904.5000 |
| `benchmark://tensorflow-v0/4` | contextual_cem | 64.0000 | 0.0000 | 64.0000 |
| `benchmark://tensorflow-v0/5` | contextual_cem | 679.0000 | 0.0000 | 679.0000 |
| `benchmark://tensorflow-v0/50` | contextual_cem | 432.5000 | 0.0000 | 432.5000 |

## Individual Runs

| Strategy | Seed | Avg improvement | Improved | Oz beaten | Avg best vs Oz | Min | Max | Errors | Oz errors |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| contextual_cem | 7 | 1252.3000 | 10 | 0 | -2389.7000 | 17.0000 | 7820.0000 | 1 | 0 |
| contextual_cem | 11 | 936.3000 | 10 | 0 | -2705.7000 | 14.0000 | 4815.0000 | 0 | 0 |
