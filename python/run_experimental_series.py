#!/usr/bin/env python3
"""Run a reproducible CompilerGym experiment series over TU-level metrics."""

from __future__ import annotations

import argparse
import csv
import json
import platform
import random
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from autotune_tu import lookup_objective
from compile_gym_bridge import (
    analyze_benchmark,
    build_plugin,
    configure_compiler_gym_dirs,
    configure_runtime_library_path,
    ensure_compiler_gym,
)


DEFAULT_BENCHMARKS = (
    "cbench-v1/qsort",
    "cbench-v1/dijkstra",
    "cbench-v1/stringsearch",
    "cbench-v1/rijndael",
)

DEFAULT_OBJECTIVES = (
    "selected_ir_share_percent",
    "dominant_function_share_percent",
    "top_3_share_percent",
    "top_5_share_percent",
    "size_concentration_hhi",
    "size_gini",
)

SUMMARY_FIELDS = (
    "benchmark",
    "trial",
    "kind",
    "status",
    "elapsed_sec",
    "actions",
    "functions_defined",
    "total_ir_insts",
    "selected_count",
    "selected_ir_insts",
    "selected_share_percent",
    "dominant_function_share_percent",
    "top_3_share_percent",
    "top_5_share_percent",
    "mean_function_size",
    "median_function_size",
    "stddev_function_size",
    "size_concentration_hhi",
    "size_gini",
    "error",
)


def parse_csv(raw: str) -> list[str]:
    return [item.strip() for item in raw.split(",") if item.strip()]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run baseline and random pass-sequence experiments for several "
            "CompilerGym benchmarks, then summarize TU-level aggregation metrics."
        )
    )
    parser.add_argument(
        "--benchmarks",
        default=",".join(DEFAULT_BENCHMARKS),
        help="Comma-separated CompilerGym benchmark URIs.",
    )
    parser.add_argument(
        "--env",
        default="llvm-v0",
        help="CompilerGym environment id (default: %(default)s).",
    )
    parser.add_argument(
        "--trials",
        type=int,
        default=12,
        help="Number of random sequences per benchmark (default: %(default)s).",
    )
    parser.add_argument(
        "--steps",
        type=int,
        default=8,
        help="Length of each random optimization sequence (default: %(default)s).",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=7,
        help="Base random seed (default: %(default)s).",
    )
    parser.add_argument(
        "--fraction",
        type=float,
        default=0.20,
        help="Fraction of largest functions selected by the pass.",
    )
    parser.add_argument(
        "--objectives",
        default=",".join(DEFAULT_OBJECTIVES),
        help="Comma-separated objective metric names for ranking.",
    )
    parser.add_argument(
        "--cpp-dir",
        default=str(Path(__file__).resolve().parents[1] / "cpp"),
        help="Path to the C++ pass directory.",
    )
    parser.add_argument(
        "--output-dir",
        default="",
        help=(
            "Directory for results. Defaults to experiments/runs/"
            "<UTC timestamp>."
        ),
    )
    parser.add_argument(
        "--fail-fast",
        action="store_true",
        help="Stop at the first failed benchmark evaluation.",
    )
    parser.add_argument(
        "--no-baseline",
        action="store_true",
        help="Skip the zero-action baseline for each benchmark.",
    )
    return parser.parse_args()


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def make_output_dir(raw: str) -> Path:
    if raw:
        out_dir = Path(raw)
    else:
        out_dir = Path(__file__).resolve().parents[1] / "experiments" / "runs" / utc_timestamp()
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir


def collect_environment(project_root: Path, env_name: str) -> dict[str, Any]:
    configure_compiler_gym_dirs(project_root)
    configure_runtime_library_path()
    compiler_gym = ensure_compiler_gym()
    return {
        "python": sys.version.split()[0],
        "python_executable": sys.executable,
        "platform": platform.platform(),
        "compiler_gym_version": getattr(compiler_gym, "__version__", "unknown"),
        "compiler_gym_env": env_name,
    }


