# Experimental Series

This directory stores the reproducible experiment plan for the LLVM IR
translation-unit aggregation prototype.

Generated runs are written to `experiments/runs/<timestamp>/` and ignored by
Git. Each run contains:

- `series.json` - full configuration, environment metadata, raw pass payloads,
  and objective rankings;
- `summary.csv` - tabular metrics for quick analysis;
- `rankings.json` - best sequences for each selected TU-level objective.

## Minimal smoke run

```bash
./.miniforge/envs/cgym-py310/bin/python python/run_experimental_series.py \
  --benchmarks cbench-v1/qsort \
  --trials 2 \
  --steps 3
```

## Main pilot run

```bash
./.miniforge/envs/cgym-py310/bin/python python/run_experimental_series.py \
  --benchmarks cbench-v1/qsort,cbench-v1/dijkstra,cbench-v1/stringsearch,cbench-v1/rijndael \
  --trials 12 \
  --steps 8 \
  --seed 7
```

The first diploma-stage goal is not to prove the final optimization strategy
yet, but to collect comparable metric behavior across several translation
units: baseline versus sampled optimization sequences, then ranking by
concentration and selected-function share metrics.

## Summarize a run

```bash
./.miniforge/envs/cgym-py310/bin/python python/summarize_experiment.py \
  experiments/runs/<timestamp>/series.json \
  --output experiments/runs/<timestamp>/report.md
```
