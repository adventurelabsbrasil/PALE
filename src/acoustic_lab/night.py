"""One bounded overnight tick; launchd invokes it every 30 minutes."""

from __future__ import annotations

from datetime import datetime
import fcntl
import json
import os
import subprocess
import time
from zoneinfo import ZoneInfo

from .evolution import LAB, cycle, write_json


START = datetime(2026, 10, 9, 23, 0, tzinfo=ZoneInfo("America/Sao_Paulo"))
END = datetime(2026, 10, 10, 9, 0, tzinfo=ZoneInfo("America/Sao_Paulo"))
TOTAL_SECONDS = 600
PER_TICK_SECONDS = 60
MAX_CYCLES = 20
LABEL = "com.adventurelabs.acoustic-lab-exp-001-night"


def unload(wait: bool = True) -> None:
    lock_path = LAB / "night.lock"
    if wait and lock_path.exists():
        with lock_path.open("w") as lock:
            for _ in range(30):
                try:
                    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    fcntl.flock(lock, fcntl.LOCK_UN)
                    break
                except BlockingIOError:
                    time.sleep(0.1)
    subprocess.run(["launchctl", "bootout", f"gui/{os.getuid()}/{LABEL}"], capture_output=True)


def tick() -> dict:
    LAB.mkdir(parents=True, exist_ok=True)
    os.nice(10)
    with (LAB / "night.lock").open("w") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return {"status": "already_running"}
        now = datetime.now(ZoneInfo("America/Sao_Paulo"))
        if not START <= now < END:
            if now >= END:
                unload(wait=False)
            return {"status": "outside_window", "at": now.isoformat()}
        if (LAB / "STOP").exists():
            unload(wait=False)
            return {"status": "stopped"}
        state_path = LAB / "night-state.json"
        state = json.loads(state_path.read_text()) if state_path.exists() else {"cycles": 0, "spent_seconds": 0.0}
        if state["cycles"] >= MAX_CYCLES or state["spent_seconds"] >= TOTAL_SECONDS:
            unload(wait=False)
            return {"status": "budget_exhausted", **state}
        seq = 100 + state["cycles"] + 1
        allowance = min(PER_TICK_SECONDS, TOTAL_SECONDS - state["spent_seconds"])
        result = cycle(seq, allowance)
        state["cycles"] += 1
        state["spent_seconds"] += result.get("elapsed_seconds", 0.0)
        state["last_status"] = result.get("status", "complete")
        state["last_at"] = now.isoformat()
        write_json(state_path, state)
        return {"status": "complete", **state}


if __name__ == "__main__":
    print(json.dumps(tick(), indent=2))
