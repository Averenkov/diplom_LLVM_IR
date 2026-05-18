#!/usr/bin/env python3
"""Run and summarize a strategy x seed autotuning sweep."""

from __future__ import annotations

import argparse
import csv
import json
import statistics
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


DEFAULT_STRATEGIES = "random,bandit,contextual_bandit,cem"
DEFAULT_SEEDS = "7,11,17,23,31"


def parse_csv(raw: str) -> list[str]:
    return [item.strip() for item in raw.split(",") if item.strip()]


def parse_int_csv(raw: str) -> list[int]:
    return [int(item) for item in parse_csv(raw)]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run run_subset_autotune.py for multiple strategies and seeds."
    )
    parser.add_argument(
        "--benchmark-file",
        required=True,
        help="CSV file with benchmark_uri rows for run_subset_autotune.py.",
    )
    parser.add_argument("--output-dir", default="experiments/runs/sweep_seed_stability")
    parser.add_argument("--strategies", default=DEFAULT_STRATEGIES)
    parser.add_argument("--seeds", default=DEFAULT_SEEDS)
    parser.add_argument("--env", default="llvm-v0")
    parser.add_argument("--trials", type=int, default=30)
    parser.add_argument("--steps", type=int, default=12)
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--fraction", type=float, default=0.20)
    parser.add_argument("--objective", default="selected_share_percent")
    parser.add_argument("--sort-by", default="total_ir_insts")
    parser.add_argument("--model-warmup", type=int, default=3)
    parser.add_argument("--model-epsilon", type=float, default=0.20)
    parser.add_argument("--model-ucb", type=float, default=1.0)
    parser.add_argument("--context-learning-rate", type=float, default=0.05)
    parser.add_argument("--context-l2", type=float, default=0.001)
    parser.add_argument("--context-suite-buckets", type=int, default=8)
    parser.add_argument("--cem-candidates", type=int, default=32)
    parser.add_argument("--cem-elite-size", type=int, default=5)
    parser.add_argument("--cem-smoothing", type=float, default=0.65)
    parser.add_argument("--cem-min-prob", type=float, default=0.001)
    parser.add_argument(
        "--force",
        action="store_true",
        help="Rerun combinations even if subset_autotune.json already exists.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print commands without running them.",
    )
    return parser.parse_args()


def run_dir_name(strategy: str, seed: int, trials: int, steps: int) -> str:
    return f"{strategy}_seed{seed}_t{trials}_s{steps}"


def build_command(
    args: argparse.Namespace,
    strategy: str,
    seed: int,
    run_dir: Path,
) -> list[str]:
    return [
        sys.executable,
        "python/run_subset_autotune.py",
        "--benchmark-file",
        args.benchmark_file,
        "--env",
        args.env,
        "--strategy",
        strategy,
        "--model-warmup",
        str(args.model_warmup),
        "--model-epsilon",
        str(args.model_epsilon),
        "--model-ucb",
        str(args.model_ucb),
        "--context-learning-rate",
        str(args.context_learning_rate),
        "--context-l2",
        str(args.context_l2),
        "--context-suite-buckets",
        str(args.context_suite_buckets),
        "--cem-candidates",
        str(args.cem_candidates),
        "--cem-elite-size",
        str(args.cem_elite_size),
        "--cem-smoothing",
        str(args.cem_smoothing),
        "--cem-min-prob",
        str(args.cem_min_prob),
        "--trials",
        str(args.trials),
        "--steps",
        str(args.steps),
        "--seed",
        str(seed),
        "--limit",
        str(args.limit),
        "--fraction",
        str(args.fraction),
        "--objective",
        args.objective,
        "--sort-by",
        args.sort_by,
        "--output-dir",
        str(run_dir),
    ]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def as_float(value: Any) -> float:
    return float(value) if value is not None and value != "" else 0.0


def summarize_run(path: Path) -> dict[str, Any]:
    payload = load_json(path)
    config = payload["config"]
    improvements = [as_float(item.get("improvement")) for item in payload["results"]]
    errors = [
        evaluation.get("error", "")
        for item in payload["results"]
        for evaluation in item.get("evaluations", [])
        if evaluation.get("error")
    ]
    return {
        "strategy": config["strategy"],
        "seed": config["seed"],
        "path": str(path),
        "benchmarks": len(payload["results"]),
        "improved": len([value for value in improvements if value > 0]),
        "avg_improvement": statistics.mean(improvements) if improvements else 0.0,
        "median_improvement": statistics.median(improvements) if improvements else 0.0,
        "min_improvement": min(improvements) if improvements else 0.0,
        "max_improvement": max(improvements) if improvements else 0.0,
        "error_count": len(errors),
    }


