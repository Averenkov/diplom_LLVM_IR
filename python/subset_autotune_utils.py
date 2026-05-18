"""Shared helpers for subset autotuning experiments."""

from __future__ import annotations

import csv
import json
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from compile_gym_bridge import run_pass, write_bitcode


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def make_output_dir(raw: str) -> Path:
    out_dir = Path(raw) if raw else Path("experiments") / "runs" / utc_timestamp()
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir


def load_rows(path: Path, sort_by: str, limit: int) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as inp:
        rows = list(csv.DictReader(inp))
    rows.sort(key=lambda row: float(row.get(sort_by) or 0), reverse=True)
    return rows[:limit] if limit else rows


def lookup_objective(payload: dict[str, Any], objective: str) -> float:
    if objective in payload:
        return float(payload[objective])
    tu_metrics = payload.get("translation_unit_aggregation", {})
    if objective in tu_metrics:
        return float(tu_metrics[objective])
    raise KeyError(objective)


def evaluate(
    env: Any,
    benchmark_uri: str,
    actions: list[int],
    opt_bin: str,
    plugin_path: Path,
    fraction: float,
) -> dict[str, Any]:
    env.reset(benchmark=benchmark_uri)
    if actions:
        env.multistep(actions)
    bitcode = env.observation["Bitcode"]
    with tempfile.TemporaryDirectory(prefix="subset_autotune_") as tmpdir:
        workdir = Path(tmpdir)
        bitcode_path = write_bitcode(bitcode, workdir)
        output_path = workdir / "top20.json"
        run_pass(opt_bin, plugin_path, bitcode_path, output_path, fraction)
        payload = json.loads(output_path.read_text(encoding="utf-8"))
    payload["benchmark"] = benchmark_uri
    payload["actions"] = actions
    return payload


def evaluate_opt_level(
    env: Any,
    benchmark_uri: str,
    opt_bin: str,
    plugin_path: Path,
    fraction: float,
    opt_level: str,
) -> dict[str, Any]:
    env.reset(benchmark=benchmark_uri)
    bitcode = env.observation["Bitcode"]
    with tempfile.TemporaryDirectory(prefix="subset_autotune_") as tmpdir:
        workdir = Path(tmpdir)
        bitcode_path = write_bitcode(bitcode, workdir)
        optimized_path = workdir / "optimized.bc"
        subprocess.run(
            [opt_bin, opt_level, "-o", str(optimized_path), str(bitcode_path)],
            check=True,
        )
        output_path = workdir / "top20.json"
        run_pass(opt_bin, plugin_path, optimized_path, output_path, fraction)
        payload = json.loads(output_path.read_text(encoding="utf-8"))
    payload["benchmark"] = benchmark_uri
    payload["actions"] = []
    payload["opt_level"] = opt_level
    return payload


def summarize_payload(payload: dict[str, Any], objective: str) -> dict[str, Any]:
    tu_metrics = payload.get("translation_unit_aggregation", {})
    return {
        "objective_value": lookup_objective(payload, objective),
        "functions_defined": payload.get("functions_defined"),
        "total_ir_insts": payload.get("total_ir_insts"),
        "selected_share_percent": payload.get("selected_share_percent"),
        "size_gini": tu_metrics.get("size_gini"),
        "size_concentration_hhi": tu_metrics.get("size_concentration_hhi"),
    }


