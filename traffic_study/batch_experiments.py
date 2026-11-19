"""Run paired controller experiments across traffic-demand levels and random seeds."""

from pathlib import Path
import argparse
import hashlib
import json
import subprocess
import sys
import time
import atexit
import os
from importlib.metadata import version, PackageNotFoundError
from concurrent.futures import ThreadPoolExecutor
from .paper_methods import METHODS, RESEARCH_METHODS, PAPERS
from .dataset import export_dataset

ROOT = Path(__file__).resolve().parents[1]
AVAILABLE = METHODS


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def process_running(pid):
    if os.name == "nt":
        import ctypes
        from ctypes import wintypes

        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        kernel.OpenProcess.restype = wintypes.HANDLE
        kernel.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
        kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        handle = kernel.OpenProcess(0x1000, False, pid)  # Query only; never terminate.
        if not handle:
            return ctypes.get_last_error() != 87  # Access denied is treated as active.
        code = wintypes.DWORD()
        try:
            return not kernel.GetExitCodeProcess(handle, ctypes.byref(code)) or code.value == 259
        finally:
            kernel.CloseHandle(handle)
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def save_json(path, data):
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def experiment_signature():
    # Record the source, network and runtime required for result reuse.
    files = sorted(
        path.relative_to(ROOT).as_posix() for path in (ROOT / "traffic_study").glob("*.py")
    )
    files += ["tan_binh_2026/signals/survey_observations.csv", "tan_binh_2026/tan_binh.net.xml.gz"]
    signature = {name: digest(ROOT / name) for name in files}
    for name in ("libsumo", "traci", "sumolib", "sumo-data", "eclipse-sumo"):
        try:
            signature["package:" + name] = version(name)
        except PackageNotFoundError:
            signature["package:" + name] = None
    return signature


def prepare_scenario(folder, scale, seed, signature):
    from . import run_fixed_time as baseline

    folder.mkdir(parents=True, exist_ok=True)
    metadata = folder / "batch_input.json"
    expected = dict(scale=scale, seed=seed, signature=signature)
    if metadata.exists() and json.loads(metadata.read_text(encoding="utf-8")) == expected:
        return
    baseline.OUT = folder
    baseline.NET = folder / "network_snapshot.net.xml.gz"
    baseline.SEED = seed
    baseline.DEMAND_SCALE = scale
    baseline.NETWORK_BACKGROUND_PER_HOUR = {
        k: int(v * scale * baseline.MAP_DEMAND_MULTIPLIER)
        for k, v in baseline.REFERENCE_MAP_PER_HOUR.items()
    }
    baseline.main(prepare_only=True)
    save_json(metadata, expected)


def worker(args):
    if (args.output / ".pause_requested").exists():
        return
    from .dataset import simulation_input_files
    from . import compare_pressure as comparison

    baseline = comparison.baseline
    scenario = args.output / "inputs" / f"d{args.scale:g}_s{args.seed}"
    signature = experiment_signature()
    plan_path = args.output / "plan.json"
    if plan_path.exists():
        planned = json.loads(plan_path.read_text(encoding="utf-8"))["signature"]
        if {k: v for k, v in planned.items() if k != "end_s"} != signature:
            raise RuntimeError(
                "Source/package version changed during batch. Stop and resume with a fresh plan; do not mix experiments."
            )
    prepare_scenario(scenario, args.scale, args.seed, signature)
    if (args.output / ".pause_requested").exists():
        return
    baseline.OUT = scenario
    baseline.NET = scenario / "network_snapshot.net.xml.gz"
    comparison.OUT = args.output / "runs" / f"d{args.scale:g}_s{args.seed}"
    comparison.OUT.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    result = comparison.run(
        args.method, args.end, args.seed, pause_file=args.output / ".pause_requested"
    )
    result.update(
        demand_scale=args.scale,
        wall_seconds=time.monotonic() - started,
        signature=signature,
        input_hashes={p.name: digest(p) for p in simulation_input_files(scenario)},
    )
    save_json(comparison.OUT / args.method / "result.json", result)


