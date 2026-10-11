"""Disposable visual probe: a synthetic bird-like sound in the two existing worlds."""

from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
import shutil

import numpy as np
from scipy import signal
import soundfile as sf
import torch

from .config import load_config
from .features import crop_and_mask, spectrogram
from .model import FuturePredictor, MaskedPredictor
from .training import embeddings, load_features


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "artifacts/phase1-final"
APPROVED = ROOT / "artifacts/experience-preview-audio-reactive"


def render_bird(path: Path, sample_rate: int, duration: float = 5.0) -> None:
    rng = np.random.default_rng(991)
    count = round(sample_rate * duration)
    audio = np.zeros(count, dtype=np.float64)
    # Four short upward/downward chirps, deliberately synthetic and labelled as a probe.
    for start, length, low, high in ((.35, .42, 1800, 5200), (1.35, .28, 2600, 6500), (2.35, .55, 4200, 1700), (3.65, .38, 2200, 7200)):
        begin = round(start * sample_rate)
        n = round(length * sample_rate)
        t = np.arange(n) / sample_rate
        envelope = np.sin(np.pi * np.linspace(0, 1, n)) ** 1.7
        tone = signal.chirp(t, f0=low, f1=high, t1=length, method="quadratic")
        tone += .18 * signal.chirp(t, f0=low * 2.01, f1=high * 1.7, t1=length, method="linear")
        end = min(count, begin + n)
        audio[begin:end] += tone[: end - begin] * envelope[: end - begin]
    audio += rng.normal(0, .003, count)
    audio /= max(np.max(np.abs(audio)), 1e-9)
    sf.write(path, (.82 * audio).astype(np.float32), sample_rate, subtype="PCM_16")


def fit_with_probe(index: list[dict], vectors: dict[str, np.ndarray], probe: np.ndarray) -> tuple[dict[str, list[float]], list[float]]:
    train = np.stack([vectors[item["id"]] for item in index if item["split"] == "train"]).astype(np.float64)
    mean = train.mean(axis=0)
    _, _, vt = np.linalg.svd(train - mean, full_matrices=False)
    components = vt[:3].copy()
    for row in components:
        pivot = int(np.argmax(np.abs(row)))
        if row[pivot] < 0:
            row *= -1
    matrix = np.stack([vectors[item["id"]] for item in index] + [probe])
    raw = (matrix - mean) @ components.T
    scale = np.maximum(np.max(np.abs(raw[:-1]), axis=0), 1e-9)
    coords = np.clip(raw / scale, -1.0, 1.0).round(6)
    known = {item["id"]: coords[i].tolist() for i, item in enumerate(index)}
    return known, coords[-1].tolist()


def future_vectors(index: list[dict], features: dict[str, np.ndarray], config, probe_features: np.ndarray) -> tuple[dict[str, np.ndarray], np.ndarray]:
    checkpoint = torch.load(APPROVED / "future_predictor.pt", map_location="cpu", weights_only=True)
    model = FuturePredictor(config.features.fft_size // 2 + 1)
    model.load_state_dict(checkpoint["state_dict"])
    model.eval()

    def past(item_features: np.ndarray) -> torch.Tensor:
        midpoint = item_features.shape[1] // 2
        return torch.from_numpy(item_features[:, :midpoint].mean(axis=1).astype(np.float32))

    with torch.no_grad():
        vectors = {}
        for item in index:
            _, hidden = model(past(features[item["id"]])[None])
            vectors[item["id"]] = hidden.numpy()[0]
        _, probe_hidden = model(past(probe_features)[None])
    return vectors, probe_hidden.numpy()[0]


def build(output: Path) -> dict:
    if output.exists():
        raise FileExistsError(output)
    output.mkdir(parents=True)
    config = load_config(SOURCE / "config.toml")
    index, features = load_features(SOURCE / "dataset_index.json", config)
    bird_path = output / "audio" / "bird_probe.wav"
    bird_path.parent.mkdir()
    render_bird(bird_path, config.data.sample_rate)
    bird_features = spectrogram(bird_path, config.data.sample_rate, config.features)

    checkpoint = torch.load(SOURCE / "checkpoint.pt", map_location="cpu", weights_only=True)
    model = MaskedPredictor(config.features.fft_size // 2 + 1)
    model.load_state_dict(checkpoint["state_dict"])
    model.eval()
    with torch.no_grad():
        x, _, region = crop_and_mask(bird_features, config.features, "bird-probe:world-a")
        mask = np.zeros((1, 1, config.features.crop_frames), dtype=np.float32)
        mask[:, :, region] = 1
        _, bird_a = model(torch.from_numpy(x[None]), torch.from_numpy(mask))
    world_a_vectors = embeddings(model, index, features, config)
    world_a, bird_a_coords = fit_with_probe(index, world_a_vectors, bird_a.numpy()[0])
    world_b_vectors, bird_b = future_vectors(index, features, config, bird_features)
    world_b, bird_b_coords = fit_with_probe(index, world_b_vectors, bird_b)

    points = []
    for item in index:
        points.append({"id": item["id"], "split": item["split"], "audio": item["path"], "world_a": world_a[item["id"]], "world_b": world_b[item["id"]]})
    points.append({"id": "bird-probe", "split": "probe", "audio": "audio/bird_probe.wav", "world_a": bird_a_coords, "world_b": bird_b_coords})
    data = {"title": "Dois mundos · probe de passarinho sintético", "source": "phase1-final + bird-probe", "probe": "Som sintético de chirps; não é gravação de pássaro e não entra no benchmark.", "representations": {"world_a": "encoder da Fase 1", "world_b": "preditor de trecho futuro"}, "fit_split": "train", "audio_requires_user_gesture": True, "max_gain": .18, "points": points}
    (output / "experience_data.json").write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
    shutil.copy2(Path(__file__).parent / "web" / "experience.html", output / "experience.html")
    shutil.copy2(Path(__file__).parent / "web" / "experience.js", output / "experience.js")
    (output / "vendor").mkdir()
    for asset in ("three.module.min.js", "three.core.min.js", "OrbitControls.js"):
        shutil.copy2(Path(__file__).parent / "web" / "vendor" / asset, output / "vendor" / asset)
    shutil.copytree(APPROVED / "audio", output / "audio", dirs_exist_ok=True)
    return {"output": str(output), "points": len(points), "bird_world_a": bird_a_coords, "bird_world_b": bird_b_coords}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "artifacts/bird-probe")
    args = parser.parse_args()
    print(json.dumps(build(args.output), indent=2))
