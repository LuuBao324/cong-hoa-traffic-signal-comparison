"""Run a resumable experiment until a specified local time, then save and pause."""

import argparse
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from traffic_study.batch_experiments import (
    complete_result,
    experiment_signature,
    process_running,
    save_json,
)
from traffic_study.dataset import export_dataset


def stop_process_tree(process):
    """Stop only the batch process started by this supervisor and its children."""
    if process.poll() is not None:
        return
    subprocess.run(
        ["taskkill", "/PID", str(process.pid), "/T", "/F"],
        check=True,
        capture_output=True,
        text=True,
        timeout=15,
    )
    process.wait(timeout=15)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--stop-at", type=datetime.fromisoformat, required=True)
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    if args.stop_at.tzinfo is None:
        parser.error("Include a timezone offset in --stop-at, for example +07:00.")
    deadline = args.stop_at.astimezone(timezone.utc)
    if datetime.now(timezone.utc) >= deadline:
        parser.error("The stop time must be in the future.")
    folder = args.output.resolve()
    if folder.parent != (ROOT / "tan_binh_2026").resolve():
        parser.error("Use an experiment directory directly inside tan_binh_2026.")
    folder.mkdir(exist_ok=True)
    plan_path = folder / "plan.json"
    saved = json.loads(plan_path.read_text(encoding="utf-8")) if plan_path.exists() else {}
    if (
        saved
        and {key: value for key, value in saved["signature"].items() if key != "end_s"}
        != experiment_signature()
    ):
        parser.error("The saved experiment uses another source version. Use a new directory.")
    scales = saved.get("scales", [0.1, 0.5, 1.0])
    seeds = saved.get("seeds", list(range(100, 124)))
    command = [
        sys.executable,
        "-X",
        "utf8",
        str(ROOT / "batch_experiments.py"),
        "--output",
        str(folder),
        "--execute",
        "--workers",
        str(args.workers),
        "--end",
        str(saved.get("end_s", 2400)),
        "--scales",
        *map(str, scales),
        "--seeds",
        *map(str, seeds),
    ]
    # Native workers close SUMO and their XML files during this grace period.
    pause_at = deadline - timedelta(seconds=120)
    pause_file = folder / ".pause_requested"
    log_path = folder / "supervisor.log"
    lock = folder / ".deadline.lock"
    if lock.exists() and not process_running(int(lock.read_text(encoding="utf-8"))):
        lock.unlink()
    with lock.open("x", encoding="utf-8") as stream:
        stream.write(str(os.getpid()))
    process = None
    pause_sent = False
    forced = False
    try:
        with log_path.open("a", encoding="utf-8") as log:
            process = subprocess.Popen(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
            save_json(
                folder / "SCHEDULE.json",
                dict(
                    status="running",
                    supervisor_pid=os.getpid(),
                    batch_pid=process.pid,
                    stop_at=args.stop_at.isoformat(),
                    pause_at=pause_at.isoformat(),
                    workers=args.workers,
                    command=command,
                ),
            )
            print(f"Running batch {process.pid}; stop at {args.stop_at.isoformat()}", flush=True)
            while process.poll() is None:
                now = datetime.now(timezone.utc)
                if now >= pause_at and not pause_sent:
                    pause_file.write_text(args.stop_at.isoformat(), encoding="utf-8")
                    pause_sent = True
                    print("Requested checkpoint and pause.", flush=True)
                if now >= deadline:
                    stop_process_tree(process)
                    forced = True
                    break
                time.sleep(min(2, max(0.01, (deadline - now).total_seconds())))
    except BaseException:
        pause_file.write_text("Supervisor interrupted", encoding="utf-8")
        if process is not None:
            stop_process_tree(process)
        raise
    finally:
        if lock.exists() and lock.read_text(encoding="utf-8") == str(os.getpid()):
            lock.unlink()
    if not plan_path.exists():
        raise RuntimeError(f"The batch did not create a plan. Inspect {log_path}.")
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    signature = {key: value for key, value in plan["signature"].items() if key != "end_s"}
    finished = sum(
        complete_result(path, signature, plan["end_s"])
        for path in (folder / "runs").glob("*/*/result.json")
    )
    paused = pause_sent or forced
    plan.update(
        completed_runs=finished,
        status=(
            "complete" if finished == plan["planned_runs"] else "paused" if paused else "incomplete"
        ),
    )
    save_json(plan_path, plan)
    batch_lock = folder / ".batch.lock"
    if batch_lock.exists() and batch_lock.read_text() == str(process.pid):
        batch_lock.unlink()
    # Completed raw results are already checkpointed. Rebuild derived tables if time permits.
    if datetime.now(timezone.utc) < deadline - timedelta(seconds=20):
        export_dataset(folder)
    status = dict(
        status=plan["status"],
        completed_runs=finished,
        planned_runs=plan["planned_runs"],
        stopped_at=datetime.now(timezone.utc).isoformat(),
        stop_at=args.stop_at.isoformat(),
        forced_stop=forced,
        batch_exit_code=process.returncode,
        resume_command=f".\\.venv\\Scripts\\python.exe -X utf8 scripts/resume_dataset.py --source {folder.name}",
    )
    save_json(folder / "SCHEDULE.json", status)
    print(json.dumps(status, indent=2), flush=True)


if __name__ == "__main__":
    main()
