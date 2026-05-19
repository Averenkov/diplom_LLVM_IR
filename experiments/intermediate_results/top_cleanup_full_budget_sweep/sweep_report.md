# Strategy Seed Stability Sweep

- Benchmark file: `experiments/benchmark_sets/autotune_stratified_30.csv`
- Strategies: `random,bandit,cem,contextual_cem`
- Seeds: `7,11,17,23,31`
- Budget: trials=50, steps=16, limit=30
- Objective: `total_ir_insts` (minimize)

## Strategy Aggregate

| Strategy | Runs | Avg mean | Avg std | Avg min | Avg max | Improved mean | Oz beaten mean | Avg best vs Oz | Wins | Errors | Oz errors |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| bandit | 5 | 840.6067 | 106.4399 | 741.5000 | 1011.2667 | 29.6000 | 7.2000 | -206.1600 | 9.583333333333334 | 1 | 0 |
| cem | 5 | 931.3867 | 83.2655 | 821.1333 | 1054.5000 | 30.0000 | 10.0000 | -115.3800 | 29.583333333333332 | 3 | 0 |
| contextual_cem | 5 | 1064.1467 | 69.3852 | 955.3333 | 1127.4667 | 30.0000 | 11.4000 | 17.3800 | 89.08333333333333 | 4 | 0 |
| random | 5 | 906.7400 | 54.5285 | 846.4000 | 983.2000 | 30.0000 | 9.2000 | -140.0267 | 21.75 | 4 | 0 |

## Per-Benchmark Aggregate

| Benchmark | Best strategy | Best mean | Margin | random mean | bandit mean | cem mean | contextual_cem mean |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `benchmark://tensorflow-v0/1985` | contextual_cem | 13498.8000 | 3010.2000 | 10318.2000 | 9858.6000 | 10488.6000 | 13498.8000 |
| `benchmark://tensorflow-v0/50` | contextual_cem | 2518.2000 | 344.8000 | 1901.2000 | 1872.6000 | 2173.4000 | 2518.2000 |
| `benchmark://mibench-v1/susan-e-2` | contextual_cem | 866.0000 | 66.4000 | 799.6000 | 654.0000 | 785.4000 | 866.0000 |
| `benchmark://chstone-v0/gsm` | contextual_cem | 899.2000 | 63.6000 | 802.6000 | 668.8000 | 835.6000 | 899.2000 |
| `benchmark://tensorflow-v0/5` | contextual_cem | 1307.6000 | 54.4000 | 1152.4000 | 893.0000 | 1253.2000 | 1307.6000 |
| `benchmark://chstone-v0/jpeg` | contextual_cem | 1507.2000 | 48.8000 | 1458.4000 | 1396.8000 | 1446.6000 | 1507.2000 |
| `benchmark://tensorflow-v0/500` | contextual_cem | 287.6000 | 42.6000 | 245.0000 | 209.6000 | 227.6000 | 287.6000 |
| `benchmark://tensorflow-v0/2` | cem | 1542.0000 | 31.6000 | 1505.0000 | 1473.4000 | 1542.0000 | 1510.4000 |
| `benchmark://opencv-v0/100` | contextual_cem | 359.8000 | 29.4000 | 330.4000 | 237.8000 | 312.6000 | 359.8000 |
| `benchmark://chstone-v0/aes` | contextual_cem | 1863.6000 | 27.4000 | 1827.2000 | 1699.0000 | 1836.2000 | 1863.6000 |
| `benchmark://chstone-v0/blowfish` | contextual_cem | 921.8000 | 24.6000 | 897.2000 | 884.6000 | 896.6000 | 921.8000 |
| `benchmark://chstone-v0/adpcm` | contextual_cem | 662.8000 | 23.6000 | 639.2000 | 553.0000 | 607.4000 | 662.8000 |
| `benchmark://chstone-v0/dfsin` | contextual_cem | 1064.2000 | 16.2000 | 1048.0000 | 992.2000 | 1014.2000 | 1064.2000 |
| `benchmark://tensorflow-v0/1500` | contextual_cem | 287.8000 | 12.8000 | 275.0000 | 175.4000 | 250.0000 | 287.8000 |
| `benchmark://mibench-v1/mad-1` | contextual_cem | 187.0000 | 11.4000 | 174.6000 | 154.8000 | 175.6000 | 187.0000 |
| `benchmark://opencv-v0/442` | contextual_cem | 48.6000 | 9.8000 | 36.4000 | 26.4000 | 38.8000 | 48.6000 |
| `benchmark://opencv-v0/4` | cem | 498.4000 | 9.6000 | 414.8000 | 296.8000 | 498.4000 | 488.8000 |
| `benchmark://tensorflow-v0/3` | contextual_cem | 54.8000 | 8.2000 | 41.8000 | 39.4000 | 46.6000 | 54.8000 |
| `benchmark://npb-v0/4` | contextual_cem | 635.8000 | 5.8000 | 630.0000 | 571.8000 | 616.6000 | 635.8000 |
| `benchmark://tensorflow-v0/4` | contextual_cem | 121.4000 | 5.2000 | 92.6000 | 70.4000 | 116.2000 | 121.4000 |
| `benchmark://npb-v0/3` | contextual_cem | 359.6000 | 4.6000 | 355.0000 | 329.6000 | 347.8000 | 359.6000 |
| `benchmark://tensorflow-v0/25` | contextual_cem | 24.0000 | 4.2000 | 18.2000 | 15.0000 | 19.8000 | 24.0000 |
| `benchmark://mibench-v1/jpeg-c` | contextual_cem | 416.8000 | 4.2000 | 412.6000 | 390.2000 | 396.0000 | 416.8000 |
| `benchmark://mibench-v1/lame-newmdct-1` | contextual_cem | 244.2000 | 3.6000 | 237.6000 | 234.0000 | 240.6000 | 244.2000 |
| `benchmark://mibench-v1/lame-takehiro-1` | contextual_cem | 220.4000 | 3.0000 | 217.4000 | 190.4000 | 215.2000 | 220.4000 |
| `benchmark://opencv-v0/50` | contextual_cem | 299.0000 | 3.0000 | 186.2000 | 185.2000 | 296.0000 | 299.0000 |
| `benchmark://opencv-v0/3` | contextual_cem | 168.0000 | 2.2000 | 103.4000 | 116.8000 | 165.8000 | 168.0000 |
| `benchmark://mibench-v1/lame-psymodel` | contextual_cem | 971.0000 | 1.8000 | 952.6000 | 900.6000 | 969.2000 | 971.0000 |
| `benchmark://npb-v0/122` | random,cem,contextual_cem | 128.0000 | 1.2000 | 128.0000 | 126.8000 | 128.0000 | 128.0000 |
| `benchmark://opencv-v0/150` | contextual_cem | 2.0000 | 0.4000 | 1.6000 | 1.2000 | 1.6000 | 2.0000 |

