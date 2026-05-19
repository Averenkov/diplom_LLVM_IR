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
    evaluate_opt_level,
    function_instruction_deltas,
    load_rows,
    make_benchmark_context,
    make_output_dir,
    summarize_function_deltas,
    summarize_payload,
    utc_timestamp,
    write_report,
)


DEFAULT_OBJECTIVE = "selected_share_percent"
OBJECTIVE_DIRECTIONS = ("maximize", "minimize")


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
        "--objective-direction",
        default="maximize",
        choices=OBJECTIVE_DIRECTIONS,
        help="Whether larger or smaller objective values are better.",
    )
    parser.add_argument(
        "--strategy",
        default="random",
        choices=(
            "random",
            "model",
            "bandit",
            "contextual",
            "contextual_bandit",
            "cem",
            "contextual_cem",
            "hybrid_cem",
            "hybrid",
        ),
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
        "--context-learning-rate",
        type=float,
        default=0.05,
        help="SGD learning rate for --strategy contextual_bandit.",
    )
    parser.add_argument(
        "--context-l2",
        type=float,
        default=0.001,
        help="L2 regularization for --strategy contextual_bandit.",
    )
    parser.add_argument(
        "--context-suite-buckets",
        type=int,
        default=8,
        help="Number of hashed suite buckets for contextual benchmark features.",
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
        "--hybrid-context-weight",
        type=float,
        default=0.35,
        help="Contextual prior weight for --strategy contextual_cem.",
    )
    parser.add_argument(
        "--semantic-prior-weight",
        type=float,
        default=0.0,
        help=(
            "Rule-based semantic pass prior weight for --strategy contextual_cem. "
            "A value of 0 disables it."
        ),
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


def objective_delta(value: float, reference: float, direction: str) -> float:
    if direction == "maximize":
        return value - reference
    return reference - value


def choose_best(
    evaluations: list[dict],
    direction: str,
) -> dict | None:
    if not evaluations:
        return None
    key = lambda item: item["summary"]["objective_value"]
    if direction == "maximize":
        return max(evaluations, key=key)
    return min(evaluations, key=key)


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
        action_names = list(getattr(env.action_space, "names", []) or [])
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
            context_learning_rate=args.context_learning_rate,
            context_l2=args.context_l2,
            context_suite_buckets=args.context_suite_buckets,
            hybrid_context_weight=args.hybrid_context_weight,
            semantic_prior_weight=args.semantic_prior_weight,
            action_names=action_names,
        )
        for row_index, row in enumerate(rows, start=1):
            benchmark_uri = row["benchmark_uri"]
            evaluations = []
            print(f"[{row_index}/{len(rows)}] {benchmark_uri}", flush=True)
            baseline_score: float | None = None
            benchmark_context = {}
            for trial in range(args.trials + 1):
                if trial == 0:
                    kind = "baseline"
                    actions: list[int] = []
                else:
                    kind, actions = selector.select(trial, benchmark_context)

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
                        benchmark_context = make_benchmark_context(row, summary)
                    elif baseline_score is not None:
                        selector.update(
                            actions,
                            objective_delta(
                                summary["objective_value"],
                                baseline_score,
                                args.objective_direction,
                            ),
                            benchmark_context,
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
            best = choose_best(successful, args.objective_direction)
            baseline = successful[0] if successful else None

            oz_error = ""
            oz_payload = None
            oz_summary = {}
            oz_started = time.perf_counter()
            try:
                oz_payload = evaluate_opt_level(
                    env,
                    benchmark_uri,
                    opt_bin,
                    plugin_path,
                    args.fraction,
                    "-Oz",
                )
                oz_summary = summarize_payload(oz_payload, args.objective)
            except Exception as exc:  # noqa: BLE001
                oz_error = f"{type(exc).__name__}: {exc}"
                print(f"  -Oz ERROR: {oz_error}", flush=True)
            oz_elapsed_sec = time.perf_counter() - oz_started

            improvement = (
                objective_delta(
                    best["summary"]["objective_value"],
                    baseline["summary"]["objective_value"],
                    args.objective_direction,
                )
                if best and baseline
                else None
            )
            oz_objective = oz_summary.get("objective_value")
            best_vs_oz = (
                objective_delta(
                    best["summary"]["objective_value"],
                    oz_objective,
                    args.objective_direction,
                )
                if best and oz_objective is not None
                else None
            )
            print(
                f"  best trial={best['trial']} delta={improvement:.4f}"
                if best and improvement is not None
                else "  no successful trials",
                flush=True,
            )
            if oz_objective is not None and best_vs_oz is not None:
                print(
                    f"  -Oz objective={oz_objective:.4f}, best_vs_oz={best_vs_oz:.4f}",
                    flush=True,
                )
            baseline_payload = baseline["payload"] if baseline else None
            best_payload = best["payload"] if best else None
            best_function_deltas = function_instruction_deltas(
                baseline_payload,
                best_payload,
            )
            oz_function_deltas = function_instruction_deltas(
                baseline_payload,
                oz_payload,
            )
            best_function_delta_summary = summarize_function_deltas(
                best_function_deltas
            )
            oz_function_delta_summary = summarize_function_deltas(oz_function_deltas)
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
                    "selected_function_instruction_delta": (
                        best_function_delta_summary["instruction_delta"]
                    ),
                    "oz_objective": oz_objective,
                    "best_vs_oz": best_vs_oz,
                    "oz_selected_function_instruction_delta": (
                        oz_function_delta_summary["instruction_delta"]
                    ),
                    "best_function_delta_summary": best_function_delta_summary,
                    "best_function_deltas": best_function_deltas,
                    "oz_function_delta_summary": oz_function_delta_summary,
                    "oz_function_deltas": oz_function_deltas,
                    "oz_baseline": {
                        "elapsed_sec": oz_elapsed_sec,
                        "error": oz_error,
                        "summary": oz_summary,
                        "payload": oz_payload,
                    },
                    "benchmark_context": benchmark_context,
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
            "objective_direction": args.objective_direction,
            "sort_by": args.sort_by,
            "strategy": args.strategy,
            "model_warmup": args.model_warmup,
            "model_epsilon": args.model_epsilon,
            "model_ucb": args.model_ucb,
            "context_learning_rate": args.context_learning_rate,
            "context_l2": args.context_l2,
            "context_suite_buckets": args.context_suite_buckets,
            "cem_candidates": args.cem_candidates,
            "cem_elite_size": args.cem_elite_size,
            "cem_smoothing": args.cem_smoothing,
            "cem_min_prob": args.cem_min_prob,
            "hybrid_context_weight": args.hybrid_context_weight,
            "semantic_prior_weight": args.semantic_prior_weight,
        },
        "model": selector.snapshot(),
        "results": results,
    }
    write_report(out_dir, report)

    print(f"Wrote: {out_dir / 'subset_autotune.json'}")
    print(f"Wrote: {out_dir / 'subset_autotune_summary.csv'}")
    print(f"Wrote: {out_dir / 'subset_function_deltas.csv'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
