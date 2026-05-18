# Strategy Seed Stability Sweep

- Benchmark file: `experiments/benchmark_sets/autotune_stratified_30.csv`
- Strategies: `random,cem,contextual_cem`
- Seeds: `7,11,17,23,31`
- Budget: trials=30, steps=12, limit=0
- Objective: `total_ir_insts` (minimize)

## Strategy Aggregate

| Strategy | Runs | Avg mean | Avg std | Avg min | Avg max | Improved mean | Oz beaten mean | Avg best vs Oz | Wins | Errors | Oz errors |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| cem | 5 | 747.2067 | 152.2845 | 532.6333 | 931.6000 | 29.4000 | 5.4000 | -828.3600 | 57.83333333333334 | 0 | 0 |
| contextual_cem | 5 | 868.5000 | 127.8485 | 712.9333 | 1061.8333 | 29.6000 | 4.8000 | -707.0667 | 52.833333333333336 | 0 | 0 |
| random | 5 | 742.2667 | 169.3658 | 488.6000 | 914.8333 | 29.6000 | 4.2000 | -833.3000 | 39.333333333333336 | 0 | 0 |

## Per-Benchmark Aggregate

| Benchmark | Best strategy | Best mean | Margin | random mean | cem mean | contextual_cem mean |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| `benchmark://tensorflow-v0/1985` | contextual_cem | 10312.4000 | 2009.6000 | 8302.8000 | 8073.4000 | 10312.4000 |
| `benchmark://tensorflow-v0/50` | contextual_cem | 1782.6000 | 1011.6000 | 686.4000 | 771.0000 | 1782.6000 |
| `benchmark://tensorflow-v0/5` | contextual_cem | 680.6000 | 326.6000 | 158.0000 | 354.0000 | 680.6000 |
| `benchmark://chstone-v0/aes` | cem | 1956.2000 | 118.8000 | 1761.2000 | 1956.2000 | 1837.4000 |
| `benchmark://chstone-v0/gsm` | cem | 857.8000 | 75.6000 | 782.2000 | 857.8000 | 750.6000 |
| `benchmark://tensorflow-v0/2` | contextual_cem | 1611.2000 | 42.4000 | 1568.8000 | 1307.0000 | 1611.2000 |
| `benchmark://mibench-v1/susan-e-2` | cem | 798.2000 | 39.6000 | 758.6000 | 798.2000 | 752.8000 |
| `benchmark://opencv-v0/100` | random | 230.4000 | 38.2000 | 230.4000 | 192.2000 | 186.8000 |
| `benchmark://chstone-v0/adpcm` | contextual_cem | 647.4000 | 31.8000 | 583.8000 | 615.6000 | 647.4000 |
| `benchmark://chstone-v0/jpeg` | random | 1561.6000 | 31.8000 | 1561.6000 | 1512.4000 | 1529.8000 |
| `benchmark://npb-v0/4` | cem | 596.4000 | 29.0000 | 529.4000 | 596.4000 | 567.4000 |
| `benchmark://opencv-v0/3` | random | 136.0000 | 22.4000 | 136.0000 | 113.6000 | 111.4000 |
| `benchmark://chstone-v0/dfsin` | cem | 1111.2000 | 22.0000 | 1057.8000 | 1111.2000 | 1089.2000 |
| `benchmark://tensorflow-v0/1500` | cem | 121.4000 | 21.2000 | 100.2000 | 121.4000 | 98.6000 |
| `benchmark://tensorflow-v0/500` | random | 145.0000 | 17.8000 | 145.0000 | 74.6000 | 127.2000 |
| `benchmark://tensorflow-v0/4` | cem | 118.2000 | 12.4000 | 87.2000 | 118.2000 | 105.8000 |
| `benchmark://npb-v0/3` | cem | 360.4000 | 11.2000 | 349.2000 | 360.4000 | 347.6000 |
| `benchmark://mibench-v1/jpeg-c` | contextual_cem | 408.2000 | 7.8000 | 400.4000 | 370.0000 | 408.2000 |
| `benchmark://chstone-v0/blowfish` | contextual_cem | 929.4000 | 7.8000 | 906.2000 | 921.6000 | 929.4000 |
| `benchmark://mibench-v1/mad-1` | contextual_cem | 181.4000 | 7.4000 | 165.0000 | 174.0000 | 181.4000 |
| `benchmark://opencv-v0/4` | contextual_cem | 301.6000 | 3.0000 | 287.2000 | 298.6000 | 301.6000 |
| `benchmark://tensorflow-v0/3` | random | 34.4000 | 3.0000 | 34.4000 | 31.4000 | 31.4000 |
| `benchmark://mibench-v1/lame-psymodel` | random | 910.8000 | 2.6000 | 910.8000 | 908.2000 | 885.0000 |
| `benchmark://tensorflow-v0/25` | cem | 19.8000 | 1.4000 | 18.4000 | 19.8000 | 17.8000 |
| `benchmark://mibench-v1/lame-newmdct-1` | cem | 242.4000 | 1.2000 | 241.2000 | 242.4000 | 240.6000 |
| `benchmark://opencv-v0/50` | random | 137.6000 | 1.2000 | 137.6000 | 135.4000 | 136.4000 |
| `benchmark://mibench-v1/lame-takehiro-1` | cem | 227.0000 | 1.0000 | 212.0000 | 227.0000 | 226.0000 |
| `benchmark://opencv-v0/442` | contextual_cem | 28.6000 | 1.0000 | 27.6000 | 25.6000 | 28.6000 |
| `benchmark://npb-v0/122` | contextual_cem | 128.8000 | 0.8000 | 127.6000 | 128.0000 | 128.8000 |
| `benchmark://opencv-v0/150` | random,contextual_cem | 1.0000 | 0.4000 | 1.0000 | 0.6000 | 1.0000 |

