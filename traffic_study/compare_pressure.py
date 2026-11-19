"""Compare fixed-time and the ten registered nonlearning controllers on shared inputs."""

from pathlib import Path
import argparse
import csv
import hashlib
import json
from functools import lru_cache
import xml.etree.ElementTree as ET
import sumolib
import traci
from . import run_fixed_time as baseline
from .pressure_controllers import YELLOW_S, ALL_RED_S, SWITCH_PROTECTION_K
from .paper_methods import METHODS, PAPERS

OUT = baseline.BASE / "comparison"


@lru_cache(maxsize=1)
def read_shared_network(path, modified_ns, size):
    # Independent methods read immutable geometry; parse once per scenario process.
    return sumolib.net.readNet(path)


def write_table(results):
    rows = [dict(p) for result in results for p in result["probes"]]
    references = {r["probe_id"]: r for r in rows if r["method"] == "fixed_time"}
    for row in rows:
        ref = references.get(row["probe_id"])
        row["improvement_vs_fixed_percent"] = (
            round(100 * (ref["travel_time_s"] - row["travel_time_s"]) / ref["travel_time_s"], 2)
            if ref and ref["valid_for_comparison"] and row["valid_for_comparison"]
            else None
        )
    if rows:
        with (OUT / "comparison.csv").open("w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
        # Preserve the per-method measurements when running one method.
        for method in {row["method"] for row in rows}:
            folder = OUT / method
            folder.mkdir(parents=True, exist_ok=True)
            with (folder / "comparison.csv").open("w", newline="", encoding="utf-8-sig") as f:
                writer = csv.DictWriter(f, fieldnames=list(rows[0]))
                writer.writeheader()
                writer.writerows(row for row in rows if row["method"] == method)
    (OUT / "results.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    write_report(rows, results)


def write_report(rows, results):
    """Summarise the recorded end-to-end journeys and run checks."""
    lines = [
        "# Cong Hoa journey comparison",
        "",
        "Travel time starts when a vehicle enters the network and ends at arrival.",
        "",
        "| Method | Vehicle | Route | Travel time (s) | Improvement over Fixed-time (%) | Valid |",
        "|---|---|---|---:|---:|---|",
    ]
    for row in rows:
        lines.append(
            f"| {row['method']} | {row['vehicle_type']} | {row['route_variant']} | "
            f"{row.get('travel_time_s')} | {row.get('improvement_vs_fixed_percent')} | "
            f"{row['valid_for_comparison']} |"
        )
    lines += [
        "",
        "Percentage improvements use completed, valid matching journeys.",
        "Controller sources and adaptations are documented in docs/PURE_NONRL_AUDIT.md.",
        "Demand and vehicle behaviour use the assumptions recorded with the scenario.",
    ]
    (OUT / "REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(
    method, end, seed, gui=False, full_network=False, reporter=None, backend="auto", pause_file=None
):
    global traci
    if gui or backend == "traci":
        import traci
    else:
        try:
            import libsumo as traci
        except ImportError:
            if backend == "libsumo":
                raise
            import traci
    folder = OUT / method
    folder.mkdir(parents=True, exist_ok=True)
    tree = ET.parse(baseline.OUT / "fixed_time.sumocfg")
    inputs = tree.getroot().find("input")
    for tag in ("net-file", "route-files", "additional-files"):
        node = inputs.find(tag)
        node.set(
            "value",
            ",".join(str((baseline.OUT / p).resolve()) for p in node.get("value").split(",")),
        )
    output = tree.getroot().find("output")
    output.find("tripinfo-output").set("value", "tripinfo.xml")
    output.find("summary-output").set("value", "summary.xml")
    tree.getroot().find("time/end").set("value", str(end))
    tree.getroot().find("random_number/seed").set("value", str(seed))
    memory = tree.getroot().find("processing/waiting-time-memory")
    if memory is None:
        memory = ET.SubElement(tree.getroot().find("processing"), "waiting-time-memory")
    memory.set("value", str(end + 10))
    config = folder / "run.sumocfg"
    native = ET.parse(baseline.OUT / "fixed.add.xml")
    for detector in native.getroot().iter():
        if detector.get("file"):
            detector.set("file", str((folder / Path(detector.get("file")).name).resolve()))
    native_file = folder / "controller.add.xml"
    baseline.write_xml(native_file, native.getroot())
    inputs.find("additional-files").set("value", str(native_file.resolve()))
    baseline.write_xml(config, tree.getroot())
    stat = baseline.NET.stat()
    net = (
        read_shared_network(str(baseline.NET), stat.st_mtime_ns, stat.st_size)
        if method != "fixed_time"
        else None
    )
    traci.start(
        [
            baseline.sumo_binary("sumo-gui" if gui else "sumo"),
            "-c",
            str(config),
            "--no-step-log",
            "true",
            "--log",
            str(folder / "sumo.log"),
        ]
        + (["--start", "--delay", "10"] if gui else [])
    )
    controller = None
    engine_version = traci.getVersion()
    simulation_step_s = traci.simulation.getDeltaT()
    departures, delays, live_probes = {}, {}, {}
    collisions_so_far = teleports_so_far = 0
    now = 0
    interrupted = False
    try:
        if method != "fixed_time":
            from .pure_controllers import PureController

            cls = PureController
            controller = cls(traci, net, method)
        while traci.simulation.getMinExpectedNumber() > 0 and traci.simulation.getTime() < end:
            if pause_file is not None and pause_file.exists():
                interrupted = True
                break
            traci.simulationStep()
            now = traci.simulation.getTime()
            departed = traci.simulation.getDepartedIDList()
            for pid in set(departed) & baseline.PROBES.keys():
                departures[pid] = traci.vehicle.getDeparture(pid)
                delays[pid] = traci.vehicle.getDepartDelay(pid)
            collisions_so_far += len(traci.simulation.getCollisions())
            teleports_so_far += len(traci.simulation.getStartingTeleportIDList())
            if controller:
                controller.step(now, departed)
            for pid in set(traci.simulation.getArrivedIDList()) & baseline.PROBES.keys():
                kind, variant = baseline.PROBES[pid]
                live_probes[pid] = dict(
                    method=method,
                    probe_id=pid,
                    vehicle_type=kind,
                    route_variant=variant,
                    completed=True,
                    travel_time_s=round(now - departures[pid], 3),
                    depart_delay_s=delays[pid],
                    waiting_time_s=None,
                    valid_for_comparison=collisions_so_far == 0 and teleports_so_far == 0,
                )
                live = dict(
                    method=method,
                    seed=seed,
                    status="running",
                    actual_end_s=now,
                    collisions=collisions_so_far,
                    teleports=teleports_so_far,
                    probes=list(live_probes.values()),
                    note="Live duration from TraCI; waitingTime reconciled on close.",
                )
                (folder / "result.json").write_text(json.dumps(live, indent=2), encoding="utf-8")
                if reporter:
                    reporter(live)
                print(
                    f'{method}: {pid} arrived at {now:.1f}s, duration={live_probes[pid]["travel_time_s"]:.1f}s',
                    flush=True,
                )
            if not full_network and len(live_probes) == len(baseline.PROBES):
                break  # Stop when all tracked vehicles have arrived.
            if round(now * 5) % 3000 == 0:
                print(f"{method}: {now:.0f}s, running={traci.vehicle.getIDCount()}", flush=True)
    finally:
        traci.close()
    trips = ET.parse(folder / "tripinfo.xml").getroot().findall("tripinfo")
    steps = ET.parse(folder / "summary.xml").getroot().findall("step")
    last = steps[-1] if steps else {}
    completed = [t for t in trips if float(t.get("arrival")) >= 0]
    collisions = max(collisions_so_far, int(last.get("collisions", 0)))
    teleports = max(teleports_so_far, int(last.get("teleports", 0)))
    controller_diagnostics = getattr(controller, "diagnostics", {})
    controller_exercised = (
        controller is None or controller_diagnostics.get("paper_phase_decisions", 0) > 0
    )
    if method == "queue_responsive_2026":
        controller_exercised = (
            controller_exercised and controller_diagnostics.get("cycle_plan_updates", 0) > 0
        )
    probe_rows = []
    for pid, (kind, variant) in baseline.PROBES.items():
        trip = next((t for t in trips if t.get("id") == pid), None)
        arrived = trip is not None and float(trip.get("arrival")) >= 0
        duration = float(trip.get("duration")) if arrived else None
        length = float(trip.get("routeLength")) if arrived else None
        probe_rows.append(
            dict(
                method=method,
                probe_id=pid,
                vehicle_type=kind,
                route_variant=variant,
                completed=arrived,
                censored=not arrived,
                departed=trip is not None and float(trip.get("depart", "-1")) >= 0,
                travel_time_s=duration,
                route_length_m=length,
                mean_speed_kmh=length / duration * 3.6 if duration and length is not None else None,
                time_loss_s=float(trip.get("timeLoss")) if arrived else None,
                waiting_count=int(trip.get("waitingCount")) if arrived else None,
                depart_s=float(trip.get("depart")) if trip is not None else None,
                arrival_s=float(trip.get("arrival")) if arrived else None,
                depart_delay_s=float(trip.get("departDelay")) if trip is not None else None,
                waiting_time_s=float(trip.get("waitingTime")) if trip is not None else None,
                valid_for_comparison=arrived
                and not interrupted
                and collisions == 0
                and teleports == 0
                and controller_exercised,
            )
        )
    gap_option = tree.getroot().find("processing/collision.mingap-factor")
    junction_option = tree.getroot().find("processing/collision.check-junctions")
    result = dict(
        method=method,
        seed=seed,
        simulation_end_s=end,
        actual_end_s=now,
        status="paused" if interrupted else "complete",
        implementation_protocol="pure_nonrl_v1",
        stop_policy="full_network" if full_network else "all_probes_arrived_or_time_limit",
        route_choice="identical frozen routes for every method",
        collisions=collisions,
        teleports=teleports,
        arrived=len(completed),
        inserted=int(last.get("inserted", 0)),
        mean_network_speed_mps=float(last.get("meanSpeed", 0)),
        halted_network_vehicles=int(last.get("halting", 0)),
        running=int(last.get("running", 0)),
        pending=int(last.get("waiting", 0)),
        mean_completed_travel_time_s=sum(float(t.get("duration")) for t in completed)
        / max(1, len(completed)),
        completion_bias_warning="Mean excludes unfinished vehicles; compare throughput and unfinished counts too.",
        controlled_signals=len(controller.signals) if controller else 0,
        phase_switches=controller.switches if controller else None,
        probes=probe_rows,
        stop_reason=(
            "user_pause"
            if interrupted
            else (
                "all_tracked_probes_arrived"
                if len(live_probes) == len(baseline.PROBES)
                else "time_limit_or_network_empty"
            )
        ),
        tracked_probes=list(baseline.PROBES),
        transition_policy=dict(
            mode=(
                "stored_signal_plan"
                if controller is None
                else "explicit_yellow_then_optional_all_red"
            ),
            extra_all_red_s=ALL_RED_S if controller else 0,
            yellow_s=YELLOW_S if controller else "stored_phase_durations",
        ),
        controller_parameters=dict(
            switch_k=SWITCH_PROTECTION_K if method == "switching_loss_mp" else None,
            decision_s=controller.interval if controller else None,
        ),
        paper=PAPERS.get(method),
        controller_diagnostics=controller_diagnostics,
        controller_exercised=controller_exercised,
        backend=traci.__name__,
        engine_version=engine_version,
        simulation_step_s=simulation_step_s,
        collision_policy={
            "minimum_gap_factor": gap_option.get("value") if gap_option is not None else "SUMO default",
            "check_junctions": junction_option.get("value") if junction_option is not None else "SUMO default",
        },
        implementation="SUMO research adaptation, not an exact reproduction of published experiments",
    )
    (folder / "result.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--method", choices=("all",) + METHODS, default="all")
    parser.add_argument("--end", type=float, default=baseline.SIMULATION_END_S)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--gui", action="store_true")
    parser.add_argument("--backend", choices=("auto", "traci", "libsumo"), default="auto")
    parser.add_argument(
        "--full-network",
        action="store_true",
        help="Continue after all probes arrive; default stops after probes.",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Reuse completed methods only when input hashes and seed match.",
    )
    parser.add_argument(
        "--report-only",
        action="store_true",
        help="Export tables/report from existing results without rerunning SUMO.",
    )
    args = parser.parse_args()
    if args.report_only:
        write_table(json.loads((OUT / "results.json").read_text(encoding="utf-8")))
        print("Report:", OUT / "REPORT.md")
        return
    source_hash = hashlib.sha256(baseline.SOURCE_NET.read_bytes()).hexdigest()
    snapshot_hash = hashlib.sha256(baseline.NET.read_bytes()).hexdigest()
    scenario_path = baseline.OUT / "scenario.json"
    scenario = (
        json.loads(scenario_path.read_text(encoding="utf-8")) if scenario_path.exists() else {}
    )
    prepared_source_hash = scenario.get("source_network_sha256", snapshot_hash)
    prepared_snapshot_hash = scenario.get("network_sha256", snapshot_hash)
    if source_hash != prepared_source_hash or snapshot_hash != prepared_snapshot_hash:
        raise RuntimeError("Network changed. Run run_fixed_time.py --prepare first.")
    OUT.mkdir(exist_ok=True)
    previous = (
        json.loads((OUT / "manifest.json").read_text(encoding="utf-8"))
        if (OUT / "manifest.json").exists()
        else {}
    )
    # Replace the interactive comparison exports for this invocation.
    for name in ("comparison.csv", "results.json"):
        (OUT / name).unlink(missing_ok=True)
    manifest = dict(
        network_sha256=snapshot_hash,
        seed=args.seed,
        simulation_end_s=args.end,
        input_hashes={
            p.name: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in [
                baseline.NET,
                baseline.OUT / "fixed.add.xml",
                baseline.OUT / "traffic.rou.xml",
            ]
            + list(baseline.OUT.glob("map_*.rou.xml"))
        },
        methods=METHODS,
        status="running",
    )
    manifest["run_kind"] = (
        "technical_check_before_probe_departure"
        if args.end <= baseline.PROBE_DEPART_S
        else "experiment"
    )
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    results = []
    for method in (METHODS if args.method == "all" else (args.method,)):
        cached_path = OUT / method / "result.json"
        cached = json.loads(cached_path.read_text(encoding="utf-8")) if cached_path.exists() else {}
        if (
            args.resume
            and cached.get("implementation_protocol") == "pure_nonrl_v1"
            and previous.get("input_hashes") == manifest["input_hashes"]
            and cached.get("seed") == args.seed
            and cached.get("status") == "complete"
            and len(cached.get("probes", [])) == len(baseline.PROBES)
            and all(p["completed"] for p in cached["probes"])
            and not args.full_network
        ):
            result = cached
            print("Reuse measured probes:", method, flush=True)
        else:
            result = run(
                method,
                args.end,
                args.seed,
                args.gui,
                args.full_network,
                lambda live: write_table(results + [live]),
                args.backend,
            )
        results.append(result)
        write_table(results)
    manifest["status"] = "complete"
    manifest["all_probes_valid"] = all(
        p["valid_for_comparison"] for r in results for p in r["probes"]
    )
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(results, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
