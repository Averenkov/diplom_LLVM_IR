# Strategy Seed Stability Sweep

- Benchmark file: `experiments/benchmark_sets/autotune_stratified_30.csv`
- Strategies: `random,bandit,contextual_bandit,cem,contextual_cem`
- Seeds: `7,11,17,23,31`
- Budget: trials=30, steps=12, limit=0

## Strategy Aggregate

| Strategy | Runs | Avg mean | Avg std | Avg min | Avg max | Improved mean | Wins | Errors |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| bandit | 5 | 5.5201 | 0.6857 | 4.6092 | 6.4084 | 29.4000 | 18.03333333333333 | 0 |
| cem | 5 | 6.5458 | 0.2429 | 6.2367 | 6.7805 | 30.0000 | 26.03333333333333 | 0 |
| contextual_bandit | 5 | 6.4642 | 0.4813 | 5.7049 | 6.9136 | 30.0000 | 29.866666666666664 | 0 |
| contextual_cem | 5 | 7.2217 | 0.2198 | 6.8813 | 7.4908 | 30.0000 | 45.86666666666667 | 1 |
| random | 5 | 6.6175 | 0.4595 | 5.8855 | 7.0036 | 30.0000 | 30.2 | 0 |

## Per-Benchmark Aggregate

| Benchmark | Best strategy | Best mean | Margin | random mean | bandit mean | contextual_bandit mean | cem mean | contextual_cem mean |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `benchmark://mibench-v1/lame-psymodel` | contextual_cem | 14.1169 | 3.3763 | 10.6679 | 8.6029 | 10.7406 | 9.5107 | 14.1169 |
| `benchmark://tensorflow-v0/1985` | bandit | 19.4850 | 2.8669 | 12.5008 | 19.4850 | 16.6181 | 13.3019 | 12.0506 |
| `benchmark://mibench-v1/lame-takehiro-1` | contextual_cem | 10.5854 | 2.2416 | 8.3438 | 8.2795 | 7.8260 | 7.5937 | 10.5854 |
| `benchmark://chstone-v0/dfsin` | contextual_bandit | 20.0481 | 2.0745 | 17.3530 | 16.2955 | 20.0481 | 17.9736 | 16.5237 |
| `benchmark://npb-v0/4` | contextual_cem | 7.2754 | 1.9509 | 4.5882 | 3.1015 | 4.8477 | 5.3246 | 7.2754 |
| `benchmark://npb-v0/122` | random | 13.0979 | 1.5679 | 13.0979 | 3.8234 | 4.5688 | 10.9869 | 11.5300 |
| `benchmark://opencv-v0/50` | contextual_cem | 10.1256 | 1.5064 | 8.4597 | 7.7632 | 8.2512 | 8.6192 | 10.1256 |
| `benchmark://tensorflow-v0/25` | contextual_cem | 5.4743 | 1.3254 | 4.1489 | 2.8808 | 4.0308 | 4.1040 | 5.4743 |
| `benchmark://mibench-v1/mad-1` | contextual_cem | 11.9323 | 1.2575 | 7.1406 | 10.4544 | 10.6748 | 7.3225 | 11.9323 |
| `benchmark://tensorflow-v0/50` | contextual_bandit | 8.0216 | 1.2083 | 5.8860 | 2.7886 | 8.0216 | 6.8133 | 6.7255 |
| `benchmark://npb-v0/3` | contextual_cem | 6.9595 | 0.9494 | 5.8272 | 4.4179 | 6.0101 | 5.1398 | 6.9595 |
| `benchmark://chstone-v0/jpeg` | random | 5.0997 | 0.9426 | 5.0997 | 2.9645 | 3.9648 | 4.1571 | 4.0531 |
| `benchmark://tensorflow-v0/2` | contextual_cem | 7.2523 | 0.9390 | 6.0065 | 5.3569 | 6.3133 | 5.8509 | 7.2523 |
| `benchmark://mibench-v1/jpeg-c` | random | 4.0232 | 0.8989 | 4.0232 | 1.5653 | 2.0267 | 2.2718 | 3.1243 |
| `benchmark://tensorflow-v0/4` | bandit | 4.7489 | 0.8897 | 2.6249 | 4.7489 | 3.2435 | 2.6631 | 3.8592 |
| `benchmark://mibench-v1/lame-newmdct-1` | cem | 6.9446 | 0.7457 | 6.1232 | 5.8625 | 5.9606 | 6.9446 | 6.1989 |
| `benchmark://tensorflow-v0/5` | cem | 5.2969 | 0.5978 | 4.6019 | 3.8964 | 4.6991 | 5.2969 | 4.5985 |
| `benchmark://opencv-v0/442` | contextual_bandit | 3.4772 | 0.3728 | 2.9775 | 1.2275 | 3.4772 | 3.1044 | 2.7583 |
| `benchmark://tensorflow-v0/3` | contextual_cem | 3.0270 | 0.3017 | 2.4622 | 2.1335 | 2.2555 | 2.7252 | 3.0270 |
| `benchmark://chstone-v0/aes` | cem | 4.1119 | 0.2924 | 3.2186 | 3.6086 | 3.7644 | 4.1119 | 3.8195 |
| `benchmark://chstone-v0/gsm` | cem | 9.6729 | 0.2917 | 9.3812 | 7.8155 | 8.7621 | 9.6729 | 8.4810 |
| `benchmark://opencv-v0/4` | contextual_cem | 7.9134 | 0.2682 | 6.9152 | 5.6491 | 7.6452 | 6.8008 | 7.9134 |
| `benchmark://chstone-v0/adpcm` | cem | 25.6057 | 0.2406 | 23.1987 | 19.8039 | 19.3508 | 25.6057 | 25.3652 |
| `benchmark://opencv-v0/100` | contextual_cem | 2.1249 | 0.1559 | 1.5877 | 0.8372 | 1.4257 | 1.9691 | 2.1249 |
| `benchmark://chstone-v0/blowfish` | random | 2.7183 | 0.1508 | 2.7183 | 1.5326 | 2.5675 | 2.0992 | 1.8833 |
| `benchmark://tensorflow-v0/1500` | contextual_bandit | 3.3526 | 0.1266 | 3.1929 | 3.2260 | 3.3526 | 3.0361 | 2.4099 |
| `benchmark://tensorflow-v0/500` | random | 9.7881 | 0.0826 | 9.7881 | 3.0663 | 8.3032 | 6.5082 | 9.7056 |
| `benchmark://opencv-v0/3` | random | 3.1831 | 0.0335 | 3.1831 | 1.3721 | 1.5081 | 3.1497 | 3.0006 |
| `benchmark://mibench-v1/susan-e-2` | contextual_cem | 2.4517 | 0.0328 | 2.3110 | 2.4189 | 2.3584 | 2.4069 | 2.4517 |
| `benchmark://opencv-v0/150` | contextual_cem | 1.3265 | 0.0171 | 1.0981 | 0.6250 | 1.3093 | 1.3093 | 1.3265 |