## Individual Runs

| Strategy | Seed | Avg improvement | Improved | Oz beaten | Avg best vs Oz | Min | Max | Errors | Oz errors |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| cem | 7 | 684.5333 | 29 | 5 | -891.0333 | 0.0000 | 8121.0000 | 0 | 0 |
| cem | 11 | 532.6333 | 29 | 5 | -1042.9333 | 0.0000 | 1993.0000 | 0 | 0 |
| cem | 17 | 746.3000 | 29 | 6 | -829.2667 | 0.0000 | 8181.0000 | 0 | 0 |
| cem | 23 | 840.9667 | 30 | 7 | -734.6000 | 1.0000 | 10731.0000 | 0 | 0 |
| cem | 31 | 931.6000 | 30 | 4 | -643.9667 | 1.0000 | 11357.0000 | 0 | 0 |
| contextual_cem | 7 | 712.9333 | 30 | 4 | -862.6333 | 1.0000 | 8105.0000 | 0 | 0 |
| contextual_cem | 11 | 896.8667 | 29 | 4 | -678.7000 | 0.0000 | 12361.0000 | 0 | 0 |
| contextual_cem | 17 | 815.3000 | 29 | 5 | -760.2667 | 0.0000 | 7316.0000 | 0 | 0 |
| contextual_cem | 23 | 855.5667 | 30 | 5 | -720.0000 | 1.0000 | 9233.0000 | 0 | 0 |
| contextual_cem | 31 | 1061.8333 | 30 | 6 | -513.7333 | 1.0000 | 14547.0000 | 0 | 0 |
| random | 7 | 914.8333 | 30 | 5 | -660.7333 | 1.0000 | 13410.0000 | 0 | 0 |
| random | 11 | 488.6000 | 30 | 4 | -1086.9667 | 2.0000 | 1805.0000 | 0 | 0 |
| random | 17 | 729.9000 | 29 | 4 | -845.6667 | 0.0000 | 8252.0000 | 0 | 0 |
| random | 23 | 699.3000 | 30 | 5 | -876.2667 | 1.0000 | 7014.0000 | 0 | 0 |
| random | 31 | 878.7000 | 29 | 3 | -696.8667 | 0.0000 | 11357.0000 | 0 | 0 |
