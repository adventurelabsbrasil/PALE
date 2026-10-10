"""Deterministic synthetic audio with audit data kept out of model input."""

import hashlib
import json
from pathlib import Path

import numpy as np
from scipy import signal
import soundfile as sf

from .config import DataConfig


FAMILIES = ("oscillator", "oscillator_mix", "modulation", "filtered_noise", "transition")


def _parameters(family: str, rng: np.random.Generator) -> dict:
    if family == "oscillator":
        return {"frequency_hz": float(rng.uniform(80, 2400))}
    if family == "oscillator_mix":
        count = int(rng.integers(2, 5))
        return {
            "frequencies_hz": [float(x) for x in rng.uniform(80, 3500, count)],
            "amplitudes": [float(x) for x in rng.uniform(0.2, 1.0, count)],
        }
    if family == "modulation":
        return {
            "carrier_hz": float(rng.uniform(100, 2400)),
            "modulator_hz": float(rng.uniform(0.4, 35)),
            "depth": float(rng.uniform(0.15, 0.8)),
        }
    if family == "filtered_noise":
        return {
            "cutoff_hz": float(rng.uniform(250, 5000)),
            "filter": "lowpass" if rng.random() < 0.5 else "highpass",
        }
    return {
        "first_hz": float(rng.uniform(80, 3000)),
        "second_hz": float(rng.uniform(80, 3000)),
        "change_fraction": float(rng.uniform(0.25, 0.75)),
    }


def _render(family: str, params: dict, rng: np.random.Generator, sample_rate: int, duration: float) -> np.ndarray:
    count = round(sample_rate * duration)
    time = np.arange(count, dtype=np.float64) / sample_rate
    if family == "oscillator":
        audio = np.sin(2 * np.pi * params["frequency_hz"] * time + rng.uniform(0, 2 * np.pi))
    elif family == "oscillator_mix":
        audio = np.zeros(count, dtype=np.float64)
        for frequency, amplitude in zip(params["frequencies_hz"], params["amplitudes"]):
            audio += amplitude * np.sin(2 * np.pi * frequency * time + rng.uniform(0, 2 * np.pi))
    elif family == "modulation":
        phase = 2 * np.pi * params["carrier_hz"] * time + rng.uniform(0, 2 * np.pi)
        envelope = 1 + params["depth"] * np.sin(2 * np.pi * params["modulator_hz"] * time)
        audio = envelope * np.sin(phase)
    elif family == "filtered_noise":
        sos = signal.butter(4, params["cutoff_hz"], btype=params["filter"], fs=sample_rate, output="sos")
        audio = signal.sosfilt(sos, rng.standard_normal(count))
    else:
        change = int(params["change_fraction"] * count)
        first = np.sin(2 * np.pi * params["first_hz"] * time + rng.uniform(0, 2 * np.pi))
        second = np.sin(2 * np.pi * params["second_hz"] * time + rng.uniform(0, 2 * np.pi))
        audio = np.where(np.arange(count) < change, first, second)
    peak = max(float(np.max(np.abs(audio))), 1e-12)
    return (0.9 * audio / peak).astype(np.float32)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def generate_dataset(config: DataConfig, directory: Path) -> tuple[Path, Path]:
    """Write a model-safe index and a separate provenance audit record."""
    audio_dir = directory / "audio"
    audio_dir.mkdir(parents=True)
    rng = np.random.default_rng(config.seed)
    groups = rng.permutation(config.parents)
    splits = {}
    for position, parent in enumerate(groups):
        if position < config.train_groups:
            split = "train"
        elif position < config.train_groups + config.validation_groups:
            split = "validation"
        else:
            split = "test"
        splits[int(parent)] = split
    index, audit = [], []
    for parent in range(config.parents):
        family = FAMILIES[parent % len(FAMILIES)]
        parent_rng = np.random.default_rng(np.random.SeedSequence([config.seed, parent, 0]))
        params = _parameters(family, parent_rng)
        group_id = hashlib.sha256(f"{config.seed}:group:{parent}".encode()).hexdigest()[:16]
        for variant in range(config.variants_per_parent):
            item_id = hashlib.sha256(f"{config.seed}:item:{parent}:{variant}".encode()).hexdigest()[:16]
            variant_rng = np.random.default_rng(np.random.SeedSequence([config.seed, parent, variant + 1]))
            audio = _render(family, params, variant_rng, config.sample_rate, config.duration_seconds)
            path = audio_dir / f"{item_id}.wav"
            sf.write(path, audio, config.sample_rate, subtype="PCM_16")
            index.append({"id": item_id, "path": f"audio/{item_id}.wav", "split": splits[parent], "sha256": _sha256(path)})
            audit.append({"id": item_id, "group_id": group_id, "family": family, "parameters": params, "generator_seed": [config.seed, parent, variant + 1]})
    index_path, audit_path = directory / "dataset_index.json", directory / "provenance_audit.json"
    index_path.write_text(json.dumps(index, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    audit_path.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return index_path, audit_path
