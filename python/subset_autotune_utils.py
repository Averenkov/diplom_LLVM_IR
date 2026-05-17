"""Shared helpers for subset autotuning experiments."""

from __future__ import annotations

import csv
import json
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
            ],
        )
        writer.writeheader()
        for item in report["results"]:
            writer.writerow({key: item.get(key, "") for key in writer.fieldnames})