def function_instruction_deltas(
    baseline_payload: dict[str, Any] | None,
    candidate_payload: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    if not baseline_payload or not candidate_payload:
        return []

    candidate_counts = {
        item["name"]: item
        for item in candidate_payload.get("function_instruction_counts", [])
    }
    rows = []
    for item in baseline_payload.get("top_functions", []):
        name = item["name"]
        baseline_count = int(item.get("instruction_count") or 0)
        candidate_item = candidate_counts.get(name)
        candidate_count = (
            int(candidate_item.get("instruction_count") or 0)
            if candidate_item
            else None
        )
        delta = (
            baseline_count - candidate_count
            if candidate_count is not None
            else None
        )
        rows.append(
            {
                "name": name,
                "baseline_rank": item.get("rank"),
                "candidate_rank": candidate_item.get("rank")
                if candidate_item
                else None,
                "baseline_instruction_count": baseline_count,
                "candidate_instruction_count": candidate_count,
                "instruction_delta": delta,
            }
        )
    return rows


def summarize_function_deltas(rows: list[dict[str, Any]]) -> dict[str, Any]:
    matched = [row for row in rows if row["candidate_instruction_count"] is not None]
    deltas = [int(row["instruction_delta"]) for row in matched]
    return {
        "function_count": len(rows),
        "matched_function_count": len(matched),
        "missing_function_count": len(rows) - len(matched),
        "baseline_instruction_count": sum(
            int(row["baseline_instruction_count"]) for row in rows
        ),
        "candidate_instruction_count": sum(
            int(row["candidate_instruction_count"]) for row in matched
        ),
        "instruction_delta": sum(deltas),
    }


def make_benchmark_context(
    row: dict[str, str],
    baseline_summary: dict[str, Any],
) -> dict[str, Any]:
    return {
        "suite": row.get("suite", ""),
        "functions_defined": baseline_summary.get("functions_defined") or 0,
        "total_ir_insts": baseline_summary.get("total_ir_insts") or 0,
        "selected_share_percent": baseline_summary.get("selected_share_percent") or 0.0,
        "size_gini": baseline_summary.get("size_gini") or 0.0,
        "size_concentration_hhi": baseline_summary.get("size_concentration_hhi")
        or 0.0,
    }


def write_report(out_dir: Path, report: dict[str, Any]) -> None:
    (out_dir / "subset_autotune.json").write_text(
        json.dumps(report, indent=2, sort_keys=False) + "\n",
        encoding="utf-8",
    )

    with (out_dir / "subset_autotune_summary.csv").open(
        "w", newline="", encoding="utf-8"
    ) as out:
        writer = csv.DictWriter(
            out,
            fieldnames=[
                "suite",
                "benchmark_uri",
                "baseline_objective",
                "best_trial",
                "best_kind",
                "best_objective",
                "improvement",
                "selected_function_instruction_delta",
                "oz_objective",
                "best_vs_oz",
                "oz_selected_function_instruction_delta",
                "oz_error",
            ],
        )
        writer.writeheader()
        for item in report["results"]:
            writer.writerow({key: item.get(key, "") for key in writer.fieldnames})

    with (out_dir / "subset_function_deltas.csv").open(
        "w", newline="", encoding="utf-8"
    ) as out:
        fieldnames = [
            "suite",
            "benchmark_uri",
            "comparison",
            "function_name",
            "baseline_rank",
            "candidate_rank",
            "baseline_instruction_count",
            "candidate_instruction_count",
            "instruction_delta",
        ]
        writer = csv.DictWriter(out, fieldnames=fieldnames)
        writer.writeheader()
        for item in report["results"]:
            for comparison, deltas_key in (
                ("best", "best_function_deltas"),
                ("oz", "oz_function_deltas"),
            ):
                for row in item.get(deltas_key, []):
                    writer.writerow(
                        {
                            "suite": item.get("suite", ""),
                            "benchmark_uri": item.get("benchmark_uri", ""),
                            "comparison": comparison,
                            "function_name": row.get("name", ""),
                            "baseline_rank": row.get("baseline_rank", ""),
                            "candidate_rank": row.get("candidate_rank", ""),
                            "baseline_instruction_count": row.get(
                                "baseline_instruction_count", ""
                            ),
                            "candidate_instruction_count": row.get(
                                "candidate_instruction_count", ""
                            ),
                            "instruction_delta": row.get("instruction_delta", ""),
                        }
                    )
