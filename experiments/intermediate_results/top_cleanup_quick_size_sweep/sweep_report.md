# Strategy Seed Stability Sweep

- Benchmark file: `experiments/benchmark_sets/autotune_stratified_30.csv`
- Strategies: `contextual_cem`
- Seeds: `7,11`
- Budget: trials=12, steps=8, limit=10
- Objective: `total_ir_insts` (minimize)

## Strategy Aggregate

| Strategy | Runs | Avg mean | Avg std | Avg min | Avg max | Improved mean | Oz beaten mean | Avg best vs Oz | Wins | Errors | Oz errors |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| contextual_cem | 2 | 728.6500 | 530.4008 | 353.6000 | 1103.7000 | 10.0000 | 0.5000 | -1444.8500 | 20 | 0 | 0 |

## Per-Benchmark Aggregate

| Benchmark | Best strategy | Best mean | Margin | contextual_cem mean |
| --- | --- | ---: | ---: | ---: |
| `benchmark://chstone-v0/aes` | contextual_cem | 1619.0000 | 0.0000 | 1619.0000 |
| `benchmark://opencv-v0/100` | contextual_cem | 183.5000 | 0.0000 | 183.5000 |
| `benchmark://opencv-v0/3` | contextual_cem | 54.0000 | 0.0000 | 54.0000 |
| `benchmark://opencv-v0/4` | contextual_cem | 141.0000 | 0.0000 | 141.0000 |
| `benchmark://tensorflow-v0/1500` | contextual_cem | 235.5000 | 0.0000 | 235.5000 |
| `benchmark://tensorflow-v0/1985` | contextual_cem | 3942.5000 | 0.0000 | 3942.5000 |
| `benchmark://tensorflow-v0/2` | contextual_cem | 624.5000 | 0.0000 | 624.5000 |
| `benchmark://tensorflow-v0/4` | contextual_cem | 18.5000 | 0.0000 | 18.5000 |
| `benchmark://tensorflow-v0/5` | contextual_cem | 267.5000 | 0.0000 | 267.5000 |
| `benchmark://tensorflow-v0/50` | contextual_cem | 200.5000 | 0.0000 | 200.5000 |

## Individual Runs

| Strategy | Seed | Avg improvement | Improved | Oz beaten | Avg best vs Oz | Min | Max | Errors | Oz errors |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| contextual_cem | 7 | 1103.7000 | 10 | 0 | -1069.8000 | 21.0000 | 7384.0000 | 0 | 0 |
| contextual_cem | 11 | 353.6000 | 10 | 1 | -1819.9000 | 16.0000 | 1786.0000 | 0 | 0 |
