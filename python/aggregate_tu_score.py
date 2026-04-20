#!/usr/bin/env python3
"""Aggregate function-level scores into a translation-unit score."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Aggregate function-level scores into a translation-unit score "
            "using the weights emitted by Top20BiggestFuncs."
        )
    )
    parser.add_argument(
        "--weights-json",
        required=True,
        help="Path to JSON emitted by the LLVM pass.",
    )
    parser.add_argument(
        "--scores-json",
        required=True,
        help=(
            "Path to JSON with function scores. Expected format: "
            '{"function_scores": [{"name": "...", "score": 0.0}, ...]}'
        ),
    )
    parser.add_argument(
        "--output",
        default="",
        help="Optional path to write aggregated TU JSON.",
    )
    return parser.parse_args()


def load_json(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def extract_weights(weights_payload: dict) -> dict[str, float]:
    top_functions = weights_payload.get("top_functions", [])
    if not top_functions:
        return {}

    if all("selected_weight_percent" in item for item in top_functions):
        return {
            item["name"]: float(item["selected_weight_percent"]) / 100.0
            for item in top_functions
        }

    selected_total = sum(float(item["instruction_count"]) for item in top_functions)
    if selected_total == 0:
        return {}

    return {
        item["name"]: float(item["instruction_count"]) / selected_total
        for item in top_functions
    }


def main() -> int:
    args = parse_args()
    weights_payload = load_json(args.weights_json)
    scores_payload = load_json(args.scores_json)

    weights = extract_weights(weights_payload)
    scores = {
        item["name"]: float(item["score"])
        for item in scores_payload.get("function_scores", [])
    }

    matched = []
    missing = []
    tu_score = 0.0

    for name, weight in weights.items():
        if name not in scores:
            missing.append(name)
            continue
        contribution = weight * scores[name]
        matched.append(
            {
                "name": name,
                "score": scores[name],
                "weight": weight,
                "weighted_contribution": contribution,
            }
        )
        tu_score += contribution

    result = {
        "aggregation_scope": "translation_unit",
        "aggregation_method": "weighted-sum-over-selected-functions",
        "weights_source": str(Path(args.weights_json).resolve()),
        "scores_source": str(Path(args.scores_json).resolve()),
        "translation_unit_score": tu_score,
        "matched_function_count": len(matched),
        "missing_function_count": len(missing),
        "matched_functions": matched,
        "missing_functions": missing,
    }

    rendered = json.dumps(result, indent=2, sort_keys=False)
    if args.output:
      Path(args.output).write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0


if __name__ == "__main__":
    sys.exit(main())
