"""Training, held-out evaluation, and versioned artifacts for a manual cycle."""

import copy
import hashlib
import json
import random
from pathlib import Path

import numpy as np
import torch

from .config import Config
from .features import crop_and_mask, interpolation_baseline, spectrogram
from .model import MaskedPredictor


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_features(index_path: Path, config: Config) -> tuple[list[dict], dict[str, np.ndarray]]:
    index = json.loads(index_path.read_text(encoding="utf-8"))
    features = {}
    for item in index:
        path = index_path.parent / item["path"]
        if _sha256(path) != item["sha256"]:
            raise ValueError(f"WAV hash mismatch: {item['id']}")
        features[item["id"]] = spectrogram(path, config.data.sample_rate, config.features)
    return index, features


def _batch(items: list[dict], features: dict[str, np.ndarray], config: Config, epoch_key: str):
    masked, targets, regions = [], [], []
    for item in items:
        x, y, region = crop_and_mask(features[item["id"]], config.features, f"{epoch_key}:{item['id']}")
        masked.append(x)
        targets.append(y)
        mask = np.zeros((1, config.features.crop_frames), dtype=np.float32)
        mask[:, region] = 1
        regions.append(mask)
    return (
        torch.from_numpy(np.stack(masked)),
        torch.from_numpy(np.stack(targets)),
        torch.from_numpy(np.stack(regions)),
    )


def _masked_mse(prediction: torch.Tensor, target: torch.Tensor, mask: torch.Tensor) -> torch.Tensor:
    return (((prediction - target) ** 2) * mask).sum() / (mask.sum() * target.shape[1])


def evaluate(model: MaskedPredictor, items: list[dict], features: dict[str, np.ndarray], config: Config) -> dict:
    model.eval()
    model_error, baseline_error, count = 0.0, 0.0, 0
    with torch.no_grad():
        for item in items:
            for crop_number in range(config.features.evaluation_crops):
                key = f"evaluation:{item['id']}:{crop_number}"
                x, y, region = crop_and_mask(features[item["id"]], config.features, key)
                mask = np.zeros((1, 1, config.features.crop_frames), dtype=np.float32)
                mask[:, :, region] = 1
                prediction, _ = model(torch.from_numpy(x[None]), torch.from_numpy(mask))
                predicted = prediction.numpy()[0, :, region]
                actual = y[:, region]
                baseline = interpolation_baseline(y, region)
                model_error += float(np.square(predicted - actual).mean())
                baseline_error += float(np.square(baseline - actual).mean())
                count += 1
    return {"model_masked_mse": model_error / count, "baseline_masked_mse": baseline_error / count, "files": len(items), "windows": count}


def train(index: list[dict], features: dict[str, np.ndarray], config: Config, output: Path) -> tuple[MaskedPredictor, dict]:
    torch.manual_seed(config.training.seed)
    np.random.seed(config.training.seed)
    random.seed(config.training.seed)
    torch.set_num_threads(config.training.max_cpu_threads)
    torch.use_deterministic_algorithms(True)
    frequency_bins = config.features.fft_size // 2 + 1
    model = MaskedPredictor(frequency_bins)
    optimizer = torch.optim.Adam(model.parameters(), lr=config.training.learning_rate)
    splits = {name: [item for item in index if item["split"] == name] for name in ("train", "validation", "test")}
    if any(not items for items in splits.values()):
        raise ValueError("All three splits need examples")
    history, best_val, best_state, best_epoch = [], float("inf"), None, None
    for epoch in range(config.training.epochs):
        model.train()
        order = np.random.default_rng(config.training.seed + epoch).permutation(len(splits["train"]))
        losses = []
        for start in range(0, len(order), config.training.batch_size):
            items = [splits["train"][int(i)] for i in order[start:start + config.training.batch_size]]
            x, y, mask = _batch(items, features, config, f"train:{epoch}")
            optimizer.zero_grad(set_to_none=True)
            prediction, _ = model(x, mask)
            loss = _masked_mse(prediction, y, mask)
            loss.backward()
            optimizer.step()
            losses.append(float(loss.detach()))
        validation = evaluate(model, splits["validation"], features, config)
        train_mse = float(np.mean(losses))
        history.append({"epoch": epoch + 1, "train_masked_mse": train_mse, **validation})
        print(f"epoch {epoch + 1}/{config.training.epochs}: train={train_mse:.6f} validation={validation['model_masked_mse']:.6f}", flush=True)
        if validation["model_masked_mse"] < best_val:
            best_val = validation["model_masked_mse"]
            best_state = copy.deepcopy(model.state_dict())
            best_epoch = epoch + 1
    assert best_state is not None
    model.load_state_dict(best_state)
    checkpoint_path = output / "checkpoint.pt"
    torch.save({"state_dict": best_state, "best_epoch": best_epoch, "training_seed": config.training.seed}, checkpoint_path)
    metrics = {
        "best_epoch": best_epoch,
        "history": history,
        "validation": evaluate(model, splits["validation"], features, config),
        "test": evaluate(model, splits["test"], features, config),
        "checkpoint_sha256": _sha256(checkpoint_path),
    }
    return model, metrics


def embeddings(model: MaskedPredictor, index: list[dict], features: dict[str, np.ndarray], config: Config) -> dict[str, np.ndarray]:
    model.eval()
    result = {}
    with torch.no_grad():
        for item in index:
            x, _, region = crop_and_mask(features[item["id"]], config.features, f"projection:{item['id']}")
            mask = np.zeros((1, 1, config.features.crop_frames), dtype=np.float32)
            mask[:, :, region] = 1
            _, embedding = model(torch.from_numpy(x[None]), torch.from_numpy(mask))
            result[item["id"]] = embedding.numpy()[0]
    return result
