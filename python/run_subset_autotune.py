#!/usr/bin/env python3
"""Run a small autotuning experiment over a benchmark subset."""

from __future__ import annotations

import argparse
import random
import sys
import time
from pathlib import Path

from compile_gym_bridge import (
    build_plugin,
    configure_compiler_gym_dirs,
    configure_runtime_library_path,
    ensure_compiler_gym,
    locate_opt,
    locate_plugin,
)
from pass_selection_models import make_pass_selector
from subset_autotune_utils import (
    evaluate,
    load_rows,
    make_output_dir,
    summarize_payload,
    utc_timestamp,
    write_report,
)


DEFAULT_OBJECTIVE = "selected_share_percent"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Sample optimization sequences for a benchmark subset."
    )
    parser.add_argument(
        "--benchmark-file",
        required=True,
        help="CSV file with `suite` and `benchmark_uri` columns.",
    )
    parser.add_argument("--env", default="llvm-v0")
    parser.add_argument("--trials", type=int, default=3)
    parser.add_argument("--steps", type=int, default=6)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--fraction", type=float, default=0.20)
    parser.add_argument("--objective", default=DEFAULT_OBJECTIVE)
    parser.add_argument(
        "--strategy",
        default="random",
        choices=("random", "model", "bandit", "cem"),
        help="How to choose optimization actions. `model` is an alias for `bandit`.",
    )
    parser.add_argument(
        "--model-warmup",
        type=int,
        default=2,
        help="Random trials per benchmark before model-guided trials.",
    )
    parser.add_argument(
        "--model-epsilon",
        type=float,
        default=0.20,
        help="Exploration probability for --strategy model.",
    )
    parser.add_argument(
        "--model-ucb",
        type=float,
        default=1.0,
        help="UCB exploration weight for --strategy model.",
    )
    parser.add_argument(
        "--cem-candidates",
        type=int,
        default=16,
        help="Candidate sequences sampled by the CEM selector per model trial.",
    )
    parser.add_argument(
        "--cem-elite-size",
        type=int,
        default=5,
        help="Number of best observed sequences used to fit the CEM distribution.",
    )
    parser.add_argument(
        "--cem-smoothing",
        type=float,
        default=0.65,
        help="CEM distribution update rate in [0, 1].",
    )
    parser.add_argument(
        "--cem-min-prob",
        type=float,
        default=0.001,
        help="Minimum probability mass for each action at each CEM position.",
    )
    parser.add_argument(
        "--sort-by",
        default="total_ir_insts",
        choices=("total_ir_insts", "size_gini", "selected_share_percent"),
        help="Column used to choose the top --limit rows from the subset CSV.",
    )
    parser.add_argument(
        "--cpp-dir",
        default=str(Path(__file__).resolve().parents[1] / "cpp"),
    )
    parser.add_argument(
        "--output-dir",
        default="",
        help="Directory for results. Defaults to experiments/runs/<timestamp>.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    rows = load_rows(Path(args.benchmark_file), args.sort_by, args.limit)
    out_dir = make_output_dir(args.output_dir)
    rng = random.Random(args.seed)

    project_root = Path(__file__).resolve().parents[1]
    cpp_dir = Path(args.cpp_dir).resolve()
    configure_compiler_gym_dirs(project_root)
    configure_runtime_library_path()
    compiler_gym = ensure_compiler_gym()

    build_plugin(cpp_dir)
    plugin_path = locate_plugin(cpp_dir)
    opt_bin = locate_opt()

    results = []
    with compiler_gym.make(args.env) as env:
        action_count = env.action_space.n
        selector = make_pass_selector(
            strategy=args.strategy,
            action_count=action_count,
            steps=args.steps,
            rng=rng,
            warmup=args.model_warmup,
            epsilon=args.model_epsilon,
            ucb=args.model_ucb,
            cem_candidates=args.cem_candidates,
            cem_elite_size=args.cem_elite_size,
            cem_smoothing=args.cem_smoothing,
            cem_min_prob=args.cem_min_prob,
        )
        for row_index, row in enumerate(rows, start=1):
            benchmark_uri = row["benchmark_uri"]
            evaluations = []
            print(f"[{row_index}/{len(rows)}] {benchmark_uri}", flush=True)
            baseline_score: float | None = None
            for trial in range(args.trials + 1):
                if trial == 0:
                    kind = "baseline"
                    actions: list[int] = []
                else:
                    kind, actions = selector.select(trial)

                started = time.perf_counter()
                error = ""
                payload = None
                summary = {}
                try:
                    payload = evaluate(
                        env,
                        benchmark_uri,
                        actions,
                        opt_bin,
                        plugin_path,
                        args.fraction,
                    )
                    summary = summarize_payload(payload, args.objective)
                    if trial == 0:
                        baseline_score = summary["objective_value"]
                    elif baseline_score is not None:
                        selector.update(
                            actions,
                            summary["objective_value"] - baseline_score,
                        )
                except Exception as exc:  # noqa: BLE001
                    error = f"{type(exc).__name__}: {exc}"
                    print(f"  trial={trial} ERROR: {error}", flush=True)
                elapsed_sec = time.perf_counter() - started
                evaluations.append(
                    {
                        "trial": trial,
                        "kind": kind,
                        "actions": actions,
                        "elapsed_sec": elapsed_sec,
                        "error": error,
                        "summary": summary,
                        "payload": payload,
                    }
                )

            successful = [item for item in evaluations if item["payload"]]
            best = (
                max(
                    successful,
                    key=lambda item: item["summary"]["objective_value"],
                )
                if successful
                else None
            )
            baseline = successful[0] if successful else None
            improvement = (
                best["summary"]["objective_value"]
                - baseline["summary"]["objective_value"]
                if best and baseline
                else None
            )
            print(
                f"  best trial={best['trial']} delta={improvement:.4f}"
                if best and improvement is not None
                else "  no successful trials",
                flush=True,
            )
            results.append(
                {
                    "suite": row.get("suite", ""),
                    "benchmark_uri": benchmark_uri,
                    "baseline_objective": baseline["summary"]["objective_value"]
                    if baseline
                    else None,
                    "best_trial": best["trial"] if best else None,
                    "best_kind": best["kind"] if best else "",
                    "best_objective": best["summary"]["objective_value"]
                    if best
                    else None,
                    "improvement": improvement,
                    "evaluations": evaluations,
                }
            )

    report = {
        "created_at_utc": utc_timestamp(),
        "benchmark_file": args.benchmark_file,
        "config": {
            "env": args.env,
            "trials": args.trials,
            "steps": args.steps,
            "seed": args.seed,
            "limit": args.limit,
            "fraction": args.fraction,
            "objective": args.objective,
            "sort_by": args.sort_by,
            "strategy": args.strategy,
            "model_warmup": args.model_warmup,
            "model_epsilon": args.model_epsilon,
            "model_ucb": args.model_ucb,
            "cem_candidates": args.cem_candidates,
            "cem_elite_size": args.cem_elite_size,
            "cem_smoothing": args.cem_smoothing,
            "cem_min_prob": args.cem_min_prob,
        },
        "model": selector.snapshot(),
        "results": results,
    }
    write_report(out_dir, report)

    print(f"Wrote: {out_dir / 'subset_autotune.json'}")
    print(f"Wrote: {out_dir / 'subset_autotune_summary.csv'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