def aggregate_by_strategy(run_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in run_rows:
        grouped.setdefault(row["strategy"], []).append(row)

    rows = []
    for strategy, items in sorted(grouped.items()):
        avg_values = [as_float(item["avg_improvement"]) for item in items]
        improved_values = [as_float(item["improved"]) for item in items]
        rows.append(
            {
                "strategy": strategy,
                "runs": len(items),
                "avg_improvement_mean": statistics.mean(avg_values)
                if avg_values
                else 0.0,
                "avg_improvement_std": statistics.stdev(avg_values)
                if len(avg_values) >= 2
                else 0.0,
                "avg_improvement_min": min(avg_values) if avg_values else 0.0,
                "avg_improvement_max": max(avg_values) if avg_values else 0.0,
                "improved_mean": statistics.mean(improved_values)
                if improved_values
                else 0.0,
                "total_errors": sum(int(item["error_count"]) for item in items),
                "wins": 0,
            }
        )
    return rows


def compute_wins(result_paths: list[Path]) -> dict[str, int | float]:
    by_case: dict[tuple[int, str], list[tuple[str, float]]] = {}
    for path in result_paths:
        payload = load_json(path)
        strategy = payload["config"]["strategy"]
        seed = int(payload["config"]["seed"])
        for item in payload["results"]:
            key = (seed, item["benchmark_uri"])
            by_case.setdefault(key, []).append((strategy, as_float(item["improvement"])))

    wins: dict[str, float] = {}
    for candidates in by_case.values():
        if not candidates:
            continue
        best_value = max(value for _, value in candidates)
        winners = [strategy for strategy, value in candidates if value == best_value]
        share = 1.0 / len(winners)
        for strategy in winners:
            wins[strategy] = wins.get(strategy, 0) + share
    return {
        strategy: int(value) if float(value).is_integer() else value
        for strategy, value in wins.items()
    }


def aggregate_by_benchmark(
    result_paths: list[Path], strategies: list[str]
) -> list[dict[str, Any]]:
    by_benchmark: dict[str, dict[str, list[tuple[int, float]]]] = {}
    by_seed_case: dict[tuple[str, int], list[tuple[str, float]]] = {}

    for path in result_paths:
        payload = load_json(path)
        strategy = payload["config"]["strategy"]
        seed = int(payload["config"]["seed"])
        for item in payload["results"]:
            benchmark = item["benchmark_uri"]
            improvement = as_float(item.get("improvement"))
            by_benchmark.setdefault(benchmark, {}).setdefault(strategy, []).append(
                (seed, improvement)
            )
            by_seed_case.setdefault((benchmark, seed), []).append((strategy, improvement))

    seed_wins: dict[str, dict[str, float]] = {}
    for (benchmark, _seed), candidates in by_seed_case.items():
        if not candidates:
            continue
        best_value = max(value for _, value in candidates)
        winners = [strategy for strategy, value in candidates if value == best_value]
        share = 1.0 / len(winners)
        bucket = seed_wins.setdefault(benchmark, {})
        for strategy in winners:
            bucket[strategy] = bucket.get(strategy, 0.0) + share

    rows: list[dict[str, Any]] = []
    for benchmark, strategy_items in sorted(by_benchmark.items()):
        strategy_means = {
            strategy: statistics.mean([value for _, value in values])
            for strategy, values in strategy_items.items()
            if values
        }
        ranked_means = sorted(
            strategy_means.items(), key=lambda item: item[1], reverse=True
        )
        best_mean = ranked_means[0][1] if ranked_means else 0.0
        best_strategies = [
            strategy for strategy, value in ranked_means if value == best_mean
        ]
        second_mean = (
            ranked_means[len(best_strategies)][1]
            if len(ranked_means) > len(best_strategies)
            else best_mean
        )

        row: dict[str, Any] = {
            "benchmark_uri": benchmark,
            "best_strategy": ",".join(best_strategies),
            "best_mean": best_mean,
            "best_margin": best_mean - second_mean,
        }
        for strategy in strategies:
            values = [value for _, value in strategy_items.get(strategy, [])]
            wins = seed_wins.get(benchmark, {}).get(strategy, 0.0)
            row[f"{strategy}_runs"] = len(values)
            row[f"{strategy}_mean"] = statistics.mean(values) if values else 0.0
            row[f"{strategy}_std"] = statistics.stdev(values) if len(values) >= 2 else 0.0
            row[f"{strategy}_min"] = min(values) if values else 0.0
            row[f"{strategy}_max"] = max(values) if values else 0.0
            row[f"{strategy}_improved_runs"] = len([value for value in values if value > 0])
            row[f"{strategy}_seed_wins"] = (
                int(wins) if float(wins).is_integer() else wins
            )
        rows.append(row)
    return rows


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as out:
        writer = csv.DictWriter(out, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def fmt(value: Any) -> str:
    return f"{value:.4f}" if isinstance(value, float) else str(value)


def render_report(
    strategy_rows: list[dict[str, Any]],
    run_rows: list[dict[str, Any]],
    benchmark_rows: list[dict[str, Any]],
    strategies: list[str],
    args: argparse.Namespace,
) -> str:
    lines = [
        "# Strategy Seed Stability Sweep",
        "",
        f"- Benchmark file: `{args.benchmark_file}`",
        f"- Strategies: `{args.strategies}`",
        f"- Seeds: `{args.seeds}`",
        f"- Budget: trials={args.trials}, steps={args.steps}, limit={args.limit}",
        "",
        "## Strategy Aggregate",
        "",
        "| Strategy | Runs | Avg mean | Avg std | Avg min | Avg max | Improved mean | Wins | Errors |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in strategy_rows:
        lines.append(
            f"| {row['strategy']} | {row['runs']} | "
            f"{fmt(row['avg_improvement_mean'])} | "
            f"{fmt(row['avg_improvement_std'])} | "
            f"{fmt(row['avg_improvement_min'])} | "
            f"{fmt(row['avg_improvement_max'])} | "
            f"{fmt(row['improved_mean'])} | {row['wins']} | "
            f"{row['total_errors']} |"
        )

    mean_columns = [f"{strategy}_mean" for strategy in strategies]
    lines.extend(
        [
            "",
            "## Per-Benchmark Aggregate",
            "",
            "| Benchmark | Best strategy | Best mean | Margin | "
            + " | ".join(f"{strategy} mean" for strategy in strategies)
            + " |",
            "| --- | --- | ---: | ---: | "
            + " | ".join("---:" for _ in strategies)
            + " |",
        ]
    )
    for row in sorted(
        benchmark_rows, key=lambda item: as_float(item["best_margin"]), reverse=True
    ):
        lines.append(
            f"| `{row['benchmark_uri']}` | {row['best_strategy']} | "
            f"{fmt(row['best_mean'])} | {fmt(row['best_margin'])} | "
            + " | ".join(fmt(row[column]) for column in mean_columns)
            + " |"
        )

    lines.extend(
        [
            "",
            "## Individual Runs",
            "",
            "| Strategy | Seed | Avg improvement | Improved | Min | Max | Errors |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for row in sorted(run_rows, key=lambda item: (item["strategy"], int(item["seed"]))):
        lines.append(
            f"| {row['strategy']} | {row['seed']} | "
            f"{fmt(row['avg_improvement'])} | {row['improved']} | "
            f"{fmt(row['min_improvement'])} | {fmt(row['max_improvement'])} | "
            f"{row['error_count']} |"
        )
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    strategies = parse_csv(args.strategies)
    seeds = parse_int_csv(args.seeds)
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    result_paths: list[Path] = []
    project_root = Path(__file__).resolve().parents[1]
    for strategy in strategies:
        for seed in seeds:
            run_dir = out_dir / run_dir_name(strategy, seed, args.trials, args.steps)
            result_path = run_dir / "subset_autotune.json"
            result_paths.append(result_path)
            cmd = build_command(args, strategy, seed, run_dir)
            print(" ".join(cmd), flush=True)
            if args.dry_run:
                continue
            if result_path.is_file() and not args.force:
                print(f"  skip existing: {result_path}", flush=True)
                continue

            run_dir.mkdir(parents=True, exist_ok=True)
            started = time.perf_counter()
            with (run_dir / "run.log").open("w", encoding="utf-8") as log:
                completed = subprocess.run(
                    cmd,
                    cwd=project_root,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    check=False,
                )
            elapsed = time.perf_counter() - started
            print(
                f"  exit={completed.returncode} elapsed={elapsed:.1f}s "
                f"log={run_dir / 'run.log'}",
                flush=True,
            )
            if completed.returncode != 0:
                raise SystemExit(completed.returncode)

    if args.dry_run:
        return 0

    existing_results = [path for path in result_paths if path.is_file()]
    run_rows = [summarize_run(path) for path in existing_results]
    strategy_rows = aggregate_by_strategy(run_rows)
    benchmark_rows = aggregate_by_benchmark(existing_results, strategies)
    wins = compute_wins(existing_results)
    for row in strategy_rows:
        row["wins"] = wins.get(row["strategy"], 0)

    write_csv(out_dir / "sweep_run_summary.csv", run_rows)
    write_csv(out_dir / "sweep_strategy_summary.csv", strategy_rows)
    write_csv(out_dir / "sweep_benchmark_strategy_summary.csv", benchmark_rows)
    report = render_report(strategy_rows, run_rows, benchmark_rows, strategies, args)
    (out_dir / "sweep_report.md").write_text(report + "\n", encoding="utf-8")
    print(report)
    print(f"\nWrote: {out_dir / 'sweep_run_summary.csv'}")
    print(f"Wrote: {out_dir / 'sweep_strategy_summary.csv'}")
    print(f"Wrote: {out_dir / 'sweep_benchmark_strategy_summary.csv'}")
    print(f"Wrote: {out_dir / 'sweep_report.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
