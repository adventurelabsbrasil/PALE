"""Build and serve the isolated Experiment 2 audiovisual organism."""

from __future__ import annotations

import argparse
from functools import partial
import hashlib
import json
from pathlib import Path
import shutil
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import threading
import webbrowser


EXPERIMENT_VERSION = "experiment2-organism-v1"
WEB_ROOT = Path(__file__).parent / "web" / "experiment2"
VENDOR_ROOT = Path(__file__).parent / "web" / "vendor"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def prepare_experiment2(audio: Path, output: Path) -> dict:
    """Create a self-contained local artifact without starting a server."""
    audio = audio.expanduser().resolve()
    output = output.expanduser().resolve()
    if output.exists():
        raise FileExistsError(f"Output directory already exists: {output}")
    if not audio.is_file():
        raise FileNotFoundError(audio)
    if audio.suffix.lower() not in {".mp3", ".wav"}:
        raise ValueError("Experiment 2 accepts only WAV or MP3 audio")
    if audio.stat().st_size == 0:
        raise ValueError("Audio file is empty")

    output.mkdir(parents=True)
    audio_dir = output / "audio"
    audio_dir.mkdir()
    copied_audio = audio_dir / audio.name
    shutil.copy2(audio, copied_audio)

    manifest = {
        "experiment": EXPERIMENT_VERSION,
        "title": "Organism · experimento 2",
        "source": {
            "original_name": audio.name,
            "copied_path": copied_audio.relative_to(output).as_posix(),
            "sha256": _sha256(audio),
            "bytes": audio.stat().st_size,
        },
        "analysis": {
            "window_samples": 2048,
            "hop_samples": 1024,
            "window_description": "Hann window, approximately 46 ms at 44.1 kHz",
            "feature_contract": "acoustic-v1",
            "features": [
                "rms", "silence", "low", "mid", "high", "centroid",
                "spread", "flatness", "flux", "attack", "density", "stereo_width",
                "repeat", "novelty",
            ],
            "normalization": "absolute values plus robust P5-P95 relative contrast",
        },
        "visual": {
            "seed": 2042,
            "detailed_memory_seconds": [8, 12],
            "historical_summary_segments": 256,
            "target_fps": 60,
            "adaptive_complexity": True,
        },
        "audio_requires_user_gesture": True,
        "created_by": "acoustic_lab.experiment2",
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    shutil.copy2(WEB_ROOT / "experiment2.html", output / "experiment2.html")
    shutil.copy2(WEB_ROOT / "experiment2.js", output / "experiment2.js")
    for shader in ("core.vert", "core.frag", "memory.vert", "memory.frag", "particles.vert", "particles.frag"):
        shutil.copy2(WEB_ROOT / shader, output / shader)
    vendor = output / "vendor"
    vendor.mkdir()
    for asset in ("three.module.min.js", "three.core.min.js", "OrbitControls.js"):
        shutil.copy2(VENDOR_ROOT / asset, vendor / asset)
    for folder in ("postprocessing", "shaders"):
        shutil.copytree(VENDOR_ROOT / folder, vendor / folder)
    return {"output": str(output), "manifest": manifest, "audio": str(copied_audio)}


class _Handler(SimpleHTTPRequestHandler):
    def do_POST(self) -> None:  # noqa: N802 - stdlib handler API
        if self.path != "/__shutdown__":
            self.send_error(404)
            return
        self.send_response(204)
        self.end_headers()
        threading.Thread(target=self.server.shutdown, daemon=True).start()

    def log_message(self, format: str, *args) -> None:
        # Keep the single-command workflow quiet; errors still reach the UI.
        return


def serve_experiment2(output: Path, host: str = "127.0.0.1", port: int = 0, open_browser: bool = True) -> str:
    output = output.resolve()
    if not (output / "experiment2.html").is_file():
        raise FileNotFoundError(output / "experiment2.html")
    handler = partial(_Handler, directory=str(output))
    server = ThreadingHTTPServer((host, port), handler)
    url = f"http://{host}:{server.server_port}/experiment2.html"
    print(f"Experiment 2: {url}", flush=True)
    if open_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return url


def run_experiment2(audio: Path, output: Path, *, host: str, port: int, open_browser: bool, serve: bool) -> dict:
    result = prepare_experiment2(audio, output)
    if serve:
        serve_experiment2(output, host=host, port=port, open_browser=open_browser)
    return result


def add_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--audio", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=0)
    parser.add_argument("--no-open", action="store_true")
    parser.add_argument("--no-serve", action="store_true")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the isolated Experiment 2 organism")
    add_arguments(parser)
    args = parser.parse_args()
    run_experiment2(
        args.audio,
        args.output,
        host=args.host,
        port=args.port,
        open_browser=not args.no_open,
        serve=not args.no_serve,
    )


if __name__ == "__main__":
    main()
