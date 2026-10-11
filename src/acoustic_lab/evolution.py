"""Bounded, resumable local evolution experiment. No active version is modified."""

from __future__ import annotations

import argparse
import ast
from datetime import datetime, timezone
import difflib
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

import numpy as np



ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "artifacts/phase1-final"
PREVIEW = ROOT / "artifacts/experience-preview-audio-reactive"
LAB = ROOT / "artifacts/evolution"
EXPERIENCE = ROOT / "src/acoustic_lab/experience.py"
EVALUATOR = Path(__file__).resolve()
MAX_BYTES = 2 * 1024**3


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_json(path: Path, value: object) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)


def baseline() -> dict:
    required = {
        "dataset_index": SOURCE / "dataset_index.json",
        "config": SOURCE / "config.toml",
        "phase1_checkpoint": SOURCE / "checkpoint.pt",
        "approved_experience_data": PREVIEW / "experience_data.json",
        "approved_experience_js": PREVIEW / "experience.js",
        "code_source": EXPERIENCE,
        "evaluator": EVALUATOR,
        "model_evaluator": ROOT / "src/acoustic_lab/evolution_worker.py",
    }
    if not all(p.is_file() for p in required.values()):
        raise FileNotFoundError("Missing frozen source or approved preview")
    manifest = {k: {"path": str(p.relative_to(ROOT)), "sha256": sha(p)} for k, p in required.items()}
    manifest["split_counts"] = {s: sum(x["split"] == s for x in json.loads(required["dataset_index"].read_text())) for s in ("train", "validation", "test")}
    return manifest


def check_baseline() -> dict:
    LAB.mkdir(parents=True, exist_ok=True)
    path = LAB / "baseline.json"
    current = baseline()
    if path.exists():
        saved = json.loads(path.read_text())
        if saved != current:
            raise RuntimeError("Frozen baseline changed; stop and review baseline.json")
    else:
        write_json(path, current)
    return current


def size_bytes(path: Path) -> int:
    return sum(p.stat().st_size for p in path.rglob("*") if p.is_file())


def battery_ok() -> bool:
    result = subprocess.run(["pmset", "-g", "batt"], text=True, capture_output=True, check=True)
    import re
    match = re.search(r"(\d+)%", result.stdout)
    return bool(match and int(match.group(1)) > 50)


def rss_bytes(pid: int) -> int:
    result = subprocess.run(["ps", "-o", "rss=", "-p", str(pid)], text=True, capture_output=True)
    try:
        return int(result.stdout.strip()) * 1024
    except ValueError:
        return 0


def run_worker(kind: str, candidate: Path, seconds: float, *, sandbox: bool = False) -> dict:
    candidate.mkdir(parents=True, exist_ok=True)
    args = [sys.executable, "-m", "acoustic_lab.evolution_worker", kind, str(candidate)]
    if sandbox:
        # The candidate receives only serialized vectors; protected data and evaluator stay outside.
        profile = candidate / "sandbox.sb"
        q = lambda p: str(p).replace('"', '\\"')
        profile.write_text('(version 1)\n(deny default)\n(allow process*)\n(allow file-read*)\n(allow file-write* (subpath "' + q(candidate) + '"))\n(allow file-write* (literal "/dev/null"))\n(deny network*)\n')
        args = ["sandbox-exec", "-f", str(profile), *args]
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "OMP_NUM_THREADS": "2", "MKL_NUM_THREADS": "2", "OPENBLAS_NUM_THREADS": "2", "VECLIB_MAXIMUM_THREADS": "2"}
    started = time.monotonic()
    with (candidate / "stdout.log").open("w") as out, (candidate / "stderr.log").open("w") as err:
        proc = subprocess.Popen(args, cwd=ROOT, env=env, stdout=out, stderr=err, start_new_session=True)
        peak = 0
        reason = None
        while proc.poll() is None:
            peak = max(peak, rss_bytes(proc.pid))
            if (LAB / "STOP").exists():
                reason = "stopped"
            elif time.monotonic() - started > seconds:
                reason = "timeout"
            elif peak > 1024**3:
                reason = "memory_limit"
            if reason:
                os.killpg(proc.pid, signal.SIGKILL)
                proc.wait()
                break
            time.sleep(0.1)
    result = {"exit_code": proc.returncode, "seconds": round(time.monotonic() - started, 3), "peak_rss_bytes": peak, "interruption": reason}
    if proc.returncode == 0 and (candidate / "result.json").exists():
        result.update(json.loads((candidate / "result.json").read_text()))
    return result


