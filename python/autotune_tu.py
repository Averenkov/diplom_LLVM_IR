#!/usr/bin/env python3
"""Simple autotuning loop over CompilerGym using TU-level aggregation."""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path
from typing import Any

from compile_gym_bridge import (
    analyze_benchmark,
    configure_compiler_gym_dirs,
    configure_runtime_library_path,
    ensure_compiler_gym,
)


DEFAULT_OBJECTIVE = "selected_ir_share_percent"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Sample optimization sequences in CompilerGym and rank them "
            "using a translation-unit metric emitted by the LLVM pass."
        )
    )
    parser.add_argument(
        "--benchmark",
        default="cbench-v1/qsort",
        help="CompilerGym benchmark URI (default: %(default)s)",
    )
    parser.add_argument(
        "--env",
        default="llvm-v0",
        help="CompilerGym environment id (default: %(default)s)",
    )
    parser.add_argument(
        "--trials",
        type=int,
        default=8,
        help="Number of sampled optimization sequences (default: %(default)s)",
    )
    parser.add_argument(
        "--steps",
        type=int,
        default=6,
        help="Length of each optimization sequence (default: %(default)s)",
    )
    parser.add_argument(
        "--fraction",
        type=float,
        default=0.20,
        help="Fraction of largest functions to select (default: %(default)s)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=7,
        help="Random seed for reproducible sampling (default: %(default)s)",
    )
    parser.add_argument(
        "--objective",
        default=DEFAULT_OBJECTIVE,
        help=(
            "TU metric to maximize. Supported top-level metrics include "
            "`selected_ir_share_percent`, and nested TU metrics include "
            "`dominant_function_share_percent`, `top_3_share_percent`, "
            "`top_5_share_percent`, `size_concentration_hhi`, `size_gini`."
        ),
    )
    parser.add_argument(
        "--cpp-dir",
        default=str(Path(__file__).resolve().parents[1] / "cpp"),
        help="Path to the C++ pass directory (default: %(default)s)",
    )
    parser.add_argument(
        "--output",
        default="",
        help="Optional path to write autotuning results JSON.",
    )
    return parser.parse_args()


def lookup_objective(payload: dict[str, Any], objective: str) -> float:
    if objective in payload:
        return float(payload[objective])

    tu_metrics = payload.get("translation_unit_aggregation", {})
    if objective in tu_metrics:
        return float(tu_metrics[objective])

    available = sorted(set(payload.keys()) | set(tu_metrics.keys()))
    raise KeyError(
        f"Unknown objective '{objective}'. Available metrics: {', '.join(available)}"
    )


def sample_action_sequences(
    benchmark: str,
    env_name: str,
    trials: int,
    steps: int,
    seed: int,
    cpp_dir: Path,
) -> list[list[int]]:
    project_root = cpp_dir.resolve().parent
    configure_compiler_gym_dirs(project_root)
    configure_runtime_library_path()
    compiler_gym = ensure_compiler_gym()
    rng = random.Random(seed)

    with compiler_gym.make(env_name, benchmark=benchmark) as env:
        env.reset()
        action_count = env.action_space.n

    sequences = []
    for _ in range(trials):
        sequences.append([rng.randrange(action_count) for _ in range(steps)])
    return sequences


def main() -> int:
    args = parse_args()
    cpp_dir = Path(args.cpp_dir)
    sequences = sample_action_sequences(
        benchmark=args.benchmark,
        env_name=args.env,
        trials=args.trials,
        steps=args.steps,
        seed=args.seed,
        cpp_dir=cpp_dir,
    )

    evaluations = []
    best_payload: dict[str, Any] | None = None
    best_score: float | None = None

    for trial_id, actions in enumerate(sequences, start=1):
        payload = analyze_benchmark(
            benchmark=args.benchmark,
            env_name=args.env,
            actions=actions,
            fraction=args.fraction,
            cpp_dir=cpp_dir,
            output_path=None,
        )
        score = lookup_objective(payload, args.objective)
        evaluations.append(
            {
                "trial": trial_id,
                "objective": args.objective,
                "objective_value": score,
                "actions": actions,
                "summary": {
                    "selected_share_percent": payload["selected_share_percent"],
                    "translation_unit_aggregation": payload[
                        "translation_unit_aggregation"
                    ],
                },
            }
        )

        if best_score is None or score > best_score:
            best_score = score
            best_payload = payload

    result = {
        "benchmark": args.benchmark,
        "compiler_gym_env": args.env,
        "objective": args.objective,
        "trials": args.trials,
        "steps": args.steps,
        "seed": args.seed,
        "best_objective_value": best_score,
        "best_actions": best_payload["actions"] if best_payload else [],
        "best_payload": best_payload,
        "evaluations": evaluations,
    }

    rendered = json.dumps(result, indent=2, sort_keys=False)
    if args.output:
        Path(args.output).write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0


if __name__ == "__main__":
    sys.exit(main())
