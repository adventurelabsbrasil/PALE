"""Fit-once projections for reproducible probe coordinates."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class FittedProjection:
    method: str
    version: str
    fit_split: str
    mean: tuple[float, ...]
    components: tuple[tuple[float, ...], ...]
    scale: tuple[float, ...]
    checkpoint_sha256: str
    config: dict

    def to_dict(self) -> dict:
        return {
            "method": self.method,
            "version": self.version,
            "fit_split": self.fit_split,
            "mean": list(self.mean),
            "components": [list(row) for row in self.components],
            "scale": list(self.scale),
            "checkpoint_sha256": self.checkpoint_sha256,
            "config": self.config,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "FittedProjection":
        # Phase 1 artifacts predate the explicit frozen-projection contract.
        # They remain readable, but are marked legacy instead of being silently
        # presented as a newly versioned fit.
        components = data["components"]
        return cls(
            method=data["method"], version=data.get("version", "pca-legacy"),
            fit_split=data["fit_split"], mean=tuple(data["mean"]),
            components=tuple(tuple(row) for row in components),
            scale=tuple(data.get("scale", [1.0] * len(components))),
            checkpoint_sha256=data.get("checkpoint_sha256", "unknown"),
            config=dict(data.get("config", {})),
        )


def fit_projection(
    train_vectors: np.ndarray,
    *,
    checkpoint_sha256: str,
    config: dict,
    dimensions: int = 2,
) -> FittedProjection:
    """Fit PCA once on training vectors; signs and display scale are frozen."""
    values = np.asarray(train_vectors, dtype=np.float64)
    if values.ndim != 2 or not len(values):
        raise ValueError("train_vectors must be a non-empty matrix")
    if not 1 <= dimensions <= min(values.shape):
        raise ValueError("dimensions must fit the training matrix")
    mean = values.mean(axis=0)
    _, _, vt = np.linalg.svd(values - mean, full_matrices=False)
    components = vt[:dimensions].copy()
    for row in components:
        pivot = int(np.argmax(np.abs(row)))
        if row[pivot] < 0:
            row *= -1
    raw = (values - mean) @ components.T
    scale = np.maximum(np.max(np.abs(raw), axis=0), 1e-9)
    return FittedProjection(
        method="PCA", version="pca-v1", fit_split="train",
        mean=tuple(mean.tolist()), components=tuple(tuple(row) for row in components.tolist()),
        scale=tuple(scale.tolist()), checkpoint_sha256=checkpoint_sha256, config=dict(config),
    )


def transform_projection(vectors: np.ndarray, fitted: FittedProjection) -> np.ndarray:
    """Transform new vectors without refitting or changing the projection."""
    values = np.asarray(vectors, dtype=np.float64)
    if values.ndim == 1:
        values = values[None, :]
    mean = np.asarray(fitted.mean)
    components = np.asarray(fitted.components)
    scale = np.asarray(fitted.scale)
    if values.ndim != 2 or values.shape[1] != mean.shape[0]:
        raise ValueError("vectors have incompatible embedding dimensions")
    return ((values - mean) @ components.T / scale).astype(np.float32)
