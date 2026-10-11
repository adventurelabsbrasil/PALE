import hashlib
import json

import numpy as np
import pytest
import soundfile as sf
import torch

from acoustic_lab.__main__ import run
from acoustic_lab.config import Config, DataConfig, FeatureConfig, TrainingConfig
from acoustic_lab.features import crop_and_mask, interpolation_baseline
from acoustic_lab.model import MaskedPredictor
from acoustic_lab.synth import generate_dataset
from acoustic_lab.training import load_features


def _small_data() -> DataConfig:
    return DataConfig(seed=17, sample_rate=22050, duration_seconds=0.2, parents=6, variants_per_parent=2, train_groups=4, validation_groups=1, test_groups=1)


def test_generation_is_deterministic_and_groups_do_not_cross_splits(tmp_path):
    first, second = tmp_path / "one", tmp_path / "two"
    first_index, first_audit = generate_dataset(_small_data(), first)
    second_index, _ = generate_dataset(_small_data(), second)
    assert first_index.read_bytes() == second_index.read_bytes()
    index = json.loads(first_index.read_text())
    audit = {item["id"]: item for item in json.loads(first_audit.read_text())}
    assert len(index) == 12
    assert {split: sum(item["split"] == split for item in index) for split in ("train", "validation", "test")} == {"train": 8, "validation": 2, "test": 2}
    grouped = {}
    for item in index:
        grouped.setdefault(audit[item["id"]]["group_id"], set()).add(item["split"])
        wav = first / item["path"]
        audio, rate = sf.read(wav)
        assert rate == 22050 and len(audio) == 4410
        assert hashlib.sha256(wav.read_bytes()).hexdigest() == item["sha256"]
        assert wav.read_bytes() == (second / item["path"]).read_bytes()
        assert "family" not in item and "parameters" not in item
    assert all(len(splits) == 1 for splits in grouped.values())


def test_mask_and_baseline_use_only_visible_context():
    feature_config = FeatureConfig(fft_size=64, hop_size=32, crop_frames=16, mask_frames=4)
    array = np.tile(np.arange(30, dtype=np.float32), (33, 1))
    masked, target, region = crop_and_mask(array, feature_config, "fixed")
    np.testing.assert_allclose(masked[:, region], interpolation_baseline(target, region))
    assert np.array_equal(masked[:, :region.start], target[:, :region.start])
    assert np.array_equal(masked[:, region.stop:], target[:, region.stop:])
    baseline = interpolation_baseline(target, region)
    np.testing.assert_allclose(baseline, target[:, region])


def test_hash_check_detects_modified_audio(tmp_path):
    index_path, _ = generate_dataset(_small_data(), tmp_path / "set")
    index = json.loads(index_path.read_text())
    wav = index_path.parent / index[0]["path"]
    wav.write_bytes(wav.read_bytes() + b"corruption")
    config = Config(_small_data(), FeatureConfig(64, 32, 16, 4), TrainingConfig(3, 1, 2, 0.001, 1))
    with pytest.raises(ValueError, match="hash mismatch"):
        load_features(index_path, config)


def test_complete_small_run(tmp_path):
    config_path = tmp_path / "small.toml"
    config_path.write_text("""[data]
seed=17
sample_rate=22050
duration_seconds=0.2
parents=6
variants_per_parent=2
train_groups=4
validation_groups=1
test_groups=1
[features]
fft_size=64
hop_size=32
crop_frames=16
mask_frames=4
[training]
seed=5
epochs=1
batch_size=2
learning_rate=0.001
max_cpu_threads=1
""")
    output = tmp_path / "run"
    result = run(config_path, output)
    assert result["metrics"]["test"]["files"] == 2
    assert result["metrics"]["test"]["windows"] == 8
    assert np.isfinite(result["metrics"]["test"]["model_masked_mse"])
    assert all((output / name).exists() for name in ("checkpoint.pt", "results.json", "report.html", "pca_fit.json", "projection.json"))
    checkpoint = torch.load(output / "checkpoint.pt", weights_only=True)
    model = MaskedPredictor(33)
    model.load_state_dict(checkpoint["state_dict"])
    report = (output / "report.html").read_text()
    index = json.loads((output / "dataset_index.json").read_text())
    assert all(item["path"] in report for item in index)
