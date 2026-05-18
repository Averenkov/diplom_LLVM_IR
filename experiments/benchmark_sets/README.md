# Benchmark Sets

`compiler_gym_target_suites.csv` fixes the concrete LLVM benchmark selection for
the next experimental stage.

The selected suites are:

- BLAS: `benchmark://blas-v0`
- CHStone: `benchmark://chstone-v0`
- MiBench: `benchmark://mibench-v1`
- NAS Parallel Benchmarks: `benchmark://npb-v0`
- OpenCV: `benchmark://opencv-v0`
- TensorFlow: `benchmark://tensorflow-v0`

The `compiler_gym_bc_path` column gives the expected CompilerGym dataset-local
`.bc` path. For datasets backed by tar archives, the file appears after the
dataset is installed. CHStone bitcode files are compiled lazily by CompilerGym.

To materialize the selected benchmarks into standalone bitcode files:

```bash
./.miniforge/envs/cgym-py310/bin/python python/materialize_benchmarks.py \
  --benchmark-file experiments/benchmark_sets/compiler_gym_target_suites.csv \
  --output-dir experiments/bitcode
```

To run the local LLVM analysis pass directly over the selected benchmark set:

```bash
./.miniforge/envs/cgym-py310/bin/python python/analyze_benchmark_set.py \
  --benchmark-file experiments/benchmark_sets/compiler_gym_target_suites.csv
```

To summarize the baseline run and derive a multi-function subset:

```bash
./.miniforge/envs/cgym-py310/bin/python python/summarize_benchmark_set.py \
  experiments/runs/<timestamp>/benchmark_set_summary.csv
```

To reproduce the stratified 30-benchmark autotuning subset:

```bash
./.miniforge/envs/cgym-py310/bin/python python/make_stratified_autotune_subset.py \
  experiments/runs/20260426T145536Z/benchmark_set_multifunction.csv \
  --output-csv experiments/benchmark_sets/autotune_stratified_30.csv
```

The generator also writes `autotune_stratified_30.csv.manifest.json` with the
selection quotas, source file, and selected benchmark URIs.
