"""Strict local configuration for the Phase 1 experiment."""

from dataclasses import dataclass
from pathlib import Path
import tomllib


@dataclass(frozen=True)
class DataConfig:
    seed: int
    sample_rate: int
    duration_seconds: float
    parents: int
    variants_per_parent: int
    train_groups: int
    validation_groups: int
    test_groups: int


@dataclass(frozen=True)
class FeatureConfig:
    fft_size: int
    hop_size: int
    crop_frames: int
    mask_frames: int
    evaluation_crops: int = 4


@dataclass(frozen=True)
class TrainingConfig:
    seed: int
    epochs: int
    batch_size: int
    learning_rate: float
    max_cpu_threads: int


@dataclass(frozen=True)
class Config:
    data: DataConfig
    features: FeatureConfig
    training: TrainingConfig


def load_config(path: Path) -> Config:
    with path.open("rb") as handle:
        raw = tomllib.load(handle)
    config = Config(
        data=DataConfig(**raw["data"]),
        features=FeatureConfig(**raw["features"]),
        training=TrainingConfig(**raw["training"]),
    )
    d, f, t = config.data, config.features, config.training
    if d.parents != d.train_groups + d.validation_groups + d.test_groups:
        raise ValueError("Split group counts must sum to parents")
    if min(d.parents, d.variants_per_parent, d.sample_rate, t.epochs, t.batch_size, t.max_cpu_threads) < 1:
        raise ValueError("Counts and rates must be positive")
    if d.duration_seconds <= 0 or t.learning_rate <= 0:
        raise ValueError("Duration and learning rate must be positive")
    if f.fft_size < 32 or f.hop_size < 1 or f.hop_size > f.fft_size:
        raise ValueError("Invalid transform dimensions")
    if not 0 < f.mask_frames < f.crop_frames - 2:
        raise ValueError("Mask must leave visible context on both sides")
    if f.evaluation_crops < 1:
        raise ValueError("At least one evaluation crop is required")
    if d.duration_seconds * d.sample_rate < f.fft_size + f.hop_size * (f.crop_frames - 1):
        raise ValueError("Audio is too short for the requested crop")
    return config
