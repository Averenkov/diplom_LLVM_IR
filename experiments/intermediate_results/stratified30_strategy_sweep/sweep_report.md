# Strategy Seed Stability Sweep

- Benchmark file: `experiments/benchmark_sets/autotune_stratified_30.csv`
- Strategies: `random,bandit,contextual_bandit,cem`
- Seeds: `7,11,17`
- Budget: trials=12, steps=8, limit=0

## Strategy Aggregate

| Strategy | Runs | Avg mean | Avg std | Avg min | Avg max | Improved mean | Wins | Errors |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| bandit | 3 | 3.9416 | 0.8304 | 3.1378 | 4.7963 | 29.3333 | 19.833333333333332 | 0 |
| cem | 3 | 4.2191 | 0.3326 | 3.8770 | 4.5413 | 29.6667 | 28 | 0 |
| contextual_bandit | 3 | 4.0650 | 0.1120 | 3.9391 | 4.1533 | 29.3333 | 21.499999999999996 | 0 |
| random | 3 | 4.0645 | 0.6808 | 3.3969 | 4.7578 | 30.0000 | 20.666666666666668 | 1 |

## Per-Benchmark Aggregate

| Benchmark | Best strategy | Best mean | Margin | random mean | bandit mean | contextual_bandit mean | cem mean |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `benchmark://chstone-v0/adpcm` | random | 21.5621 | 8.1972 | 21.5621 | 12.8589 | 13.3650 | 12.9349 |
| `benchmark://npb-v0/122` | random | 8.4327 | 4.8113 | 8.4327 | 3.5548 | 3.5548 | 3.6214 |
| `benchmark://tensorflow-v0/1985` | bandit | 16.9590 | 4.0355 | 12.9235 | 16.9590 | 6.9963 | 8.3084 |
| `benchmark://chstone-v0/dfsin` | contextual_bandit | 11.2440 | 2.9102 | 8.1286 | 8.3337 | 11.2440 | 7.9544 |
| `benchmark://opencv-v0/50` | cem | 6.1650 | 2.8757 | 2.8014 | 3.2775 | 3.2893 | 6.1650 |
| `benchmark://chstone-v0/gsm` | cem | 7.5194 | 2.5017 | 3.7680 | 5.0176 | 2.3147 | 7.5194 |
| `benchmark://mibench-v1/lame-psymodel` | contextual_bandit | 11.5737 | 1.6371 | 8.3788 | 7.5789 | 11.5737 | 9.9366 |
| `benchmark://opencv-v0/4` | cem | 6.0949 | 1.5195 | 2.2528 | 3.9780 | 4.5754 | 6.0949 |
| `benchmark://chstone-v0/aes` | contextual_bandit | 3.9622 | 1.2446 | 1.4105 | 1.3911 | 3.9622 | 2.7176 |
| `benchmark://mibench-v1/lame-takehiro-1` | bandit,contextual_bandit | 6.7984 | 1.0917 | 5.4756 | 6.7984 | 6.7984 | 5.7068 |
| `benchmark://tensorflow-v0/500` | cem | 4.6551 | 1.0828 | 3.0479 | 3.5723 | 2.5528 | 4.6551 |
| `benchmark://chstone-v0/blowfish` | contextual_bandit | 2.0209 | 0.9447 | 0.6829 | 1.0762 | 2.0209 | 0.9538 |
| `benchmark://npb-v0/4` | cem | 3.6208 | 0.8952 | 2.1856 | 2.6966 | 2.7256 | 3.6208 |
| `benchmark://tensorflow-v0/50` | contextual_bandit | 6.4107 | 0.8851 | 5.5256 | 2.3631 | 6.4107 | 3.2775 |
| `benchmark://opencv-v0/442` | random | 2.8900 | 0.8101 | 2.8900 | 1.4782 | 0.8991 | 2.0798 |
| `benchmark://tensorflow-v0/1500` | bandit | 2.2209 | 0.7396 | 1.2836 | 2.2209 | 0.9541 | 1.4813 |
| `benchmark://mibench-v1/susan-e-2` | bandit | 2.2780 | 0.6675 | 1.5768 | 2.2780 | 1.6105 | 1.5334 |
| `benchmark://tensorflow-v0/3` | cem | 2.3052 | 0.6072 | 1.6980 | 0.9223 | 0.9636 | 2.3052 |
| `benchmark://tensorflow-v0/5` | random | 4.6302 | 0.4852 | 4.6302 | 3.0192 | 4.1450 | 3.8187 |
| `benchmark://tensorflow-v0/25` | contextual_bandit | 3.1144 | 0.4055 | 2.2135 | 2.0405 | 3.1144 | 2.7089 |
| `benchmark://opencv-v0/150` | random | 1.3093 | 0.3520 | 1.3093 | 0.5311 | 0.8729 | 0.9573 |
| `benchmark://opencv-v0/3` | bandit | 3.0798 | 0.3178 | 2.7620 | 3.0798 | 1.0453 | 1.9518 |
| `benchmark://tensorflow-v0/2` | random | 2.7323 | 0.2701 | 2.7323 | 1.4582 | 2.4622 | 0.9286 |
| `benchmark://npb-v0/3` | contextual_bandit | 5.9970 | 0.2078 | 3.9292 | 5.7892 | 5.9970 | 5.1546 |
| `benchmark://mibench-v1/lame-newmdct-1` | contextual_bandit | 5.3795 | 0.1936 | 2.9361 | 4.8238 | 5.3795 | 5.1858 |
| `benchmark://opencv-v0/100` | random | 1.4807 | 0.0912 | 1.4807 | 1.2395 | 0.9068 | 1.3895 |
| `benchmark://mibench-v1/jpeg-c` | contextual_bandit | 1.3244 | 0.0430 | 1.2814 | 0.8830 | 1.3244 | 1.1768 |
| `benchmark://mibench-v1/mad-1` | cem | 6.8267 | 0.0356 | 2.8716 | 4.8437 | 6.7911 | 6.8267 |
| `benchmark://tensorflow-v0/4` | cem | 2.7709 | 0.0329 | 1.0744 | 1.3365 | 2.7380 | 2.7709 |
| `benchmark://chstone-v0/jpeg` | bandit | 2.8492 | 0.0112 | 0.6913 | 2.8492 | 1.3638 | 2.8380 |

## Individual Runs

| Strategy | Seed | Avg improvement | Improved | Min | Max | Errors |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| bandit | 7 | 4.7963 | 29 | 0.0000 | 21.3207 | 0 |
| bandit | 11 | 3.1378 | 29 | 0.0000 | 9.3650 | 0 |
| bandit | 17 | 3.8909 | 30 | 0.0029 | 21.9639 | 0 |
| cem | 7 | 3.8770 | 30 | 0.2472 | 9.3650 | 0 |
| cem | 11 | 4.5413 | 29 | 0.0000 | 19.8592 | 0 |
| cem | 17 | 4.2391 | 30 | 0.0026 | 11.6972 | 0 |
| contextual_bandit | 7 | 4.1533 | 30 | 0.1145 | 18.8806 | 0 |
| contextual_bandit | 11 | 3.9391 | 28 | 0.0000 | 14.8019 | 0 |
| contextual_bandit | 17 | 4.1028 | 30 | 0.1208 | 19.8592 | 0 |
| random | 7 | 3.3969 | 30 | 0.0195 | 19.8592 | 1 |
| random | 11 | 4.0389 | 30 | 0.1962 | 24.9826 | 0 |
| random | 17 | 4.7578 | 30 | 0.0297 | 19.8447 | 0 |
