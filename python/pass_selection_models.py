"""Pass-sequence selection models for CompilerGym autotuning."""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Any, Protocol

from semantic_pass_priors import semantic_prior_distribution, top_semantic_actions


def clamp(raw: float, lower: float, upper: float) -> float:
    return min(upper, max(lower, raw))


def random_sequence(rng: random.Random, action_count: int, steps: int) -> list[int]:
    return [rng.randrange(action_count) for _ in range(steps)]


class PassSelector(Protocol):
    def select(
        self,
        trial: int,
        context: dict[str, Any] | None = None,
    ) -> tuple[str, list[int]]:
        """Return a trial kind label and a sequence of action ids."""

    def update(
        self,
        actions: list[int],
        reward: float,
        context: dict[str, Any] | None = None,
    ) -> None:
        """Update the selector after a successful sequence evaluation."""

    def snapshot(self, top_n: int = 20) -> dict[str, Any]:
        """Return a JSON-serializable model summary."""


@dataclass
class RandomPassSelector:
    action_count: int
    steps: int
    rng: random.Random

    def select(
        self,
        trial: int,
        context: dict[str, Any] | None = None,
    ) -> tuple[str, list[int]]:
        return "random", random_sequence(self.rng, self.action_count, self.steps)

    def update(
        self,
        actions: list[int],
        reward: float,
        context: dict[str, Any] | None = None,
    ) -> None:
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

    def select(
        self,
        trial: int,
        context: dict[str, Any] | None = None,
    ) -> tuple[str, list[int]]:
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

    def update(
        self,
        actions: list[int],
        reward: float,
        context: dict[str, Any] | None = None,
    ) -> None:
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
class ContextualLinearBanditPassSelector:
    """Linear contextual bandit over benchmark and sequence-position features."""

    action_count: int
    steps: int
    rng: random.Random
    warmup: int
    epsilon: float
    ucb: float
    learning_rate: float
    l2: float
    suite_buckets: int
    counts: list[int] = field(init=False)
    weights: list[list[float]] = field(init=False)
    squared_gradients: list[list[float]] = field(init=False)
    feature_exposure: list[list[float]] = field(init=False)
    total_updates: int = 0
    reward_count: int = 0
    reward_mean: float = 0.0
    reward_m2: float = 0.0
    feature_names: list[str] = field(init=False)

    def __post_init__(self) -> None:
        self.warmup = max(0, self.warmup)
        self.epsilon = clamp(self.epsilon, 0.0, 1.0)
        self.ucb = max(0.0, self.ucb)
        self.learning_rate = max(0.0, self.learning_rate)
        self.l2 = max(0.0, self.l2)
        self.suite_buckets = max(1, self.suite_buckets)
        self.feature_names = [
            "bias",
            "position",
            "position_squared",
            "log_total_ir",
            "log_functions",
            "selected_share",
            "size_gini",
            "size_hhi",
            "log_total_ir_x_selected_share",
            "log_total_ir_x_gini",
            "selected_share_x_gini",
            "selected_share_x_hhi",
            "semantic_call_density",
            "semantic_memory_density",
            "semantic_branch_density",
            "semantic_conditional_branch_density",
            "semantic_phi_density",
            "semantic_alloca_density",
            "semantic_vector_density",
            "semantic_float_density",
            "semantic_integer_density",
            "semantic_compare_density",
            "semantic_select_density",
            "semantic_basic_blocks_per_function",
            "semantic_loop_like_score",
            "semantic_memory_x_branch",
            "semantic_call_x_branch",
            "semantic_loop_x_memory",
        ] + [f"suite_bucket_{index}" for index in range(self.suite_buckets)]
        self.counts = [0 for _ in range(self.action_count)]
        self.weights = [
            [0.0 for _ in self.feature_names] for _ in range(self.action_count)
        ]
        self.squared_gradients = [
            [0.0 for _ in self.feature_names] for _ in range(self.action_count)
        ]
        self.feature_exposure = [
            [0.0 for _ in self.feature_names] for _ in range(self.action_count)
        ]

    def select(
        self,
        trial: int,
        context: dict[str, Any] | None = None,
    ) -> tuple[str, list[int]]:
        if trial <= self.warmup:
            return "random", random_sequence(self.rng, self.action_count, self.steps)
        return "contextual_bandit", [
            self._choose_action(self._features(context, position))
            for position in range(self.steps)
        ]

    def _choose_action(self, features: list[float]) -> int:
        if self.rng.random() < self.epsilon:
            return self.rng.randrange(self.action_count)

        log_total = math.log(self.total_updates + 2)
        best_score: float | None = None
        best_actions: list[int] = []
        for action in range(self.action_count):
            prediction = self._predict(action, features)
            exploration = self.ucb * math.sqrt(log_total) * self._uncertainty(
                action, features
            )
            score = prediction + exploration
            if best_score is None or score > best_score:
                best_score = score
                best_actions = [action]
            elif score == best_score:
                best_actions.append(action)
        return self.rng.choice(best_actions)

    def update(
        self,
        actions: list[int],
        reward: float,
        context: dict[str, Any] | None = None,
    ) -> None:
        target = self._standardize_reward(reward)
        self._observe_reward(reward)
        for position, action in enumerate(actions):
            features = self._features(context, position)
            self.total_updates += 1
            self.counts[action] += 1
            prediction = self._predict(action, features)
            error = clamp(target - prediction, -5.0, 5.0)
            weights = self.weights[action]
            squared_gradients = self.squared_gradients[action]
            feature_exposure = self.feature_exposure[action]
            for index, feature in enumerate(features):
                feature_exposure[index] += feature * feature
                regularization = self.l2 * weights[index]
                gradient = error * feature - regularization
                squared_gradients[index] += gradient * gradient
                adjusted_lr = self.learning_rate / math.sqrt(
                    squared_gradients[index] + 1e-8
                )
                weights[index] += adjusted_lr * gradient

    def _features(self, context: dict[str, Any] | None, position: int) -> list[float]:
        context = context or {}
        total_ir = float(context.get("total_ir_insts") or 0.0)
        functions = float(context.get("functions_defined") or 0.0)
        selected_share = float(context.get("selected_share_percent") or 0.0) / 100.0
        size_gini = float(context.get("size_gini") or 0.0)
        size_hhi = float(context.get("size_concentration_hhi") or 0.0)
        call_density = float(context.get("semantic_call_density") or 0.0)
        memory_density = float(context.get("semantic_memory_density") or 0.0)
        branch_density = float(context.get("semantic_branch_density") or 0.0)
        conditional_branch_density = float(
            context.get("semantic_conditional_branch_density") or 0.0
        )
        phi_density = float(context.get("semantic_phi_density") or 0.0)
        alloca_density = float(context.get("semantic_alloca_density") or 0.0)
        vector_density = float(context.get("semantic_vector_density") or 0.0)
        float_density = float(context.get("semantic_float_density") or 0.0)
        integer_density = float(context.get("semantic_integer_density") or 0.0)
        compare_density = float(context.get("semantic_compare_density") or 0.0)
        select_density = float(context.get("semantic_select_density") or 0.0)
        basic_blocks_per_function = float(
            context.get("semantic_basic_blocks_per_function") or 0.0
        )
        loop_like_score = float(context.get("semantic_loop_like_score") or 0.0)
        log_total_ir = math.log1p(max(0.0, total_ir)) / 12.0
        log_functions = math.log1p(max(0.0, functions)) / 8.0
        selected_share = clamp(selected_share, 0.0, 1.0)
        size_gini = clamp(size_gini, 0.0, 1.0)
        size_hhi = clamp(size_hhi, 0.0, 1.0)
        call_density = clamp(call_density, 0.0, 1.0)
        memory_density = clamp(memory_density, 0.0, 1.0)
        branch_density = clamp(branch_density, 0.0, 1.0)
        conditional_branch_density = clamp(conditional_branch_density, 0.0, 1.0)
        phi_density = clamp(phi_density, 0.0, 1.0)
        alloca_density = clamp(alloca_density, 0.0, 1.0)
        vector_density = clamp(vector_density, 0.0, 1.0)
        float_density = clamp(float_density, 0.0, 1.0)
        integer_density = clamp(integer_density, 0.0, 1.0)
        compare_density = clamp(compare_density, 0.0, 1.0)
        select_density = clamp(select_density, 0.0, 1.0)
        basic_blocks_per_function = clamp(
            math.log1p(max(0.0, basic_blocks_per_function)) / 8.0,
            0.0,
            1.0,
        )
        loop_like_score = clamp(loop_like_score, 0.0, 1.0)
        position_ratio = position / max(1, self.steps - 1)

        features = [
            1.0,
            position_ratio,
            position_ratio * position_ratio,
            log_total_ir,
            log_functions,
            selected_share,
            size_gini,
            size_hhi,
            log_total_ir * selected_share,
            log_total_ir * size_gini,
            selected_share * size_gini,
            selected_share * size_hhi,
            call_density,
            memory_density,
            branch_density,
            conditional_branch_density,
            phi_density,
            alloca_density,
            vector_density,
            float_density,
            integer_density,
            compare_density,
            select_density,
            basic_blocks_per_function,
            loop_like_score,
            memory_density * branch_density,
            call_density * branch_density,
            loop_like_score * memory_density,
        ]
        suite_bucket = self._suite_bucket(str(context.get("suite", "")))
        features.extend(
            1.0 if index == suite_bucket else 0.0
            for index in range(self.suite_buckets)
        )
        return features

    def _suite_bucket(self, suite: str) -> int:
        value = 0
        for char in suite:
            value = (value * 131 + ord(char)) % 2_147_483_647
        return value % self.suite_buckets

    def _predict(self, action: int, features: list[float]) -> float:
        return sum(
            weight * feature
            for weight, feature in zip(self.weights[action], features)
        )

    def _uncertainty(self, action: int, features: list[float]) -> float:
        exposure = self.feature_exposure[action]
        variance = sum(
            feature * feature / (seen + 1.0 + self.l2)
            for feature, seen in zip(features, exposure)
        )
        return math.sqrt(variance / len(features))

    def _standardize_reward(self, reward: float) -> float:
        if self.reward_count == 0:
            return reward
        if self.reward_count < 2:
            return reward - self.reward_mean
        variance = self.reward_m2 / (self.reward_count - 1)
        if variance <= 1e-12:
            return reward - self.reward_mean
        return (reward - self.reward_mean) / math.sqrt(variance)

    def _observe_reward(self, reward: float) -> None:
        self.reward_count += 1
        delta = reward - self.reward_mean
        self.reward_mean += delta / self.reward_count
        delta2 = reward - self.reward_mean
        self.reward_m2 += delta * delta2

    def snapshot(self, top_n: int = 20) -> dict[str, Any]:
        ranked = sorted(
            range(self.action_count),
            key=lambda action: (self.counts[action], max(self.weights[action])),
            reverse=True,
        )
        return {
            "type": "contextual_linear_bandit",
            "warmup": self.warmup,
            "epsilon": self.epsilon,
            "ucb": self.ucb,
            "learning_rate": self.learning_rate,
            "l2": self.l2,
            "suite_buckets": self.suite_buckets,
            "feature_names": self.feature_names,
            "total_updates": self.total_updates,
            "exploration": "diagonal_contextual_ucb",
            "reward_count": self.reward_count,
            "reward_mean": self.reward_mean,
            "reward_std": math.sqrt(self.reward_m2 / (self.reward_count - 1))
            if self.reward_count >= 2
            else 0.0,
            "top_actions": [
                {
                    "action": action,
                    "count": self.counts[action],
                    "weights": self.weights[action],
                }
                for action in ranked[:top_n]
                if self.counts[action] > 0
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

    def select(
        self,
        trial: int,
        context: dict[str, Any] | None = None,
    ) -> tuple[str, list[int]]:
        if trial <= self.warmup or len(self.outcomes) < self.elite_size:
            return "random", random_sequence(self.rng, self.action_count, self.steps)

        candidates = [
            self._sample_from_model() for _ in range(self.candidate_count)
        ]
        best = max(candidates, key=self._sequence_log_probability)
        return "cem", best

    def update(
        self,
        actions: list[int],
        reward: float,
        context: dict[str, Any] | None = None,
    ) -> None:
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


@dataclass
class ContextualCrossEntropyPassSelector:
    """CEM sequence model with a contextual prior over actions.

    CEM captures position-wise structure from elite sequences. The contextual
    model biases each position distribution toward actions that look promising
    for the current benchmark features.
    """

    action_count: int
    steps: int
    rng: random.Random
    warmup: int
    epsilon: float
    ucb: float
    candidate_count: int
    elite_size: int
    smoothing: float
    min_prob: float
    learning_rate: float
    l2: float
    suite_buckets: int
    context_weight: float
    semantic_prior_weight: float
    action_names: list[str] | None = None
    outcomes: list[Outcome] = field(default_factory=list)
    probabilities: list[list[float]] = field(init=False)
    contextual: ContextualLinearBanditPassSelector = field(init=False)

    def __post_init__(self) -> None:
        self.warmup = max(0, self.warmup)
        self.epsilon = clamp(self.epsilon, 0.0, 1.0)
        self.ucb = max(0.0, self.ucb)
        self.candidate_count = max(1, self.candidate_count)
        self.elite_size = max(1, self.elite_size)
        self.smoothing = clamp(self.smoothing, 0.0, 1.0)
        self.min_prob = clamp(self.min_prob, 0.0, 1.0 / self.action_count)
        self.context_weight = clamp(self.context_weight, 0.0, 1.0)
        self.semantic_prior_weight = clamp(self.semantic_prior_weight, 0.0, 1.0)
        if self.action_names is not None and len(self.action_names) != self.action_count:
            self.action_names = None
        uniform = 1.0 / self.action_count
        self.probabilities = [
            [uniform for _ in range(self.action_count)] for _ in range(self.steps)
        ]
        self.contextual = ContextualLinearBanditPassSelector(
            action_count=self.action_count,
            steps=self.steps,
            rng=self.rng,
            warmup=0,
            epsilon=0.0,
            ucb=self.ucb,
            learning_rate=self.learning_rate,
            l2=self.l2,
            suite_buckets=self.suite_buckets,
        )

    def select(
        self,
        trial: int,
        context: dict[str, Any] | None = None,
    ) -> tuple[str, list[int]]:
        if trial <= self.warmup or len(self.outcomes) < self.elite_size:
            if self.semantic_prior_weight > 0.0 and self.action_names:
                distribution = self._semantic_prior_distribution(context)
                return "semantic_prior", self._sample_from_distributions(
                    [distribution for _ in range(self.steps)]
                )
            return "random", random_sequence(self.rng, self.action_count, self.steps)

        distributions = [
            self._hybrid_distribution(context, position)
            for position in range(self.steps)
        ]
        candidates = [
            self._sample_from_distributions(distributions)
            for _ in range(self.candidate_count)
        ]
        best = max(
            candidates,
            key=lambda actions: self._sequence_log_probability(actions, distributions),
        )
        return "contextual_cem", best

    def update(
        self,
        actions: list[int],
        reward: float,
        context: dict[str, Any] | None = None,
    ) -> None:
        if len(actions) != self.steps:
            return
        self.outcomes.append(Outcome(actions=list(actions), reward=reward))
        self.contextual.update(actions, reward, context)
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

    def _hybrid_distribution(
        self, context: dict[str, Any] | None, position: int
    ) -> list[float]:
        cem_probs = self.probabilities[position]
        context_probs = self._contextual_distribution(context, position)
        blended = [
            (1.0 - self.context_weight) * cem_prob
            + self.context_weight * context_prob
            for cem_prob, context_prob in zip(cem_probs, context_probs)
        ]
        if self.semantic_prior_weight > 0.0 and self.action_names:
            semantic_probs = self._semantic_prior_distribution(context)
            blended = [
                (1.0 - self.semantic_prior_weight) * learned_prob
                + self.semantic_prior_weight * semantic_prob
                for learned_prob, semantic_prob in zip(blended, semantic_probs)
            ]
        return self._normalize_with_floor(blended)

    def _semantic_prior_distribution(
        self, context: dict[str, Any] | None
    ) -> list[float]:
        if not self.action_names:
            return [1.0 / self.action_count for _ in range(self.action_count)]
        return semantic_prior_distribution(context, self.action_names)

    def _contextual_distribution(
        self, context: dict[str, Any] | None, position: int
    ) -> list[float]:
        features = self.contextual._features(context, position)
        log_total = math.log(self.contextual.total_updates + 2)
        scores = []
        for action in range(self.action_count):
            prediction = self.contextual._predict(action, features)
            exploration = self.ucb * math.sqrt(log_total) * self.contextual._uncertainty(
                action, features
            )
            scores.append(prediction + exploration)
        return self._softmax(scores)

    def _sample_from_distributions(self, distributions: list[list[float]]) -> list[int]:
        actions = []
        for probs in distributions:
            if self.rng.random() < self.epsilon:
                actions.append(self.rng.randrange(self.action_count))
            else:
                actions.append(self._sample_categorical(probs))
        return actions

    def _sample_categorical(self, probs: list[float]) -> int:
        needle = self.rng.random()
        cumulative = 0.0
        for action, prob in enumerate(probs):
            cumulative += prob
            if needle <= cumulative:
                return action
        return self.action_count - 1

    def _sequence_log_probability(
        self, actions: list[int], distributions: list[list[float]]
    ) -> float:
        return sum(
            math.log(max(distributions[position][action], 1e-12))
            for position, action in enumerate(actions)
        )

    def _softmax(self, scores: list[float]) -> list[float]:
        if not scores:
            return []
        shift = max(scores)
        values = [math.exp(clamp(score - shift, -40.0, 40.0)) for score in scores]
        return self._normalize(values)

    def _normalize_with_floor(self, probs: list[float]) -> list[float]:
        normalized = self._normalize(probs)
        floor_mass = self.min_prob * self.action_count
        remaining_mass = max(0.0, 1.0 - floor_mass)
        return [
            self.min_prob + remaining_mass * prob
            for prob in normalized
        ]

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
        for position in range(self.steps):
            distribution = self._hybrid_distribution(None, position)
            ranked = sorted(
                range(self.action_count),
                key=lambda action: distribution[action],
                reverse=True,
            )[:top_n]
            top_per_position.append(
                {
                    "position": position,
                    "top_actions": [
                        {"action": action, "probability": distribution[action]}
                        for action in ranked
                    ],
                }
            )

        return {
            "type": "contextual_cross_entropy_sequence_model",
            "warmup": self.warmup,
            "epsilon": self.epsilon,
            "ucb": self.ucb,
            "candidate_count": self.candidate_count,
            "elite_size": self.elite_size,
            "smoothing": self.smoothing,
            "min_prob": self.min_prob,
            "context_weight": self.context_weight,
            "semantic_prior_weight": self.semantic_prior_weight,
            "observations": len(self.outcomes),
            "elite": [
                {"actions": item.actions, "reward": item.reward} for item in elite
            ],
            "positions": top_per_position,
            "contextual": self.contextual.snapshot(top_n=top_n),
            "semantic_prior": {
                "enabled": self.semantic_prior_weight > 0.0 and bool(self.action_names),
                "top_actions_without_context": top_semantic_actions(
                    None, self.action_names, top_n=top_n
                )
                if self.action_names
                else [],
            },
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
    context_learning_rate: float,
    context_l2: float,
    context_suite_buckets: int,
    hybrid_context_weight: float = 0.35,
    semantic_prior_weight: float = 0.0,
    action_names: list[str] | None = None,
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
    if strategy in {"contextual", "contextual_bandit"}:
        return ContextualLinearBanditPassSelector(
            action_count=action_count,
            steps=steps,
            rng=rng,
            warmup=warmup,
            epsilon=epsilon,
            ucb=ucb,
            learning_rate=context_learning_rate,
            l2=context_l2,
            suite_buckets=context_suite_buckets,
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
    if strategy in {"contextual_cem", "hybrid_cem", "hybrid"}:
        return ContextualCrossEntropyPassSelector(
            action_count=action_count,
            steps=steps,
            rng=rng,
            warmup=warmup,
            epsilon=epsilon,
            ucb=ucb,
            candidate_count=cem_candidates,
            elite_size=cem_elite_size,
            smoothing=cem_smoothing,
            min_prob=cem_min_prob,
            learning_rate=context_learning_rate,
            l2=context_l2,
            suite_buckets=context_suite_buckets,
            context_weight=hybrid_context_weight,
            semantic_prior_weight=semantic_prior_weight,
            action_names=action_names,
        )
    raise ValueError(f"Unknown pass selection strategy: {strategy}")
