"""Pass-sequence selection models for CompilerGym autotuning."""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Any, Protocol


def clamp(raw: float, lower: float, upper: float) -> float:
    return min(upper, max(lower, raw))


def random_sequence(rng: random.Random, action_count: int, steps: int) -> list[int]:
    return [rng.randrange(action_count) for _ in range(steps)]


class PassSelector(Protocol):
    def select(self, trial: int) -> tuple[str, list[int]]:
        """Return a trial kind label and a sequence of action ids."""

    def update(self, actions: list[int], reward: float) -> None:
        """Update the selector after a successful sequence evaluation."""

    def snapshot(self, top_n: int = 20) -> dict[str, Any]:
        """Return a JSON-serializable model summary."""


@dataclass
class RandomPassSelector:
    action_count: int
    steps: int
    rng: random.Random

    def select(self, trial: int) -> tuple[str, list[int]]:
        return "random", random_sequence(self.rng, self.action_count, self.steps)

    def update(self, actions: list[int], reward: float) -> None:
        return None

    def snapshot(self, top_n: int = 20) -> dict[str, Any]:
        return {"type": "random"}


@dataclass
class BanditPassSelector:
    """Online action-value model with epsilon-greedy UCB exploration."""

    action_count: int
    steps: int
    rng: random.Random
    warmup: int
    epsilon: float
    ucb: float
    counts: list[int] = field(init=False)
    values: list[float] = field(init=False)
    total_updates: int = 0

    def __post_init__(self) -> None:
        self.warmup = max(0, self.warmup)
        self.epsilon = clamp(self.epsilon, 0.0, 1.0)
        self.ucb = max(0.0, self.ucb)
        self.counts = [0 for _ in range(self.action_count)]
        self.values = [0.0 for _ in range(self.action_count)]

    def select(self, trial: int) -> tuple[str, list[int]]:
        if trial <= self.warmup:
            return "random", random_sequence(self.rng, self.action_count, self.steps)
        return "bandit", [self._choose_action() for _ in range(self.steps)]

    def _choose_action(self) -> int:
        if self.rng.random() < self.epsilon:
            return self.rng.randrange(self.action_count)

        log_total = math.log(self.total_updates + 2)
        best_score: float | None = None
        best_actions: list[int] = []
        for action in range(self.action_count):
            count = self.counts[action]
            exploration = self.ucb * math.sqrt(log_total / (count + 1))
            score = self.values[action] + exploration
            if best_score is None or score > best_score:
                best_score = score
                best_actions = [action]
            elif score == best_score:
                best_actions.append(action)
        return self.rng.choice(best_actions)

    def update(self, actions: list[int], reward: float) -> None:
        for action in actions:
            self.total_updates += 1
            self.counts[action] += 1
            count = self.counts[action]
            self.values[action] += (reward - self.values[action]) / count

    def snapshot(self, top_n: int = 20) -> dict[str, Any]:
        observed = [action for action in range(self.action_count) if self.counts[action]]
        ranked = sorted(
            observed,
            key=lambda action: (self.values[action], self.counts[action]),
            reverse=True,
        )
        return {
            "type": "epsilon_greedy_ucb_action_value",
            "warmup": self.warmup,
            "epsilon": self.epsilon,
            "ucb": self.ucb,
            "total_updates": self.total_updates,
            "top_actions": [
                {
                    "action": action,
                    "count": self.counts[action],
                    "value": self.values[action],
                }
                for action in ranked[:top_n]
            ],
        }


@dataclass
class Outcome:
    actions: list[int]
    reward: float


