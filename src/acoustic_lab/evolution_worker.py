"""Isolated candidate worker; writes only to its candidate directory."""

import json
from pathlib import Path
import sys

import numpy as np
import torch

from .config import load_config
from .model import FuturePredictor
from .training import load_features


def main() -> None:
    kind, path_text = sys.argv[1:3]
    if kind != "model":
        raise ValueError(kind)
    path = Path(path_text)
    request = json.loads((path / "request.json").read_text())
    source = Path(request["source"])
    config = load_config(source / "config.toml")
    index, features = load_features(source / "dataset_index.json", config)
    seed = request["seed"]
    torch.manual_seed(seed)
    torch.set_num_threads(2)
    torch.use_deterministic_algorithms(True)
    np.random.seed(seed)

    def pair(item):
        spectrum = features[item["id"]]
        midpoint = spectrum.shape[1] // 2
        end = midpoint + max(1, spectrum.shape[1] // 4)
        past = spectrum[:, :midpoint].mean(axis=1).astype(np.float32)
        future = spectrum[:, midpoint:end].mean(axis=1).astype(np.float32)
        return past, future

    splits = {s: [pair(item) for item in index if item["split"] == s] for s in ("train", "validation", "test")}
    model = FuturePredictor(config.features.fft_size // 2 + 1)
    optimizer = torch.optim.Adam(model.parameters(), lr=config.training.learning_rate)

    def evaluate(rows):
        model.eval()
        x = torch.from_numpy(np.stack([p for p, _ in rows]))
        y = np.stack([f for _, f in rows])
        with torch.no_grad():
            prediction = model(x)[0].numpy()
        return {"model_mse": float(np.square(prediction - y).mean()), "persistence_mse": float(np.square(x.numpy() - y).mean())}

    best = float("inf")
    best_state = None
    train = splits["train"]
    for epoch in range(request["epochs"]):
        order = np.random.default_rng(seed + epoch).permutation(len(train))
        model.train()
        for start in range(0, len(order), config.training.batch_size):
            batch = [train[int(i)] for i in order[start:start + config.training.batch_size]]
            x = torch.from_numpy(np.stack([p for p, _ in batch]))
            y = torch.from_numpy(np.stack([f for _, f in batch]))
            prediction = model(x)[0]
            loss = torch.square(prediction - y).mean()
            optimizer.zero_grad(set_to_none=True)
            loss.backward()
            optimizer.step()
        validation = evaluate(splits["validation"])
        if validation["model_mse"] < best:
            best = validation["model_mse"]
            best_state = {key: value.clone() for key, value in model.state_dict().items()}
    model.load_state_dict(best_state)
    torch.save({"state_dict": best_state, "seed": seed}, path / "checkpoint.pt")
    result = {"validation": evaluate(splits["validation"])}
    gain = 1 - result["validation"]["model_mse"] / result["validation"]["persistence_mse"]
    if gain >= 0.05:
        result["test"] = evaluate(splits["test"])
    (path / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
