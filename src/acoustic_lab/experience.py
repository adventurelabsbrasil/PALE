"""Build the local two-world audiovisual prototype from a completed Phase 1 run."""

from __future__ import annotations

import copy
import json
from pathlib import Path
import random
import shutil

import numpy as np
import torch

from .config import load_config
from .model import FuturePredictor, MaskedPredictor
from .training import embeddings, load_features
from .visualization import project_2d


def _fit_3d(index: list[dict], vectors: dict[str, np.ndarray]) -> dict[str, list[float]]:
    train = np.stack([vectors[item["id"]] for item in index if item["split"] == "train"]).astype(np.float64)
    mean = train.mean(axis=0)
    _, _, vt = np.linalg.svd(train - mean, full_matrices=False)
    components = vt[:3].copy()
    for row in components:
        pivot = int(np.argmax(np.abs(row)))
        if row[pivot] < 0:
            row *= -1
    raw = {item["id"]: ((vectors[item["id"]] - mean) @ components.T) for item in index}
    matrix = np.stack(list(raw.values()))
    scale = np.maximum(np.max(np.abs(matrix), axis=0), 1e-9)
    return {item_id: np.clip((value / scale), -1.0, 1.0).round(6).tolist() for item_id, value in raw.items()}


def _future_vectors(index: list[dict], features: dict[str, np.ndarray], config, output: Path) -> dict[str, np.ndarray]:
    seed = config.training.seed + 1
    torch.manual_seed(seed)
    np.random.seed(seed)
    random.seed(seed)
    torch.set_num_threads(config.training.max_cpu_threads)
    torch.use_deterministic_algorithms(True)
    frequency_bins = config.features.fft_size // 2 + 1
    model = FuturePredictor(frequency_bins)
    optimizer = torch.optim.Adam(model.parameters(), lr=config.training.learning_rate)
    train_items = [item for item in index if item["split"] == "train"]

    def pair(item: dict) -> tuple[torch.Tensor, torch.Tensor]:
        spectrum = features[item["id"]]
        midpoint = spectrum.shape[1] // 2
        future_end = midpoint + max(1, spectrum.shape[1] // 4)
        past = spectrum[:, :midpoint].mean(axis=1).astype(np.float32)
        future = spectrum[:, midpoint:future_end].mean(axis=1).astype(np.float32)
        return torch.from_numpy(past), torch.from_numpy(future)

    best_state, best_loss = None, float("inf")
    for epoch in range(6):
        order = np.random.default_rng(seed + epoch).permutation(len(train_items))
        model.train()
        losses = []
        for start in range(0, len(order), config.training.batch_size):
            batch = [train_items[int(i)] for i in order[start:start + config.training.batch_size]]
            past, future = zip(*(pair(item) for item in batch))
            prediction, _ = model(torch.stack(past))
            loss = torch.square(prediction - torch.stack(future)).mean()
            optimizer.zero_grad(set_to_none=True)
            loss.backward()
            optimizer.step()
            losses.append(float(loss.detach()))
        epoch_loss = float(np.mean(losses))
        print(f"future predictor epoch {epoch + 1}/6: train={epoch_loss:.6f}", flush=True)
        if epoch_loss < best_loss:
            best_loss = epoch_loss
            best_state = copy.deepcopy(model.state_dict())
    assert best_state is not None
    model.load_state_dict(best_state)
    torch.save({"state_dict": best_state, "training_seed": seed, "train_loss": best_loss}, output / "future_predictor.pt")
    model.eval()
    vectors = {}
    with torch.no_grad():
        for item in index:
            past, _ = pair(item)
            _, hidden = model(past[None])
            vectors[item["id"]] = hidden.numpy()[0]
    return vectors


def build_experience(source: Path, output: Path) -> dict:
    if output.exists():
        raise FileExistsError(f"Output directory already exists: {output}")
    source = source.resolve()
    output.mkdir(parents=True)
    config = load_config(source / "config.toml")
    index, features = load_features(source / "dataset_index.json", config)

    checkpoint = torch.load(source / "checkpoint.pt", map_location="cpu", weights_only=True)
    model = MaskedPredictor(config.features.fft_size // 2 + 1)
    model.load_state_dict(checkpoint["state_dict"])
    world_a_vectors = embeddings(model, index, features, config)
    world_b_vectors = _future_vectors(index, features, config, output)
    world_a = _fit_3d(index, world_a_vectors)
    world_b = _fit_3d(index, world_b_vectors)

    points = []
    for item in index:
        points.append({
            "id": item["id"],
            "split": item["split"],
            "audio": item["path"],
            "world_a": world_a[item["id"]],
            "world_b": world_b[item["id"]],
        })
    data = {
        "title": "Dois mundos acústicos · prévia local",
        "source": "artifacts/phase1-final",
        "representations": {
            "world_a": "encoder da Fase 1",
            "world_b": "preditor de trecho futuro, treinado do zero",
        },
        "fit_split": "train",
        "audio_requires_user_gesture": True,
        "max_gain": 0.18,
        "points": points,
    }
    (output / "experience_data.json").write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    web_source = Path(__file__).parent / "web"
    shutil.copytree(source / "audio", output / "audio")
    shutil.copy2(web_source / "experience.html", output / "experience.html")
    shutil.copy2(web_source / "experience.js", output / "experience.js")
    (output / "vendor").mkdir()
    for asset in ("three.module.min.js", "three.core.min.js", "OrbitControls.js"):
        shutil.copy2(web_source / "vendor" / asset, output / "vendor" / asset)
    projection, _ = project_2d(index, world_a_vectors)
    (output / "world_a_projection_2d.json").write_text(json.dumps(projection, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {"output": str(output), "points": len(points), "representations": data["representations"]}