## Individual Runs

| Strategy | Seed | Avg improvement | Improved | Oz beaten | Avg best vs Oz | Min | Max | Errors | Oz errors |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| bandit | 7 | 1011.2667 | 30 | 9 | -35.5000 | 2.0000 | 13198.0000 | 0 | 0 |
| bandit | 11 | 856.7333 | 30 | 8 | -190.0333 | 2.0000 | 9653.0000 | 1 | 0 |
| bandit | 17 | 763.1000 | 29 | 5 | -283.6667 | 0.0000 | 8330.0000 | 0 | 0 |
| bandit | 23 | 741.5000 | 30 | 6 | -305.2667 | 2.0000 | 7810.0000 | 0 | 0 |
| bandit | 31 | 830.4333 | 29 | 8 | -216.3333 | 0.0000 | 10302.0000 | 0 | 0 |
| cem | 7 | 821.1333 | 30 | 9 | -225.6333 | 2.0000 | 8219.0000 | 0 | 0 |
| cem | 11 | 912.7333 | 30 | 11 | -134.0333 | 1.0000 | 9653.0000 | 1 | 0 |
| cem | 17 | 1054.5000 | 30 | 8 | 7.7333 | 1.0000 | 15002.0000 | 0 | 0 |
| cem | 23 | 939.5333 | 30 | 11 | -107.2333 | 2.0000 | 9267.0000 | 0 | 0 |
| cem | 31 | 929.0333 | 30 | 11 | -117.7333 | 2.0000 | 10302.0000 | 2 | 0 |
| contextual_cem | 7 | 1127.4667 | 30 | 11 | 80.7000 | 2.0000 | 15858.0000 | 1 | 0 |
| contextual_cem | 11 | 955.3333 | 30 | 11 | -91.4333 | 2.0000 | 10130.0000 | 0 | 0 |
| contextual_cem | 17 | 1037.6333 | 30 | 12 | -9.1333 | 2.0000 | 12898.0000 | 2 | 0 |
| contextual_cem | 23 | 1092.6667 | 30 | 12 | 45.9000 | 2.0000 | 14007.0000 | 0 | 0 |
| contextual_cem | 31 | 1107.6333 | 30 | 11 | 60.8667 | 2.0000 | 14601.0000 | 1 | 0 |
| random | 7 | 930.0667 | 30 | 9 | -116.7000 | 2.0000 | 10318.0000 | 0 | 0 |
| random | 11 | 863.7333 | 30 | 8 | -183.0333 | 1.0000 | 9653.0000 | 3 | 0 |
| random | 17 | 846.4000 | 30 | 8 | -200.3667 | 1.0000 | 8754.0000 | 0 | 0 |
| random | 23 | 983.2000 | 30 | 11 | -63.5667 | 2.0000 | 12564.0000 | 0 | 0 |
| random | 31 | 910.3000 | 30 | 10 | -136.4667 | 2.0000 | 10302.0000 | 1 | 0 |
