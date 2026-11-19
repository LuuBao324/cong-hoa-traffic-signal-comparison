"""Resume only missing runs of the saved plan. Run manually when ready."""

from pathlib import Path
import argparse
import json
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from traffic_study.batch_experiments import experiment_signature, process_running



def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", default="dataset_current")
    args = parser.parse_args()
    if Path(args.source).name != args.source:
        parser.error("Use a dataset folder name inside tan_binh_2026.")
    folder = ROOT / "tan_binh_2026" / args.source
    if not (folder / "plan.json").exists():
        parser.error("Create an experiment plan with batch_experiments.py first.")
    plan = json.loads((folder / "plan.json").read_text(encoding="utf-8"))
    expected = {k: v for k, v in plan["signature"].items() if k != "end_s"}
    if experiment_signature() != expected:
        raise SystemExit(
            "Source/network/SUMO signature changed. Resume refused to avoid mixing versions."
        )
    lock = folder / ".batch.lock"
    if lock.exists() and process_running(int(lock.read_text())):
        raise SystemExit("Batch is already running.")
    command = [
        sys.executable,
        "-X",
        "utf8",
        str(ROOT / "batch_experiments.py"),
        "--execute",
        "--workers",
        "4",
        "--output",
        str(folder),
        "--end",
        str(plan["end_s"]),
        "--methods",
        *plan["methods"],
        "--scales",
        *map(str, plan["scales"]),
        "--seeds",
        *map(str, plan["seeds"]),
    ]
    subprocess.run(command, cwd=ROOT, check=True)
    subprocess.run(
        [
            sys.executable,
            "-X",
            "utf8",
            str(ROOT / "scripts/finalize_dataset.py"),
            "--source",
            folder.name,
        ],
        cwd=ROOT,
        check=True,
    )


if __name__ == "__main__":
    main()