def finish_report(output, plan, signature):
    results = []
    for job in plan:
        path = output / "runs" / job["scenario"] / job["method"] / "result.json"
        if complete_result(path, signature, job["end"]):
            results.append(json.loads(path.read_text(encoding="utf-8")))
    research = [r for r in results if r["method"] in RESEARCH_METHODS]
    baseline = [r for r in results if r["method"] == "fixed_time"]
    affected = [r for r in results if r.get("collisions", 0) or r.get("teleports", 0)]
    unfinished = sum(not p["completed"] for r in results for p in r["probes"])
    lines = [
        "# Dataset execution report",
        "",
        f"Research runs finished: {len(research)}. Fixed-time reference runs finished: {len(baseline)}.",
        f"Total finished: {len(results)}/{len(plan)}. Runs with collision/teleport: {len(affected)}. Unfinished probes: {unfinished}.",
        "",
        "Execution completeness and scientific validity are separate. Invalid/censored runs are kept in raw data.",
        "summary.csv reports valid sample counts; means omit invalid/censored probes and must be read with those counts.",
        "See docs/PAPER_IMPLEMENTATIONS.md for the paper sources and explicit adaptations.",
        "",
        "| Method | Paper year | Finished runs |",
        "|---|---|---:|",
    ]
    for method in dict.fromkeys(j["method"] for j in plan):
        lines.append(
            f"| {method} | {PAPERS.get(method,{}).get('year','baseline')} | {sum(r['method']==method for r in results)} |"
        )
    (output / "EXECUTION_REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def complete_result(path, signature, end):
    try:
        result = json.loads(path.read_text(encoding="utf-8"))
        return (
            result.get("status") == "complete"
            and result.get("signature") == signature
            and result.get("simulation_end_s") == end
        )
    except (OSError, ValueError):
        return False


def run_case(args, scale, seed, methods):
    if (args.output / ".pause_requested").exists():
        return 0
    scenario = f"d{scale:g}_s{seed}"
    folder = args.output / "runs" / scenario
    folder.mkdir(parents=True, exist_ok=True)
    command = [
        sys.executable,
        "-X",
        "utf8",
        "-m",
        "traffic_study.batch_experiments",
        "--scenario-worker",
        "--output",
        str(args.output),
        "--scale",
        str(scale),
        "--seed",
        str(seed),
        "--end",
        str(args.end),
        "--methods",
        *methods,
    ]
    if args.technical_check:
        command.append("--technical-check")
    with (folder / "case.log").open("w", encoding="utf-8") as log:
        return subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, cwd=ROOT).returncode


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "tan_binh_2026/dataset_current")
    parser.add_argument("--methods", nargs="+", choices=AVAILABLE, default=list(AVAILABLE))
    parser.add_argument("--scales", nargs="+", type=float, default=[0.1, 0.5, 1.0])
    parser.add_argument("--seeds", nargs="+", type=int, default=list(range(100, 105)))
    parser.add_argument("--end", type=float, default=2400)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument(
        "--technical-check",
        action="store_true",
        help="Allow short runs before probes depart; never a measured dataset.",
    )
    parser.add_argument(
        "--max-runs", type=int, default=0, help="0 runs the complete plan; N limits new runs to N"
    )
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--scenario-worker", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument(
        "--workers",
        type=int,
        default=2,
        help="Independent scenarios in parallel; methods within each scenario run sequentially.",
    )
    parser.add_argument("--method", choices=AVAILABLE, help=argparse.SUPPRESS)
    parser.add_argument("--scale", type=float, help=argparse.SUPPRESS)
    parser.add_argument("--seed", type=int, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if (
        any(s <= 0 for s in args.scales)
        or args.end <= 0
        or (args.end <= 300 and not args.technical_check)
    ):
        parser.error("Demand must be positive and --end must exceed the probe departure at 300 s.")
    if args.workers < 1 or args.max_runs < 0:
        parser.error("--workers must be >=1 and --max-runs >=0")
    if (
        len(set(args.methods)) != len(args.methods)
        or len(set(args.seeds)) != len(args.seeds)
        or len(set(args.scales)) != len(args.scales)
    ):
        parser.error("Methods, seeds and demand scales must be unique.")
    args.output = args.output.resolve()
    # Use a dedicated output folder for batch experiments.
    protected = [ROOT / "tan_binh_2026/comparison", ROOT / "tan_binh_2026/baseline_fixed_time"]
    if any(
        args.output == p or p in args.output.parents or args.output in p.parents for p in protected
    ):
        parser.error("Choose a batch output outside comparison/ and baseline_fixed_time/.")
    args.output.mkdir(parents=True, exist_ok=True)
    previous_plan = args.output / "plan.json"
    if not args.worker and not args.scenario_worker and previous_plan.exists():
        previous = json.loads(previous_plan.read_text(encoding="utf-8"))
        expected_signature = {
            key: value for key, value in previous.get("signature", {}).items() if key != "end_s"
        }
        if expected_signature != experiment_signature():
            parser.error(
                "This folder contains a different experiment version. Choose a new output folder."
            )
        if previous.get("protocol") != "pure_nonrl_v1":
            parser.error(
                "Legacy experiment is preserved. Use a new output folder for the pure non-RL protocol."
            )
    if args.worker:
        worker(args)
        return
    if args.scenario_worker:
        errors = 0
        for method in args.methods:
            if (args.output / ".pause_requested").exists():
                break
            args.method = method
            destination = args.output / "runs" / f"d{args.scale:g}_s{args.seed}" / method
            destination.mkdir(parents=True, exist_ok=True)
            if complete_result(destination / "result.json", experiment_signature(), args.end):
                continue
            try:
                print("START", method, args.scale, args.seed, flush=True)
                worker(args)
                print("DONE", method, flush=True)
            except Exception:
                import traceback

                traceback.print_exc()
                errors += 1
        raise SystemExit(1 if errors else 0)
    if args.execute:
        lock = args.output / ".batch.lock"
        if lock.exists():
            try:
                owner = int(lock.read_text())
            except (OSError, ValueError):
                owner = None
            if owner is not None and not process_running(owner):
                lock.unlink()  # This known lock belongs to a dead batch, not a result file.
        try:
            with lock.open("x", encoding="utf-8") as f:
                f.write(str(os.getpid()))
        except FileExistsError:
            parser.error(
                "This output has a batch lock. Stop the existing batch first; remove .batch.lock only after confirming its process has ended."
            )

        def release_lock():
            if lock.exists() and lock.read_text() == str(os.getpid()):
                lock.unlink()

        atexit.register(release_lock)
        (args.output / ".pause_requested").unlink(missing_ok=True)
    elif (args.output / ".batch.lock").exists():
        parser.error("A batch is running here; do not overwrite its plan.")
    signature = experiment_signature()
    signature["end_s"] = args.end
    # Worker stores source hashes; horizon checked separately on resume.
    source_signature = experiment_signature()
    plan = [
        dict(method=m, scale=d, seed=s, end=args.end, scenario=f"d{d:g}_s{s}")
        for d in args.scales
        for s in args.seeds
        for m in args.methods
    ]
    manifest = dict(
        planned_runs=len(plan),
        methods=args.methods,
        scales=args.scales,
        seeds=args.seeds,
        end_s=args.end,
        signature=signature,
        status="planned",
        comparison_policy="all_four_arrived",
        research_methods=list(RESEARCH_METHODS),
        papers=PAPERS,
        target_note=f'{len(set(args.methods) & set(RESEARCH_METHODS))*len(args.scales)*len(args.seeds)} research runs and {int("fixed_time" in args.methods)*len(args.scales)*len(args.seeds)} fixed-time references.',
        protocol="pure_nonrl_v1",
        distinct_papers=len({p["url"] for p in PAPERS.values()}),
    )
    from . import run_fixed_time as baseline

    manifest["demand_reference"] = dict(
        estimated_corridor_passage_vps_both_directions=baseline.CORRIDOR_OBSERVED_TOTAL_VPS,
        reference_corridor_related_requested_vph=baseline.REFERENCE_CORRIDOR_DEMAND_VPH,
        observation_duration_s=baseline.OBSERVATION_DURATION_S,
        corridor_vph_forward=0,
        reverse_ratio=baseline.REVERSE_DEMAND_RATIO,
        corridor_vph_reverse=0,
        background_vph=sum(baseline.REFERENCE_MAP_PER_HOUR.values())
        * baseline.MAP_DEMAND_MULTIPLIER,
        background_multiplier=baseline.MAP_DEMAND_MULTIPLIER,
        total_requested_vph=baseline.REFERENCE_TOTAL_DEMAND_VPH,
        direct_corridor_share=baseline.DIRECT_CORRIDOR_SHARE,
        source="Map-wide ordinary traffic; four tracked corridor journeys. Passage target estimated from a ten-minute video; total map demand is a separate assumption.",
    )
    manifest["run_kind"] = "technical_check" if args.technical_check else "experiment"
    save_json(args.output / "plan.json", manifest)
    print(
        f"Plan: {len(args.methods)} methods × {len(args.scales)} demand levels × {len(args.seeds)} seeds = {len(plan)} runs",
        flush=True,
    )
    if not args.execute:
        return
    if args.workers > 1:
        cases = []
        remaining_limit = args.max_runs or len(plan)
        for scale in args.scales:
            for seed in args.seeds:
                scenario = f"d{scale:g}_s{seed}"
                pending = [
                    m
                    for m in args.methods
                    if not complete_result(
                        args.output / "runs" / scenario / m / "result.json",
                        source_signature,
                        args.end,
                    )
                ]
                chosen = pending[:remaining_limit]
                if chosen:
                    cases.append((scale, seed, chosen))
                    remaining_limit -= len(chosen)

        def checkpoint(status):
            completed = sum(
                complete_result(
                    args.output / "runs" / job["scenario"] / job["method"] / "result.json",
                    source_signature,
                    args.end,
                )
                for job in plan
            )
            export_dataset(args.output)
            manifest.update(
                status="complete" if completed == len(plan) else status, completed_runs=completed
            )
            save_json(args.output / "plan.json", manifest)
            return completed

        checkpoint("running")
        failed_cases = []
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            tasks = {pool.submit(run_case, args, d, s, ms): (d, s, ms) for d, s, ms in cases}
            done = set()
            while len(done) < len(tasks):
                time.sleep(5)
                for task, case in tasks.items():
                    if task.done() and task not in done:
                        done.add(task)
                        code = task.result()
                        if code:
                            failed_cases.append(dict(scale=case[0], seed=case[1], exit_code=code))
                        manifest["failed_cases"] = failed_cases
                        print("CASE", case[:2], "exit", code, flush=True)
                total = checkpoint("running")
                if any(t.done() for t in tasks):
                    (
                        print(f"Progress {total}/{len(plan)}", flush=True)
                        if len(done) != getattr(args, "last_done", -1)
                        else None
                    )
                    args.last_done = len(done)
        checkpoint("incomplete")
        finish_report(args.output, plan, source_signature)
        return
    completed = launched = failures = 0
    for index, job in enumerate(plan, 1):
        if (args.output / ".pause_requested").exists():
            break
        folder = args.output / "runs" / job["scenario"] / job["method"]
        result_path = folder / "result.json"
        old = json.loads(result_path.read_text(encoding="utf-8")) if result_path.exists() else {}
        if (
            old.get("status") == "complete"
            and old.get("signature") == source_signature
            and old.get("simulation_end_s") == args.end
        ):
            completed += 1
            continue
        if args.max_runs and launched >= args.max_runs:
            break
        folder.mkdir(parents=True, exist_ok=True)
        print(f"[{index}/{len(plan)}] {job}", flush=True)
        command = [
            sys.executable,
            "-X",
            "utf8",
            "-m",
            "traffic_study.batch_experiments",
            "--worker",
            "--output",
            str(args.output),
            "--method",
            job["method"],
            "--scale",
            str(job["scale"]),
            "--seed",
            str(job["seed"]),
            "--end",
            str(args.end),
        ]
        if args.technical_check:
            command.append("--technical-check")
        with (folder / "worker.log").open("w", encoding="utf-8") as log:
            proc = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, cwd=ROOT)
        launched += 1
        failures += int(proc.returncode != 0)
        completed += int(complete_result(result_path, source_signature, args.end))
        export_dataset(args.output)
        manifest.update(status="running", completed_runs=completed, failed_runs=failures)
        save_json(args.output / "plan.json", manifest)
    manifest.update(
        status=(
            "complete" if completed == len(plan)
            else "paused" if (args.output / ".pause_requested").exists()
            else "incomplete"
        ),
        completed_runs=completed,
        failed_runs=failures,
    )
    export_dataset(args.output)
    save_json(args.output / "plan.json", manifest)
    finish_report(args.output, plan, source_signature)


if __name__ == "__main__":
    main()
