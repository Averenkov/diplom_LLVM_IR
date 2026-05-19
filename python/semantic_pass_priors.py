"""Rule-based semantic priors over LLVM pass actions."""

from __future__ import annotations

from typing import Any


def clamp(raw: float, lower: float = 0.0, upper: float = 1.0) -> float:
    return min(upper, max(lower, raw))


def semantic_prior_distribution(
    context: dict[str, Any] | None,
    action_names: list[str],
) -> list[float]:
    """Build a probability distribution from top-function semantic features."""

    context = context or {}
    scores = [1.0 for _ in action_names]
    lowered_names = [name.lower() for name in action_names]

    memory = clamp(float(context.get("semantic_memory_density") or 0.0))
    calls = clamp(float(context.get("semantic_call_density") or 0.0))
    branches = clamp(float(context.get("semantic_branch_density") or 0.0))
    cond_branches = clamp(
        float(context.get("semantic_conditional_branch_density") or 0.0)
    )
    phis = clamp(float(context.get("semantic_phi_density") or 0.0))
    allocas = clamp(float(context.get("semantic_alloca_density") or 0.0))
    vectors = clamp(float(context.get("semantic_vector_density") or 0.0))
    floats = clamp(float(context.get("semantic_float_density") or 0.0))
    integers = clamp(float(context.get("semantic_integer_density") or 0.0))
    compares = clamp(float(context.get("semantic_compare_density") or 0.0))
    selects = clamp(float(context.get("semantic_select_density") or 0.0))
    loop_like = clamp(float(context.get("semantic_loop_like_score") or 0.0))
    basic_blocks = clamp(
        float(context.get("semantic_basic_blocks_per_function") or 0.0) / 128.0
    )

    def boost(patterns: tuple[str, ...], amount: float) -> None:
        if amount <= 0.0:
            return
        for index, name in enumerate(lowered_names):
            if any(pattern in name for pattern in patterns):
                scores[index] += amount

    def dampen(patterns: tuple[str, ...], amount: float) -> None:
        if amount <= 0.0:
            return
        factor = max(0.25, 1.0 - amount)
        for index, name in enumerate(lowered_names):
            if any(pattern in name for pattern in patterns):
                scores[index] *= factor

    cleanup_signal = max(memory, branches, cond_branches, compares, selects)
    boost(
        (
            "instcombine",
            "aggressive-instcombine",
            "simplifycfg",
            "early-cse",
            "adce",
            "bdce",
            "dce",
            "globaldce",
            "constprop",
            "constmerge",
        ),
        1.2 + 2.0 * cleanup_signal,
    )

    boost(
        ("sroa", "mem2reg", "dse", "gvn", "newgvn", "licm"),
        0.8 + 3.0 * max(memory, allocas),
    )
    boost(
        ("simplifycfg", "jump-threading", "correlated-propagation", "break-crit"),
        0.8 + 3.0 * max(branches, cond_branches, basic_blocks),
    )
    boost(
        ("functionattrs", "function-attrs", "ipsccp", "called-value", "deadargelim"),
        0.8 + 2.5 * calls,
    )
    boost(
        ("loop-simplify", "lcssa", "indvars", "loop-deletion", "loop-rotate"),
        0.6 + 2.5 * max(loop_like, phis),
    )
    boost(
        ("instcombine", "reassociate", "gvn", "newgvn"),
        0.5 + 2.0 * max(integers, floats, vectors),
    )
    boost(
        ("instcombine", "simplifycfg", "correlated-propagation"),
        0.5 + 2.0 * max(compares, selects),
    )

    # For a size-oriented prior, avoid aggressively expanding code unless
    # runtime experiments prove those actions useful through the learned model.
    dampen(
        ("loop-unroll", "unroll", "slp-vectorizer", "loop-vectorize", "inline"),
        0.35 + 0.35 * max(vectors, calls),
    )

    total = sum(scores)
    if total <= 0.0:
        return [1.0 / len(action_names) for _ in action_names]
    return [score / total for score in scores]


def top_semantic_actions(
    context: dict[str, Any] | None,
    action_names: list[str],
    top_n: int = 20,
) -> list[dict[str, Any]]:
    distribution = semantic_prior_distribution(context, action_names)
    ranked = sorted(
        range(len(action_names)),
        key=lambda action: distribution[action],
        reverse=True,
    )[:top_n]
    return [
        {
            "action": action,
            "name": action_names[action],
            "probability": distribution[action],
        }
        for action in ranked
    ]