def sample_sequences(
    compiler_gym: Any,
    benchmark: str,
    env_name: str,
    trials: int,
    steps: int,
    seed: int,
) -> list[list[int]]:
    rng = random.Random(seed)
    with compiler_gym.make(env_name, benchmark=benchmark) as env:
        env.reset()
        action_count = env.action_space.n
    return [[rng.randrange(action_count) for _ in range(steps)] for _ in range(trials)]


def flatten_payload(
    benchmark: str,
    trial: int,
    kind: str,
    actions: list[int],
    payload: dict[str, Any] | None,
    elapsed_sec: float,
    error: str = "",
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "benchmark": benchmark,
        "trial": trial,
        "kind": kind,
        "status": "ok" if payload is not None else "error",
        "elapsed_sec": round(elapsed_sec, 6),
        "actions": ",".join(str(action) for action in actions),
        "error": error,
    }

    if payload is None:
        return row

    tu_metrics = payload.get("translation_unit_aggregation", {})
    row.update(
        {
            "functions_defined": payload.get("functions_defined"),
            "total_ir_insts": payload.get("total_ir_insts"),
            "selected_count": payload.get("selected_count"),
            "selected_ir_insts": payload.get("selected_ir_insts"),
            "selected_share_percent": payload.get("selected_share_percent"),
            "dominant_function_share_percent": tu_metrics.get(
                "dominant_function_share_percent"
            ),
            "top_3_share_percent": tu_metrics.get("top_3_share_percent"),
            "top_5_share_percent": tu_metrics.get("top_5_share_percent"),
            "mean_function_size": tu_metrics.get("mean_function_size"),
            "median_function_size": tu_metrics.get("median_function_size"),
            "stddev_function_size": tu_metrics.get("stddev_function_size"),
            "size_concentration_hhi": tu_metrics.get("size_concentration_hhi"),
            "size_gini": tu_metrics.get("size_gini"),
        }
    )
    return row


def evaluate_one(
    benchmark: str,
    env_name: str,
    actions: list[int],
    fraction: float,
    cpp_dir: Path,
) -> tuple[dict[str, Any] | None, float, str]:
    started = time.perf_counter()
    try:
        payload = analyze_benchmark(
            benchmark=benchmark,
            env_name=env_name,
            actions=actions,
            fraction=fraction,
            cpp_dir=cpp_dir,
            output_path=None,
            rebuild_plugin=False,
        )
        return payload, time.perf_counter() - started, ""
    except Exception as exc:  # noqa: BLE001 - keep the series report complete.
        return None, time.perf_counter() - started, f"{type(exc).__name__}: {exc}"


def rank_results(
    evaluations: list[dict[str, Any]],
    objectives: list[str],
) -> dict[str, list[dict[str, Any]]]:
    rankings: dict[str, list[dict[str, Any]]] = {}
    successful = [item for item in evaluations if item.get("payload") is not None]

    for objective in objectives:
        ranked = []
        for item in successful:
            try:
                value = lookup_objective(item["payload"], objective)
            except (KeyError, TypeError, ValueError):
                continue
            ranked.append(
                {
                    "benchmark": item["benchmark"],
                    "trial": item["trial"],
                    "kind": item["kind"],
                    "objective": objective,
                    "objective_value": value,
                    "actions": item["actions"],
                }
            )
        rankings[objective] = sorted(
            ranked,
            key=lambda item: item["objective_value"],
            reverse=True,
        )
    return rankings


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as out:
        writer = csv.DictWriter(out, fieldnames=SUMMARY_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in SUMMARY_FIELDS})


def append_benchmark_error(
    evaluations: list[dict[str, Any]],
    summary_rows: list[dict[str, Any]],
    benchmark: str,
    error: str,
) -> None:
    evaluations.append(
        {
            "benchmark": benchmark,
            "trial": -1,
            "kind": "setup",
            "actions": [],
            "elapsed_sec": 0.0,
            "error": error,
            "payload": None,
        }
    )
    summary_rows.append(
        flatten_payload(
            benchmark=benchmark,
            trial=-1,
            kind="setup",
            actions=[],
            payload=None,
            elapsed_sec=0.0,
            error=error,
        )
    )


