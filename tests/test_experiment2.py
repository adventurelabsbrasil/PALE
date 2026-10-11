import hashlib
import json

import pytest

from acoustic_lab.experiment2 import prepare_experiment2


def test_prepare_experiment2_copies_audio_hash_and_assets(tmp_path):
    source = tmp_path / "source.mp3"
    source.write_bytes(b"test audio bytes")
    output = tmp_path / "output"

    result = prepare_experiment2(source, output)
    manifest = json.loads((output / "manifest.json").read_text())

    copied = output / "audio" / "source.mp3"
    assert copied.read_bytes() == source.read_bytes()
    assert manifest["source"]["sha256"] == hashlib.sha256(source.read_bytes()).hexdigest()
    assert result["output"] == str(output.resolve())
    assert all((output / name).exists() for name in ("experiment2.html", "experiment2.js", "manifest.json"))
    assert all((output / name).exists() for name in ("core.vert", "core.frag", "memory.vert", "memory.frag", "particles.vert", "particles.frag"))
    assert (output / "vendor" / "three.module.min.js").exists()
    assert (output / "vendor" / "postprocessing" / "EffectComposer.js").exists()
    assert (output / "vendor" / "postprocessing" / "UnrealBloomPass.js").exists()
    assert (output / "vendor" / "shaders" / "LuminosityHighPassShader.js").exists()
    assert {"repeat", "novelty"}.issubset(manifest["analysis"]["features"])


def test_prepare_experiment2_rejects_existing_output_and_invalid_audio(tmp_path):
    source = tmp_path / "source.txt"
    source.write_text("not audio")
    with pytest.raises(ValueError, match="WAV or MP3"):
        prepare_experiment2(source, tmp_path / "output")

    valid = tmp_path / "source.wav"
    valid.write_bytes(b"wav")
    output = tmp_path / "existing"
    output.mkdir()
    with pytest.raises(FileExistsError):
        prepare_experiment2(valid, output)
