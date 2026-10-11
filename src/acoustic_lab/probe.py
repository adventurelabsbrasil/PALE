"""Controlled WAV representation probe; probe artifacts never enter training."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import time

import numpy as np
import soundfile as sf
import torch

from .config import load_config
from .features import crop_and_mask, spectrogram
from .model import MaskedPredictor
from .projection import FittedProjection, transform_projection
from .windows import WindowConfig, sliding_windows


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _embedding(model: MaskedPredictor, window: np.ndarray, config, key: str) -> np.ndarray:
    masked, _, region = crop_and_mask(window, config, key)
    mask = np.zeros((1, 1, config.crop_frames), dtype=np.float32)
    mask[:, :, region] = 1
    with torch.no_grad():
        _, vector = model(torch.from_numpy(masked[None]), torch.from_numpy(mask))
    return vector.numpy()[0]


def _audio_metrics(audio: np.ndarray) -> dict:
    peak = float(np.max(np.abs(audio))) if len(audio) else 0.0
    return {
        "samples": int(len(audio)),
        "peak": peak,
        "rms": float(np.sqrt(np.mean(np.square(audio)))) if len(audio) else 0.0,
        "silence": bool(peak == 0.0),
        "clipping": bool(np.any(np.abs(audio) >= 0.999)),
    }


def _write_html(output: Path, report: dict, frame_seconds: float) -> None:
    """Write a deliberately small, self-contained exploratory trajectory view."""
    payload = json.dumps(report, sort_keys=True).replace("</", "<\\/")
    html = f"""<!doctype html>