## Individual Runs

| Strategy | Seed | Avg improvement | Improved | Min | Max | Errors |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| bandit | 7 | 5.7125 | 30 | 0.1189 | 28.3428 | 0 |
| bandit | 11 | 6.4084 | 30 | 0.1064 | 28.3853 | 0 |
| bandit | 17 | 5.7596 | 29 | 0.0000 | 26.0522 | 0 |
| bandit | 23 | 4.6092 | 28 | 0.0000 | 26.1670 | 0 |
| bandit | 31 | 5.1109 | 30 | 0.0948 | 14.8478 | 0 |
| cem | 7 | 6.7805 | 30 | 1.3093 | 26.0567 | 0 |
| cem | 11 | 6.7591 | 30 | 1.3093 | 25.2797 | 0 |
| cem | 17 | 6.2367 | 30 | 1.3093 | 26.8250 | 0 |
| cem | 23 | 6.3533 | 30 | 1.3093 | 24.9768 | 0 |
| cem | 31 | 6.5994 | 30 | 1.3093 | 24.8905 | 0 |
| contextual_bandit | 7 | 6.7708 | 30 | 0.3340 | 28.3559 | 0 |
| contextual_bandit | 11 | 6.3011 | 30 | 0.3136 | 19.8806 | 0 |
| contextual_bandit | 17 | 6.9136 | 30 | 1.3093 | 25.5491 | 0 |
| contextual_bandit | 23 | 6.6306 | 30 | 1.3093 | 25.9806 | 0 |
| contextual_bandit | 31 | 5.7049 | 30 | 0.4716 | 15.1694 | 0 |
| contextual_cem | 7 | 7.1995 | 30 | 1.3093 | 27.4928 | 0 |
| contextual_cem | 11 | 7.2611 | 30 | 1.3949 | 24.7577 | 0 |
| contextual_cem | 17 | 6.8813 | 30 | 1.1127 | 23.5362 | 1 |
| contextual_cem | 23 | 7.4908 | 30 | 1.3093 | 25.0263 | 0 |
| contextual_cem | 31 | 7.2761 | 30 | 1.3093 | 26.0128 | 0 |
| random | 7 | 5.8855 | 30 | 1.3093 | 19.4366 | 0 |
| random | 11 | 7.0036 | 30 | 1.3093 | 24.4987 | 0 |
| random | 17 | 6.8286 | 30 | 1.3093 | 24.7775 | 0 |
| random | 23 | 6.9152 | 30 | 1.3093 | 22.8352 | 0 |
| random | 31 | 6.4548 | 30 | 0.2533 | 24.4456 | 0 |
