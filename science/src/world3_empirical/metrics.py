"""Metrics that remain comparable across different variable scales."""

from __future__ import annotations

import numpy as np


def rmse(observed: np.ndarray, predicted: np.ndarray) -> float:
    observed = np.asarray(observed, dtype=float)
    predicted = np.asarray(predicted, dtype=float)
    return float(np.sqrt(np.mean(np.square(predicted - observed))))


def mape(observed: np.ndarray, predicted: np.ndarray) -> float:
    observed = np.asarray(observed, dtype=float)
    predicted = np.asarray(predicted, dtype=float)
    valid = observed != 0
    if not valid.any():
        return float("nan")
    return float(np.mean(np.abs((predicted[valid] - observed[valid]) / observed[valid])) * 100)


def direction_accuracy(observed: np.ndarray, predicted: np.ndarray) -> float:
    observed_direction = np.sign(np.diff(np.asarray(observed, dtype=float)))
    predicted_direction = np.sign(np.diff(np.asarray(predicted, dtype=float)))
    if observed_direction.size == 0:
        return float("nan")
    return float(np.mean(observed_direction == predicted_direction))

