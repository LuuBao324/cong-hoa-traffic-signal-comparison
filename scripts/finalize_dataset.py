"""Wait for the owned batch to finish, then audit real outputs. Does not run simulations."""

from pathlib import Path
import argparse
import json
import subprocess
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from traffic_study.dataset import BASE, sources


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", choices=sources(), default="dataset_pure_nonrl")
    parser.add_argument("--wait", action="store_true")
    args = parser.parse_args()
    folder = BASE / args.source
    while True:
        try:
            plan = json.loads((folder / "plan.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            plan = {}
        if plan.get("status") in ("complete", "incomplete"):
            break
        if not args.wait:
            print("Batch is not finished; no final dataset claimed.", flush=True)
            return
        time.sleep(20)
    from recover_finished_results import recover

    recovery = recover(folder)
    (folder / "RESULT_RECOVERY.json").write_text(json.dumps(recovery, indent=2), encoding="utf-8")
    if recovery["recovered"]:
        from traffic_study.batch_experiments import (
            complete_result,
            export_dataset,
            finish_report,
            save_json,
        )

        signature = {k: v for k, v in plan["signature"].items() if k != "end_s"}
        jobs = [
            dict(method=m, scale=d, seed=s, end=plan["end_s"], scenario=f"d{d:g}_s{s}")
            for d in plan["scales"]
            for s in plan["seeds"]
            for m in plan["methods"]
        ]
        finished = sum(
            complete_result(
                folder / "runs" / j["scenario"] / j["method"] / "result.json", signature, j["end"]
            )
            for j in jobs
        )
        plan.update(
            completed_runs=finished, status="complete" if finished == len(jobs) else "incomplete"
        )
        export_dataset(folder)
        finish_report(folder, jobs, signature)
        save_json(folder / "plan.json", plan)
    from traffic_study.dataset import export_dataset

    export_dataset(folder)
    process = subprocess.run(
        [
            sys.executable,
            "-X",
            "utf8",
            str(Path(__file__).resolve().parent / "validate_dataset.py"),
            "--source",
            args.source,
        ]
    )
    audit = json.loads((folder / "acceptance.json").read_text(encoding="utf-8"))
    status = dict(
        execution_complete=plan.get("status") == "complete",
        planned_runs=plan.get("planned_runs"),
        finished_runs=plan.get("completed_runs"),
        accepted=audit["accepted"],
        actual_research_runs=audit["actual_research_runs"],
        note="Execution complete does not mean all probes arrived or all simulations are scientifically valid.",
        audit_exit_code=process.returncode,
    )
    (folder / "FINAL_STATUS.json").write_text(json.dumps(status, indent=2), encoding="utf-8")
    print(json.dumps(status, indent=2), flush=True)


if __name__ == "__main__":
    main()