<html lang="pt-BR"><meta charset="utf-8">
<title>Probe acústico · trajetória exploratória</title>
<style>
body{{font:16px system-ui;max-width:980px;margin:2rem auto;padding:0 1rem;color:#17212b}}
svg{{width:100%;height:auto;border:1px solid #ccd4dc;background:#f8fafc}}
circle{{fill:#2878b5;cursor:pointer}}circle.active{{fill:#d55e00;r:6}}
button,input{{font:inherit}}.grid{{display:grid;grid-template-columns:2fr 1fr;gap:1rem}}
table{{border-collapse:collapse}}td,th{{padding:.35rem .6rem;border-bottom:1px solid #ccd4dc;text-align:left}}
.note{{color:#53616d;font-size:.9rem}}
</style>
<h1>Probe acústico</h1>
<p class="note">Visualização exploratória da representação congelada. Pontos não são espécies, instrumentos, gêneros, notas ou emoções.</p>
<div class="grid"><section><svg id="plot" viewBox="0 0 760 440" role="img" aria-label="Trajetória temporal do embedding"></svg>
<label>Janela <input id="slider" type="range" min="0" max="0" value="0"></label>
<span id="window-label"></span><br><button id="play">Ouvir</button> <audio id="audio" controls preload="metadata"></audio></section>
<section><table id="metrics"></table><p id="details" class="note"></p></section></div>
<script>
const data = {payload};
const frameSeconds = {frame_seconds};
const points = data.points;
const plot = document.getElementById('plot');
const slider = document.getElementById('slider');
const audio = document.getElementById('audio');
const label = document.getElementById('window-label');
const details = document.getElementById('details');
slider.max = Math.max(points.length - 1, 0);
audio.src = data.audio_url;
const xy = points.map(p => p.coordinate);
const lo = [Math.min(...xy.map(p => p[0]), 0), Math.min(...xy.map(p => p[1]), 0)];
const hi = [Math.max(...xy.map(p => p[0]), 0), Math.max(...xy.map(p => p[1]), 0)];
const span = [Math.max(hi[0] - lo[0], 1e-9), Math.max(hi[1] - lo[1], 1e-9)];
const pos = p => [40 + 680 * (p[0] - lo[0]) / span[0], 400 - 360 * (p[1] - lo[1]) / span[1]];
const polyline = document.createElementNS('http://www.w3.org/2000/svg','polyline');
polyline.setAttribute('points', xy.map(pos).map(p => p.join(',')).join(' '));
polyline.setAttribute('fill','none'); polyline.setAttribute('stroke','#9bb8cc'); polyline.setAttribute('stroke-width','2');
plot.append(polyline);
const dots = points.map((point, i) => {{ const c=document.createElementNS('http://www.w3.org/2000/svg','circle'); const p=pos(point.coordinate); c.setAttribute('cx',p[0]); c.setAttribute('cy',p[1]); c.setAttribute('r','4'); c.onclick=()=>{{slider.value=i; update()}}; plot.append(c); return c; }});
function update() {{ if (!points.length) {{ label.textContent=' · sem janelas completas'; details.textContent='O áudio é menor que a janela mínima.'; return; }} const i=Number(slider.value); dots.forEach((d,j)=>d.classList.toggle('active',j===i)); const p=points[i]; label.textContent=` · janela ${{p.window}}`; details.textContent=`coordenada: [${{p.coordinate.map(v=>v.toFixed(5)).join(', ')}}] · tempo aproximado: ${{(p.window * {frame_seconds}).toFixed(3)}} s`; }}
slider.oninput=update;
document.getElementById('play').onclick=()=>{{audio.currentTime=Number(slider.value)*{frame_seconds}; audio.play()}};
const m=data.metrics; document.getElementById('metrics').innerHTML=`<tr><th>Janelas</th><td>${{data.windows}}</td></tr><tr><th>Silêncio</th><td>${{data.audio.silence}}</td></tr><tr><th>Clipping</th><td>${{data.audio.clipping}}</td></tr><tr><th>Latência/janela</th><td>${{m.embedding_latency_ms_per_window.toFixed(3)}} ms</td></tr><tr><th>Distância adjacente</th><td>${{m.adjacent_projection_distance_mean.toFixed(6)}}</td></tr><tr><th>Repetibilidade</th><td>${{m.repeatability_same_window_max_distance.toExponential(2)}}</td></tr>`;
update();
</script></html>"""
    (output / "probe.html").write_text(html, encoding="utf-8")


def probe_wav(
    audio_path: Path,
    checkpoint_path: Path,
    projection_path: Path,
    config_path: Path,
    output: Path,
    *,
    hop_frames: int = 16,
) -> dict:
    """Generate reproducible points and stability metrics for one external WAV."""
    if output.exists():
        raise FileExistsError(output)
    output.mkdir(parents=True)
    config = load_config(config_path)
    audio, sample_rate = sf.read(audio_path, dtype="float32", always_2d=False)
    if audio.ndim != 1 or sample_rate != config.data.sample_rate:
        raise ValueError(f"Expected mono WAV at {config.data.sample_rate} Hz")
    features = spectrogram(audio_path, config.data.sample_rate, config.features)
    windows = sliding_windows(features, WindowConfig(config.features.crop_frames, hop_frames, "empty"))
    checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=True)
    model = MaskedPredictor(config.features.fft_size // 2 + 1)
    model.load_state_dict(checkpoint["state_dict"])
    model.eval()
    started = time.perf_counter()
    vectors = np.stack([_embedding(model, window, config.features, f"probe:{i}") for i, window in enumerate(windows)]) if windows else np.empty((0, model.encoder[0].out_channels))
    elapsed = time.perf_counter() - started
    repeated = np.stack([_embedding(model, window, config.features, f"probe:{i}") for i, window in enumerate(windows)]) if windows else vectors
    fitted = FittedProjection.from_dict(json.loads(projection_path.read_text(encoding="utf-8")))
    coordinates = transform_projection(vectors, fitted) if len(vectors) else np.empty((0, len(fitted.components)), dtype=np.float32)
    adjacent = np.linalg.norm(np.diff(coordinates, axis=0), axis=1) if len(coordinates) > 1 else np.array([], dtype=np.float32)
    repeats = np.linalg.norm(vectors[1:] - vectors[:-1], axis=1) if len(vectors) > 1 else np.array([], dtype=np.float32)
    shutil.copy2(audio_path, output / "probe-audio.wav")
    report = {
        "audio": {"path": str(audio_path), "sha256": _sha256(audio_path), "sample_rate": int(sample_rate), **_audio_metrics(audio)},
        "audio_url": "probe-audio.wav",
        "contract": {"feature": "canonical spectrogram", "window_frames": config.features.crop_frames, "hop_frames": hop_frames, "short_audio": "empty"},
        "frozen": {"checkpoint_sha256": _sha256(checkpoint_path), "projection": fitted.to_dict()},
        "windows": int(len(windows)),
        "points": [{"window": i, "coordinate": coordinates[i].tolist()} for i in range(len(coordinates))],
        "metrics": {
            "embedding_latency_ms_total": elapsed * 1000,
            "embedding_latency_ms_per_window": elapsed * 1000 / len(windows) if windows else 0.0,
            "adjacent_projection_distance_mean": float(adjacent.mean()) if len(adjacent) else 0.0,
            "adjacent_embedding_distance_mean": float(repeats.mean()) if len(repeats) else 0.0,
            "repeatability_same_window_max_distance": float(np.linalg.norm(vectors - repeated, axis=1).max()) if len(vectors) else 0.0,
        },
    }
    (output / "probe.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    window_step_seconds = config.features.hop_size * hop_frames / config.data.sample_rate
    _write_html(output, report, window_step_seconds)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Probe a WAV through the frozen acoustic representation")
    parser.add_argument("--audio", type=Path, required=True)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--projection", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--hop-frames", type=int, default=16)
    args = parser.parse_args()
    report = probe_wav(
        args.audio, args.checkpoint, args.projection, args.config, args.output,
        hop_frames=args.hop_frames,
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