@dataclass
class CrossEntropyPassSelector:
    """Cross-Entropy Method sequence model.

    The model keeps a categorical distribution for each sequence position.
    After every successful trial it rebuilds the distribution from elite
    sequences, then samples candidate sequences from the learned distribution.
    """

    action_count: int
    steps: int
    rng: random.Random
    warmup: int
    epsilon: float
    candidate_count: int
    elite_size: int
    smoothing: float
    min_prob: float
    outcomes: list[Outcome] = field(default_factory=list)
    probabilities: list[list[float]] = field(init=False)

    def __post_init__(self) -> None:
        self.warmup = max(0, self.warmup)
        self.epsilon = clamp(self.epsilon, 0.0, 1.0)
        self.candidate_count = max(1, self.candidate_count)
        self.elite_size = max(1, self.elite_size)
        self.smoothing = clamp(self.smoothing, 0.0, 1.0)
        self.min_prob = clamp(self.min_prob, 0.0, 1.0 / self.action_count)
        uniform = 1.0 / self.action_count
        self.probabilities = [
            [uniform for _ in range(self.action_count)] for _ in range(self.steps)
        ]

    def select(self, trial: int) -> tuple[str, list[int]]:
        if trial <= self.warmup or len(self.outcomes) < self.elite_size:
            return "random", random_sequence(self.rng, self.action_count, self.steps)

        candidates = [
            self._sample_from_model() for _ in range(self.candidate_count)
        ]
        best = max(candidates, key=self._sequence_log_probability)
        return "cem", best

    def update(self, actions: list[int], reward: float) -> None:
        if len(actions) != self.steps:
            return
        self.outcomes.append(Outcome(actions=list(actions), reward=reward))
        self._fit_distribution()

    def _fit_distribution(self) -> None:
        elite = sorted(self.outcomes, key=lambda item: item.reward, reverse=True)[
            : self.elite_size
        ]
        prior = 1.0
        floor_mass = self.min_prob * self.action_count
        remaining_mass = max(0.0, 1.0 - floor_mass)

        for position in range(self.steps):
            counts = [prior for _ in range(self.action_count)]
            for item in elite:
                counts[item.actions[position]] += 1.0

            total = sum(counts)
            target = [
                self.min_prob + remaining_mass * (count / total)
                for count in counts
            ]
            blended = [
                (1.0 - self.smoothing) * old + self.smoothing * new
                for old, new in zip(self.probabilities[position], target)
            ]
            self.probabilities[position] = self._normalize(blended)

    def _sample_from_model(self) -> list[int]:
        actions = []
        for position in range(self.steps):
            if self.rng.random() < self.epsilon:
                actions.append(self.rng.randrange(self.action_count))
            else:
                actions.append(self._sample_categorical(self.probabilities[position]))
        return actions

    def _sample_categorical(self, probs: list[float]) -> int:
        needle = self.rng.random()
        cumulative = 0.0
        for action, prob in enumerate(probs):
            cumulative += prob
            if needle <= cumulative:
                return action
        return self.action_count - 1

    def _sequence_log_probability(self, actions: list[int]) -> float:
        return sum(
            math.log(max(self.probabilities[position][action], 1e-12))
            for position, action in enumerate(actions)
        )

    def _normalize(self, probs: list[float]) -> list[float]:
        total = sum(probs)
        if total <= 0.0:
            return [1.0 / self.action_count for _ in range(self.action_count)]
        return [prob / total for prob in probs]

    def snapshot(self, top_n: int = 20) -> dict[str, Any]:
        elite = sorted(self.outcomes, key=lambda item: item.reward, reverse=True)[
            : self.elite_size
        ]
        top_per_position = []
        for position, probs in enumerate(self.probabilities):
            ranked = sorted(
                range(self.action_count),
                key=lambda action: probs[action],
                reverse=True,
            )[:top_n]
            top_per_position.append(
                {
                    "position": position,
                    "top_actions": [
                        {"action": action, "probability": probs[action]}
                        for action in ranked
                    ],
                }
            )

        return {
            "type": "cross_entropy_sequence_model",
            "warmup": self.warmup,
            "epsilon": self.epsilon,
            "candidate_count": self.candidate_count,
            "elite_size": self.elite_size,
            "smoothing": self.smoothing,
            "min_prob": self.min_prob,
            "observations": len(self.outcomes),
            "elite": [
                {"actions": item.actions, "reward": item.reward} for item in elite
            ],
            "positions": top_per_position,
        }


def make_pass_selector(
    strategy: str,
    action_count: int,
    steps: int,
    rng: random.Random,
    warmup: int,
    epsilon: float,
    ucb: float,
    cem_candidates: int,
    cem_elite_size: int,
    cem_smoothing: float,
    cem_min_prob: float,
) -> PassSelector:
    if strategy == "random":
        return RandomPassSelector(action_count=action_count, steps=steps, rng=rng)
    if strategy in {"model", "bandit"}:
        return BanditPassSelector(
            action_count=action_count,
            steps=steps,
            rng=rng,
            warmup=warmup,
            epsilon=epsilon,
            ucb=ucb,
        )
    if strategy == "cem":
        return CrossEntropyPassSelector(
            action_count=action_count,
            steps=steps,
            rng=rng,
            warmup=warmup,
            epsilon=epsilon,
            candidate_count=cem_candidates,
            elite_size=cem_elite_size,
            smoothing=cem_smoothing,
            min_prob=cem_min_prob,
        )
    raise ValueError(f"Unknown pass selection strategy: {strategy}")