def main() -> int:
    args = parse_args()
    benchmarks = parse_csv(args.benchmarks)
    objectives = parse_csv(args.objectives)
    cpp_dir = Path(args.cpp_dir).resolve()
    project_root = cpp_dir.parent
    out_dir = make_output_dir(args.output_dir)

    environment = collect_environment(project_root, args.env)
    compiler_gym = ensure_compiler_gym()
    build_plugin(cpp_dir)

    evaluations: list[dict[str, Any]] = []
    summary_rows: list[dict[str, Any]] = []

    for bench_index, benchmark in enumerate(benchmarks):
        benchmark_seed = args.seed + bench_index
        try:
            sequences = sample_sequences(
                compiler_gym=compiler_gym,
                benchmark=benchmark,
                env_name=args.env,
                trials=args.trials,
                steps=args.steps,
                seed=benchmark_seed,
            )
        except Exception as exc:  # noqa: BLE001 - keep a diagnostic artifact.
            error = f"{type(exc).__name__}: {exc}"
            print(f"[{benchmark}] setup ERROR: {error}", flush=True)
            append_benchmark_error(evaluations, summary_rows, benchmark, error)
            if args.fail_fast:
                break
            continue

        if not args.no_baseline:
            sequences = [[]] + sequences

        for trial, actions in enumerate(sequences):
            kind = "baseline" if not actions else "random"
            print(
                f"[{benchmark}] trial={trial} kind={kind} actions={actions}",
                flush=True,
            )
            payload, elapsed_sec, error = evaluate_one(
                benchmark=benchmark,
                env_name=args.env,
                actions=actions,
                fraction=args.fraction,
                cpp_dir=cpp_dir,
            )
            evaluations.append(
                {
                    "benchmark": benchmark,
                    "trial": trial,
                    "kind": kind,
                    "actions": actions,
                    "elapsed_sec": elapsed_sec,
                    "error": error,
                    "payload": payload,
                }
            )
            summary_rows.append(
                flatten_payload(
                    benchmark=benchmark,
                    trial=trial,
                    kind=kind,
                    actions=actions,
                    payload=payload,
                    elapsed_sec=elapsed_sec,
                    error=error,
                )
            )
            if error:
                print(f"  ERROR: {error}", flush=True)
                if args.fail_fast:
                    break
        if args.fail_fast and evaluations and evaluations[-1]["error"]:
            break

    rankings = rank_results(evaluations, objectives)
    successful_count = sum(1 for item in evaluations if item["payload"] is not None)
    result = {
        "created_at_utc": utc_timestamp(),
        "environment": environment,
        "config": {
            "benchmarks": benchmarks,
            "objectives": objectives,
            "trials": args.trials,
            "steps": args.steps,
            "seed": args.seed,
            "fraction": args.fraction,
            "cpp_dir": str(cpp_dir),
            "include_baseline": not args.no_baseline,
        },
        "successful_evaluations": successful_count,
        "failed_evaluations": len(evaluations) - successful_count,
        "rankings": rankings,
        "evaluations": evaluations,
    }

    (out_dir / "series.json").write_text(
        json.dumps(result, indent=2, sort_keys=False) + "\n",
        encoding="utf-8",
    )
    write_csv(out_dir / "summary.csv", summary_rows)
    (out_dir / "rankings.json").write_text(
        json.dumps(rankings, indent=2, sort_keys=False) + "\n",
        encoding="utf-8",
    )

    print(f"\nWrote: {out_dir / 'series.json'}")
    print(f"Wrote: {out_dir / 'summary.csv'}")
    print(f"Wrote: {out_dir / 'rankings.json'}")

    return 0 if successful_count else 1


if __name__ == "__main__":
    sys.exit(main())
