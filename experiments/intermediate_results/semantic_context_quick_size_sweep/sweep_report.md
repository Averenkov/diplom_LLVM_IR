# Strategy Seed Stability Sweep

- Benchmark file: `experiments/benchmark_sets/autotune_stratified_30.csv`
- Strategies: `cem,contextual_cem`
- Seeds: `7,11`
- Budget: trials=12, steps=8, limit=10
- Objective: `total_ir_insts` (minimize)

## Strategy Aggregate

| Strategy | Runs | Avg mean | Avg std | Avg min | Avg max | Improved mean | Oz beaten mean | Avg best vs Oz | Wins | Errors | Oz errors |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| cem | 2 | 903.2500 | 536.1991 | 524.1000 | 1282.4000 | 10.0000 | 0.0000 | -2738.7500 | 7.5 | 0 | 0 |
| contextual_cem | 2 | 1012.2000 | 554.6546 | 620.0000 | 1404.4000 | 10.0000 | 0.5000 | -2629.8000 | 12.5 | 0 | 0 |

## Per-Benchmark Aggregate

| Benchmark | Best strategy | Best mean | Margin | cem mean | contextual_cem mean |
| --- | --- | ---: | ---: | ---: | ---: |
| `benchmark://tensorflow-v0/1985` | contextual_cem | 5611.5000 | 1283.0000 | 4328.5000 | 5611.5000 |
| `benchmark://tensorflow-v0/2` | cem | 1671.0000 | 833.5000 | 1671.0000 | 837.5000 |
| `benchmark://tensorflow-v0/5` | contextual_cem | 1013.5000 | 369.0000 | 644.5000 | 1013.5000 |
| `benchmark://opencv-v0/4` | contextual_cem | 365.5000 | 209.0000 | 156.5000 | 365.5000 |
| `benchmark://tensorflow-v0/50` | cem | 373.0000 | 188.0000 | 373.0000 | 185.0000 |
| `benchmark://tensorflow-v0/1500` | contextual_cem | 197.0000 | 159.0000 | 38.0000 | 197.0000 |
| `benchmark://chstone-v0/aes` | contextual_cem | 1644.5000 | 130.0000 | 1514.5000 | 1644.5000 |
| `benchmark://opencv-v0/100` | cem | 121.5000 | 32.5000 | 121.5000 | 89.0000 |
| `benchmark://opencv-v0/3` | cem | 128.0000 | 7.5000 | 128.0000 | 120.5000 |
| `benchmark://tensorflow-v0/4` | contextual_cem | 58.0000 | 1.0000 | 57.0000 | 58.0000 |

## Individual Runs

| Strategy | Seed | Avg improvement | Improved | Oz beaten | Avg best vs Oz | Min | Max | Errors | Oz errors |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| cem | 7 | 1282.4000 | 10 | 0 | -2359.6000 | 41.0000 | 8281.0000 | 0 | 0 |
| cem | 11 | 524.1000 | 10 | 0 | -3117.9000 | 6.0000 | 1702.0000 | 0 | 0 |
| contextual_cem | 7 | 1404.4000 | 10 | 0 | -2237.6000 | 20.0000 | 9945.0000 | 0 | 0 |
| contextual_cem | 11 | 620.0000 | 10 | 1 | -3022.0000 | 29.0000 | 1784.0000 | 0 | 0 |
