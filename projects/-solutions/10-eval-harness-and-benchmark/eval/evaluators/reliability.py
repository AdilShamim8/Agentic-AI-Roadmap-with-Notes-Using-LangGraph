"""Inter-rater reliability metrics.

Used by `eval kappa` to compute agreement between two evaluators on the
same dataset. The spec target is Cohen's kappa > 0.6 on 100 samples.

Implemented:

- `cohen_kappa` — pairwise agreement on a categorical label.
- `krippendorff_alpha` — nominal alpha for arbitrary missing-value patterns.
- `agreement_matrix` — build the confusion matrix between two raters.
"""

from __future__ import annotations

from collections import Counter
from typing import Iterable

import math


def _to_label(score: float, threshold: float = 0.7) -> str:
    """Bin a 0-1 score into a categorical label (pass/fail) for kappa."""

    return "pass" if score >= threshold else "fail"


def agreement_matrix(
    rater_a: Iterable[float],
    rater_b: Iterable[float],
    threshold: float = 0.7,
) -> Counter[tuple[str, str]]:
    """Return a Counter over (label_a, label_b) pairs."""

    a = [_to_label(s, threshold) for s in rater_a]
    b = [_to_label(s, threshold) for s in rater_b]
    if len(a) != len(b):
        raise ValueError(
            f"Rater lists must be equal length; got {len(a)} vs {len(b)}."
        )
    return Counter(zip(a, b))


def cohen_kappa(
    rater_a: Iterable[float],
    rater_b: Iterable[float],
    threshold: float = 0.7,
) -> float:
    """Cohen's kappa between two raters.

    Interpretation (Landis & Koch 1977):
      < 0     poor
      0-0.2   slight
      0.2-0.4 fair
      0.4-0.6 moderate
      0.6-0.8 substantial   <-- the spec target
      0.8-1.0 almost perfect
    """

    matrix = agreement_matrix(rater_a, rater_b, threshold)
    n = sum(matrix.values())
    if n == 0:
        return 0.0

    labels = sorted({la for la, _ in matrix} | {lb for _, lb in matrix})

    # Observed agreement.
    p_o = sum(matrix.get((l, l), 0) for l in labels) / n

    # Expected agreement (independent raters) -- weighted by sample count.
    a_counts: Counter[str] = Counter()
    b_counts: Counter[str] = Counter()
    for (la, lb), c in matrix.items():
        a_counts[la] += c
        b_counts[lb] += c
    p_e = sum((a_counts[l] / n) * (b_counts[l] / n) for l in labels)

    if p_e == 1.0:
        return 1.0
    return (p_o - p_e) / (1.0 - p_e)


def krippendorff_alpha_nominal(
    ratings: list[list[float | None]],
    threshold: float = 0.7,
) -> float:
    """Krippendorff's nominal alpha for arbitrary raters × units.

    `ratings` is a list of (rater × unit) score matrices, where each
    inner list is one rater's scores across all units, and `None` means
    "missing". This is the more general sibling of Cohen's kappa.
    """

    if not ratings:
        return 0.0
    n_raters = len(ratings)
    n_units = max(len(r) for r in ratings)

    # Build per-unit label lists (drop None).
    per_unit: list[list[str]] = [[] for _ in range(n_units)]
    for rater in ratings:
        for i, score in enumerate(rater):
            if score is None:
                continue
            per_unit[i].append(_to_label(score, threshold))

    # n_u = number of ratings per unit (must be >= 2 for that unit to count)
    total_pairs = 0
    agree_pairs = 0
    labels: Counter[str] = Counter()
    for units in per_unit:
        for u in units:
            labels[u] += 1
        if len(units) >= 2:
            total_pairs += len(units) * (len(units) - 1)
            c = Counter(units)
            for v in c.values():
                agree_pairs += v * (v - 1)

    n_total = sum(labels.values())
    if n_total <= 1 or total_pairs == 0:
        return 0.0

    # Observed disagreement Do = 1 - (sum_o v_cu(v-1)) / (sum_u n_u (n_u - 1))
    Do = 1.0 - (agree_pairs / total_pairs) if total_pairs else 0.0

    # Expected disagreement De = 1 - sum_c n_c (n_c - 1) / (N (N - 1))
    De = 1.0 - sum(v * (v - 1) for v in labels.values()) / (n_total * (n_total - 1))

    if De == 0:
        return 1.0
    return 1.0 - (Do / De)


def interpret_kappa(k: float) -> str:
    """Return a Landis-Koch interpretation string for a kappa value."""

    if k < 0:
        return "poor"
    if k < 0.2:
        return "slight"
    if k < 0.4:
        return "fair"
    if k < 0.6:
        return "moderate"
    if k < 0.8:
        return "substantial"
    return "almost perfect"