def visual_candidates(preview: dict, cycle: Path, limit: float, sequence: int) -> list[dict]:
    variation = sequence - 100 if sequence >= 100 else sequence
    points = preview["points"]
    a = np.array([p["world_a"] for p in points], dtype=float)
    b = np.array([p["world_b"] for p in points], dtype=float)
    # Fixed point trajectories through each world proxy for visible difference and pan response.
    baseline_gap = float(np.mean(np.linalg.norm(a - b, axis=1)))
    output = []
    for i, (angle, bend) in enumerate(((0.08 + .01 * variation, 0), (-0.08 - .01 * variation, 0.04), (0.14 + .01 * variation, -0.04)), 1):
        path = cycle / f"visual-{i}"
        path.mkdir(exist_ok=True)
        if (path / "manifest.json").exists():
            output.append(json.loads((path / "manifest.json").read_text()))
            continue
        if time.monotonic() > limit:
            break
        c, s = np.cos(angle), np.sin(angle)
        rot = np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])
        transformed = b @ rot.T
        transformed[:, 2] += bend * np.sin(np.arange(len(b)) * 0.17)
        transformed = np.clip(transformed, -1, 1)
        gap = float(np.mean(np.linalg.norm(a - transformed, axis=1)))
        pan_change = float(np.mean(np.abs(transformed[:, 0] - b[:, 0])))
        distinct = bool(gap >= baseline_gap * 1.01 and pan_change >= 0.02)
        result = {"line": "visual_audio", "candidate": i, "seed": 7000 + i, "parameters": {"rotation_radians": angle, "z_bend": bend}, "metrics": {"world_gap": gap, "baseline_world_gap": baseline_gap, "mean_pan_change": pan_change}, "status": "awaiting_perceptual_review" if distinct else "rejected", "reason": "human trajectory/audio review required" if distinct else "objective distinction gate failed"}
        write_json(path / "coordinates.json", transformed.round(6).tolist())
        write_json(path / "manifest.json", result)
        output.append(result)
    return output


def code_candidates(preview: dict, cycle: Path, limit: float, sequence: int) -> list[dict]:
    variation = sequence - 100 if sequence >= 100 else sequence
    source = EXPERIENCE.read_text()
    tree = ast.parse(source)
    function = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_fit_3d")
    original = ast.get_source_segment(source, function)
    vectors = {p["id"]: p["world_b"] for p in preview["points"]}
    # The protected evaluator compares geometry. Candidate process only receives these vectors.
    baseline = np.array(list(vectors.values()))
    base_occupancy = len({tuple(np.floor((v + 1) * 8).astype(int)) for v in baseline})
    results = []
    for i, quantile in enumerate((0.99 - .005 * variation, 0.97 - .005 * variation, 0.95 - .005 * variation), 1):
        path = cycle / f"code-{i}"
        path.mkdir(exist_ok=True)
        if (path / "manifest.json").exists():
            prior = json.loads((path / "manifest.json").read_text())
            if prior.get("reason") != "sandbox execution failed; see stderr.log":
                results.append(prior)
                continue
        if time.monotonic() > limit:
            break
        # Syntax-aware mutation of one expression in the project function.
        candidate = original.replace("np.max(np.abs(matrix), axis=0)", f"np.quantile(np.abs(matrix), {quantile}, axis=0)")
        if candidate == original or not ast.parse(candidate).body:
            raise RuntimeError("Expected AST mutation target not found")
        worker = 'import json\nimport numpy as np\nfrom pathlib import Path\n' + candidate + '\n' + 'root=Path(__file__).parent\ndata=json.loads((root/"input.json").read_text())\nresult=_fit_3d(data["index"], {k:np.array(v) for k,v in data["vectors"].items()})\n(root/"output.json").write_text(json.dumps(result))\n'
        (path / "candidate.py").write_text(worker)
        (path / "input.json").write_text(json.dumps({"index": [{"id": p["id"], "split": p["split"]} for p in preview["points"]], "vectors": vectors}))
        (path / "change.diff").write_text("".join(difflib.unified_diff(original.splitlines(True), candidate.splitlines(True), fromfile="src/acoustic_lab/experience.py", tofile="candidate/experience.py")))
        profile = '(version 1)(deny default)(allow process*)(allow file-read*)(deny file-read* (subpath "' + str(SOURCE) + '"))(deny file-read* (subpath "' + str(ROOT / 'src') + '"))(allow sysctl-read)(allow file-write* (subpath "' + str(path) + '"))(allow file-write* (literal "/dev/null"))(deny network*)'
        args = ["sandbox-exec", "-p", profile, sys.executable, "-I", str(path / "candidate.py")]
        started = time.monotonic()
        with (path / "stdout.log").open("w") as out, (path / "stderr.log").open("w") as err:
            proc = subprocess.Popen(args, cwd=path, env={"PATH": "/usr/bin:/bin:/opt/homebrew/bin", "PYTHONDONTWRITEBYTECODE": "1", "OPENBLAS_NUM_THREADS": "2", "TMPDIR": str(path)}, stdout=out, stderr=err, start_new_session=True)
            while proc.poll() is None:
                if (LAB / "STOP").exists() or time.monotonic() - started > min(20, limit - started) or rss_bytes(proc.pid) > 1024**3:
                    os.killpg(proc.pid, signal.SIGKILL)
                    proc.wait()
                    break
                time.sleep(0.1)
        ok = proc.returncode == 0 and (path / "output.json").exists()
        metrics = {}
        if ok:
            coords = np.array(list(json.loads((path / "output.json").read_text()).values()))
            occupancy = len({tuple(np.floor((v + 1) * 8).astype(int)) for v in coords})
            clipped = float(np.mean(np.abs(coords) >= 0.999999))
            metrics = {"voxel_occupancy": occupancy, "baseline_occupancy": base_occupancy, "clipped_fraction": clipped, "finite": bool(np.isfinite(coords).all()), "within_bounds": bool(np.abs(coords).max() <= 1.000001)}
        passed = ok and metrics["voxel_occupancy"] > base_occupancy and metrics["clipped_fraction"] <= 0.05 and metrics["finite"] and metrics["within_bounds"]
        result = {"line": "code", "candidate": i, "seed": None, "target_metric": "increase 3D voxel occupancy without >5% clipped coordinates", "mutation": f"quantile={quantile}", "diff_sha256": sha(path / "change.diff"), "metrics": metrics, "status": "awaiting_human_approval" if passed else "rejected", "reason": "code cannot enter active version automatically" if passed else "metric gate failed" if ok else "sandbox execution failed; see stderr.log"}
        write_json(path / "manifest.json", result)
        results.append(result)
    return results


def model_candidates(cycle: Path, limit: float, sequence: int) -> list[dict]:
    results = []
    for i in range(1, 4):
        path = cycle / f"model-{i}"
        path.mkdir(exist_ok=True)
        if (path / "manifest.json").exists():
            results.append(json.loads((path / "manifest.json").read_text()))
            continue
        if time.monotonic() > limit:
            break
        seed = 2026 + sequence * 3 + i
        write_json(path / "request.json", {"seed": seed, "source": str(SOURCE), "epochs": 6})
        worker = run_worker("model", path, min(60, max(1, limit - time.monotonic())))
        val = worker.get("validation", {})
        gain = 1 - val.get("model_mse", float("inf")) / val.get("persistence_mse", 1)
        result = {"line": "model", "candidate": i, "seed": seed, "worker": worker, "validation_gain": gain, "status": "eligible_for_group_gate" if gain >= 0.05 and worker["exit_code"] == 0 else "rejected", "reason": "synthetic validation gain >=5%; needs three-seed test gate" if gain >= 0.05 and worker["exit_code"] == 0 else "validation gain below 5% or incomplete"}
        write_json(path / "manifest.json", result)
        results.append(result)
    return results


def cycle(sequence: int, seconds: float = 60) -> dict:
    frozen = check_baseline()
    if (LAB / "STOP").exists():
        return {"status": "stopped"}
    if not battery_ok():
        return {"status": "skipped_battery"}
    if size_bytes(ROOT / "artifacts") > MAX_BYTES:
        return {"status": "skipped_disk_cap"}
    path = LAB / f"cycle-{sequence:03d}"
    path.mkdir(exist_ok=True)
    started = time.monotonic()
    deadline = started + min(seconds, 600)
    preview = json.loads((PREVIEW / "experience_data.json").read_text())
    # Split time equally; incomplete candidates remain on disk for resumption.
    portion = (deadline - started) / 3
    visual = visual_candidates(preview, path, started + portion, sequence)
    model = model_candidates(path, started + 2 * portion, sequence)
    code = code_candidates(preview, path, deadline, sequence)
    model_gate = {"status": "failed_validation", "reason": "all three independent seeds must improve synthetic persistence by at least 5%"}
    if len(model) == 3 and all(item["status"] == "eligible_for_group_gate" for item in model):
        test_gains = [1 - item["worker"]["test"]["model_mse"] / item["worker"]["test"]["persistence_mse"] for item in model]
        model_gate = {"status": "provisional_eligible" if all(gain >= .05 for gain in test_gains) else "failed_test", "test_gains": test_gains, "scope": "synthetic_only"}
    result = {"sequence": sequence, "at_utc": datetime.now(timezone.utc).isoformat(), "baseline_sha256": sha(LAB / "baseline.json"), "elapsed_seconds": round(time.monotonic() - started, 3), "lines": {"visual_audio": visual, "model": model, "code": code}, "model_group_gate": model_gate, "integration": {"status": "not_run", "reason": "no promoted line winners; human perceptual and code gates pending"}}
    write_json(path / "report.json", result)
    return result


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("command", choices=["baseline", "cycle", "stop", "status"])
    p.add_argument("--sequence", type=int, default=1)
    p.add_argument("--seconds", type=float, default=60)
    args = p.parse_args()
    if args.command == "baseline":
        print(json.dumps(check_baseline(), indent=2))
    elif args.command == "cycle":
        print(json.dumps(cycle(args.sequence, args.seconds), indent=2))
    elif args.command == "stop":
        LAB.mkdir(parents=True, exist_ok=True)
        (LAB / "STOP").touch()
        from .night import unload
        unload()
        print("Stop requested")
    else:
        print(json.dumps({"stopped": (LAB / "STOP").exists(), "reports": sorted(str(p) for p in LAB.glob("cycle-*/report.json"))}, indent=2))


if __name__ == "__main__":
    main()
