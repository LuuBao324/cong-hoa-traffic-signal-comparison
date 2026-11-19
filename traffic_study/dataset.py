"""Dataset assembly from recorded SUMO runs and tracked journeys."""

from pathlib import Path
import csv
import io
import json
import math
import hashlib
import statistics
from itertools import combinations
import xml.etree.ElementTree as ET
from functools import lru_cache

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "tan_binh_2026"
SCHEMA = {
    "run_id": ("provenance", "One simulation run; four probes belong to the same run"),
    "scenario": ("provenance", "Shared demand and seed input configuration"),
    "probe_id": ("provenance", "Tracked vehicle identifier"),
    "method": ("input", "Controller, not a learned feature"),
    "is_reference": ("provenance", "True for the extra shared fixed-time baseline"),
    "backend": ("provenance", "Simulator API/backend"),
    "engine_version": ("provenance", "Actual simulator version reported by the running backend"),
    "simulation_step_s": ("provenance", "Numerical simulation step length in seconds"),
    "stop_reason": ("quality", "All tracked probes arrived, or simulation guard reached"),
    "phase_switches": (
        "outcome",
        "Controller switches across the network up to stop; unequal windows",
    ),
    "controller_exercised": (
        "quality",
        "False for QD runs that only used the initial/fallback plan",
    ),
    "demand_scale": ("input", "Demand multiplier; assumed, not observed traffic"),
    "seed": ("provenance", "Paired random seed; not a traffic measurement"),
    "vehicle_type": ("input", "Probe class"),
    "vehicle_movement_model": ("input", "Recorded movement model; unspecified for legacy runs"),
    "lane_change_model": ("input", "Recorded SUMO lane-changing model"),
    "route_variant": ("input", "Fixed center/outer probe path"),
    "corridor_vph_per_direction": ("input", "Explicitly assigned corridor background vehicles/hour/direction"),
    "corridor_requested_vph_forward": (
        "input",
        "Explicitly assigned corridor background vehicles/hour towards Truong Chinh",
    ),
    "corridor_requested_vph_reverse": (
        "input",
        "Explicitly assigned corridor background vehicles/hour in the opposite direction",
    ),
    "map_requested_vph": ("input", "Requested background vehicles/hour, whole map"),
    "corridor_related_requested_vph": ("input", "Requested journeys/hour using any Cong Hoa segment; includes side-road entry and exit journeys"),
    "corridor_related_generated_vehicles": ("input", "Generated ordinary journeys using any Cong Hoa segment during the demand window"),
    "map_generated_vehicles": (
        "input",
        "Generated background vehicles during demand window; not actually inserted",
    ),
    "map_generation_ratio": (
        "quality",
        "Generated / requested background vehicles during demand window; routing losses, not completion rate",
    ),
    "demand_duration_s": ("input", "Demand generation window (s)"),
    "probe_requested_depart_s": ("input", "Scheduled probe departure (s)"),
    "motorcycle_share": ("input", "Requested corridor motorcycle proportion"),
    "car_share": ("input", "Requested corridor passenger-car proportion"),
    "truck_share": ("input", "Requested corridor truck proportion"),
    "bus_share": ("input", "Requested corridor bus proportion"),
    "travel_time_s": ("outcome", "Actual insertion to arrival; excludes departure delay"),
    "waiting_time_s": ("outcome", "Waiting within trip, already part of travel time"),
    "depart_delay_s": ("outcome", "Delay before insertion; separate from travel time"),
    "route_length_m": ("outcome", "Distance actually traveled from SUMO tripinfo (m)"),
    "mean_speed_kmh": ("outcome", "Actual route length / trip duration × 3.6"),
    "time_loss_s": ("outcome", "SUMO timeLoss, not equal to waitingTime"),
    "waiting_count": ("outcome", "SUMO waitingCount"),
    "collisions": ("quality", "Whole-run collision count up to stop"),
    "teleports": ("quality", "Whole-run teleport count up to stop"),
    "completed": ("quality", "Probe arrival recorded"),
    "censored": ("quality", "Probe has no recorded arrival at experiment stop"),
    "departed": ("quality", "Probe was actually inserted into the network"),
    "valid_for_comparison": (
        "quality",
        "Eligibility under the saved comparison policy; all_four_arrived permits runs with flagged events",
    ),
    "clean_run": ("quality", "Original strict check including zero whole-run collisions and teleports"),
    "all_four_arrived": ("quality", "All four distinct tracked vehicles recorded positive completed trip durations"),
    "probe_teleported": ("quality", "Tracked vehicle named in a teleport warning; blank if simulator log is unavailable"),
    "probe_collision": ("quality", "Tracked vehicle named in a collision warning; blank if simulator log is unavailable"),
    "paired_valid": ("quality", "Valid probe and fixed-time reference with matching input hashes"),
    "improvement_vs_fixed_percent": ("outcome", "Paired travel-time reduction; positive is faster"),
    "network_sha256": ("provenance", "Network content version"),
    "input_sha256": ("provenance", "Canonical digest of all frozen simulation input hashes"),
    "actual_end_s": ("provenance", "Actual observation horizon for this method"),
    "inserted_network_vehicles": ("quality", "Vehicles actually inserted by run stop"),
    "mean_network_speed_mps": (
        "quality",
        "Network snapshot speed at stop; observation horizons may differ",
    ),
    "halted_network_vehicles": ("quality", "Vehicles halting at experiment stop"),
    "arrived_network_vehicles": (
        "quality",
        "Vehicles arrived by run stop; windows differ, do not rank raw totals",
    ),
    "running_network_vehicles": ("quality", "Vehicles still running when experiment stops"),
    "pending_network_vehicles": ("quality", "Vehicles awaiting insertion when experiment stops"),
}


def simulation_input_files(folder):
    """Enumerate the configuration and files consumed as frozen SUMO inputs."""
    folder = Path(folder)
    config = folder / "fixed_time.sumocfg"
    inputs = ET.parse(config).getroot().find("input")
    files = [config]
    for name in ("net-file", "route-files", "additional-files"):
        for value in inputs.find(name).get("value").split(","):
            path = Path(value)
            files.append(path if path.is_absolute() else folder / path)
    return tuple(dict.fromkeys(files))


def input_digest(hashes, folder=None):
    if not hashes:
        return None
    if folder is not None and (Path(folder) / "fixed_time.sumocfg").exists():
        names = {path.name for path in simulation_input_files(folder)}
        if not names <= hashes.keys():
            return None
        hashes = {name: hashes[name] for name in names}
    return hashlib.sha256(
        json.dumps(hashes, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def valid_pair(first, second):
    return bool(
        first
        and second
        and first.get("valid_for_comparison")
        and second.get("valid_for_comparison")
        and first.get("input_sha256")
        and first["input_sha256"] == second.get("input_sha256")
        and first.get("backend")
        and first["backend"] == second.get("backend")
        and first.get("engine_version")
        and first["engine_version"] == second.get("engine_version")
        and first.get("probe_id") == second.get("probe_id")
        and first.get("vehicle_type") == second.get("vehicle_type")
        and first.get("route_variant") == second.get("route_variant")
        and number(first.get("travel_time_s")) is not None
        and first["travel_time_s"] > 0
        and number(second.get("travel_time_s")) is not None
        and second["travel_time_s"] > 0
    )


def pairwise_rows(rows):
    """Compare all method pairs within the same demand, seed and tracked journey."""
    groups = {}
    for row in rows:
        key = (row["demand_scale"], row["seed"], row["probe_id"])
        groups.setdefault(key, []).append(row)
    result = []
    for group in groups.values():
        for first, second in combinations(sorted(group, key=lambda r: r["method"]), 2):
            paired = valid_pair(first, second)
            result.append(
                dict(
                    demand_scale=first["demand_scale"],
                    seed=first["seed"],
                    probe_id=first["probe_id"],
                    vehicle_type=first["vehicle_type"],
                    route_variant=first["route_variant"],
                    method_a=first["method"],
                    method_b=second["method"],
                    paired_valid=paired,
                    clean_pair=bool(first.get("clean_run") and second.get("clean_run")),
                    collisions_a=first.get("collisions"),
                    collisions_b=second.get("collisions"),
                    teleports_a=first.get("teleports"),
                    teleports_b=second.get("teleports"),
                    probe_teleported_a=first.get("probe_teleported"),
                    probe_teleported_b=second.get("probe_teleported"),
                    travel_time_a_s=first.get("travel_time_s"),
                    travel_time_b_s=second.get("travel_time_s"),
                    difference_a_minus_b_s=(
                        first["travel_time_s"] - second["travel_time_s"] if paired else None
                    ),
                    improvement_a_vs_b_percent=(
                        100
                        * (second["travel_time_s"] - first["travel_time_s"])
                        / second["travel_time_s"]
                        if paired
                        else None
                    ),
                )
            )
    return result


def read_json(path, default=None):
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return {} if default is None else default


def sources():
    return sorted(p.name for p in BASE.iterdir() if p.is_dir() and (p / "plan.json").exists())


def number(value):
    try:
        value = float(value)
        return value if math.isfinite(value) else None
    except (ValueError, TypeError):
        return None


@lru_cache(maxsize=2048)
def probe_trips(filename, modified_ns, size):
    """Cache immutable completed XML; refresh when file changes during a run."""
    trips = {}
    for _, element in ET.iterparse(filename, events=("end",)):
        if element.tag == "tripinfo":
            if element.get("id", "").startswith("probe_"):
                trips[element.get("id")] = dict(element.attrib)
            element.clear()
    return trips


def build_dataset(name):
    if name not in sources():
        raise ValueError("Unknown batch dataset")
    folder = BASE / name
    plan = read_json(folder / "plan.json")
    arrival_policy = plan.get("comparison_policy") == "all_four_arrived"
    rows, runs, issues = [], [], []
    allowed = set(plan.get("methods", []))
    for path in sorted((folder / "runs").glob("*/*/result.json")):
        result = read_json(path)
        method = result.get("method")
        scenario = path.parent.parent.name
        if method not in allowed:
            continue
        inputs = folder / "inputs" / scenario
        info = read_json(inputs / "scenario.json")
        scale = result.get("demand_scale", info.get("demand_scale"))
        if scale not in plan.get("scales", []) or result.get("seed") not in plan.get("seeds", []):
            continue
        if result.get("simulation_end_s") != plan.get("end_s"):
            issues.append(f"{scenario}/{method}: horizon differs from plan; excluded")
            continue
        expected_signature = {k: v for k, v in plan.get("signature", {}).items() if k != "end_s"}
        if result.get("signature") != expected_signature:
            issues.append(f"{scenario}/{method}: source version differs from plan; excluded")
            continue
        if result.get("status") != "complete":
            continue
        trips = {}
        try:
            trip_path = path.parent / "tripinfo.xml"
            stat = trip_path.stat()
            trips = probe_trips(str(trip_path), stat.st_mtime_ns, stat.st_size)
        except (OSError, ET.ParseError):
            issues.append(f"{scenario}/{method}: tripinfo unavailable; extra metrics left blank")
        signature = result.get("signature", {})
        key = f"{scenario}/{method}"
        probes = result.get("probes", [])
        all_arrived = (
            len(probes) == 4
            and len({p.get("probe_id") for p in probes}) == 4
            and all(p.get("completed") and (number(p.get("travel_time_s")) or 0) > 0 for p in probes)
        )
        clean_run = (
            bool(probes)
            and all(p.get("valid_for_comparison") for p in probes)
            and result.get("collisions") == 0
            and result.get("teleports") == 0
        )
        log_path = path.parent / "sumo.log"
        event_lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines() if log_path.exists() else None
        runs.append(
            dict(
                run_id=key,
                method=method,
                demand_scale=scale,
                seed=result.get("seed"),
                collisions=result.get("collisions"),
                teleports=result.get("teleports"),
                actual_end_s=result.get("actual_end_s"),
                status=result.get("status"),
                valid=all_arrived if arrival_policy else clean_run,
                clean_run=clean_run,
            )
        )
        for probe in probes:
            trip = trips.get(probe["probe_id"], {})
            duration = number(probe.get("travel_time_s"))
            length = number(trip.get("routeLength")) if probe.get("completed") else None
            row = dict(run_id=key, scenario=scenario, **probe)
            row.update(
                demand_scale=scale,
                seed=result.get("seed"),
                is_reference=method == "fixed_time",
                backend=result.get("backend"),
                engine_version=(result.get("engine_version") or [None])[-1],
                simulation_step_s=result.get("simulation_step_s"),
                stop_reason=result.get("stop_reason"),
                phase_switches=result.get("phase_switches"),
                controller_exercised=result.get("controller_exercised"),
                corridor_vph_per_direction=info.get("corridor_vehicles_per_hour_per_direction"),
                corridor_requested_vph_forward=info.get(
                    "corridor_requested_vph_forward",
                    info.get("corridor_vehicles_per_hour_per_direction"),
                ),
                corridor_requested_vph_reverse=info.get(
                    "corridor_requested_vph_reverse",
                    info.get("corridor_vehicles_per_hour_per_direction"),
                ),
                map_requested_vph=(
                    sum(info["network_background_requested_per_hour"].values())
                    if "network_background_requested_per_hour" in info
                    else None
                ),
                corridor_related_requested_vph=info.get("corridor_related_requested_vph"),
                corridor_related_generated_vehicles=(
                    sum(info["corridor_related_generated_vehicles"].values())
                    if "corridor_related_generated_vehicles" in info else None
                ),
                map_generated_vehicles=(
                    sum(info["network_background_generated"].values())
                    if "network_background_generated" in info
                    else None
                ),
                vehicle_movement_model=info.get("vehicle_movement_model"),
                lane_change_model=info.get("lane_change_model"),
                demand_duration_s=info.get("demand_duration_s"),
                probe_requested_depart_s=info.get("requested_depart_s"),
                **{
                    f"{kind}_share": info.get("corridor_mix", {}).get(kind)
                    for kind in ["motorcycle", "car", "truck", "bus"]
                },
                route_length_m=length,
                mean_speed_kmh=(
                    length / duration * 3.6
                    if length is not None and duration and duration > 0
                    else None
                ),
                time_loss_s=number(trip.get("timeLoss")) if probe.get("completed") else None,
                waiting_count=number(trip.get("waitingCount")) if probe.get("completed") else None,
                collisions=result.get("collisions"),
                teleports=result.get("teleports"),
                completed=bool(probe.get("completed")),
                censored=not bool(probe.get("completed")),
                departed=bool(
                    probe.get("completed")
                    or (number(trip.get("depart")) is not None and number(trip.get("depart")) >= 0)
                ),
                all_four_arrived=all_arrived,
                clean_run=clean_run,
                probe_teleported=(
                    any(f"Teleporting vehicle '{probe['probe_id']}'" in line for line in event_lines)
                    if event_lines is not None else None
                ),
                probe_collision=(
                    any("collision" in line.lower() and f"'{probe['probe_id']}'" in line for line in event_lines)
                    if event_lines is not None else None
                ),
                valid_for_comparison=all_arrived if arrival_policy else bool(
                    probe.get("valid_for_comparison")
                    and probe.get("completed")
                    and duration is not None
                    and duration > 0
                    and result.get("collisions") == 0
                    and result.get("teleports") == 0
                ),
                actual_end_s=result.get("actual_end_s"),
                wall_seconds=result.get("wall_seconds"),
                network_sha256=info.get(
                    "network_sha256", signature.get("tan_binh_2026/tan_binh.net.xml.gz")
                ),
                input_sha256=input_digest(result.get("input_hashes"), inputs),
                _input_hashes=result.get("input_hashes"),
            )
            requested = row["map_requested_vph"]
            window = row["demand_duration_s"]
            generated = row["map_generated_vehicles"]
            row["map_generation_ratio"] = (
                generated / (requested * window / 3600)
                if requested and window and generated is not None
                else None
            )
            row["arrived_network_vehicles"] = result.get("arrived")
            row["running_network_vehicles"] = result.get("running")
            row["pending_network_vehicles"] = result.get("pending")
            row["inserted_network_vehicles"] = result.get("inserted")
            row["mean_network_speed_mps"] = result.get("mean_network_speed_mps")
            row["halted_network_vehicles"] = result.get("halted_network_vehicles")
            rows.append(row)
    refs = {
        (r["scenario"], r["seed"], r["probe_id"]): r for r in rows if r["method"] == "fixed_time"
    }
    for row in rows:
        ref = refs.get((row["scenario"], row["seed"], row["probe_id"]))
        paired = valid_pair(ref, row)
        row["paired_valid"] = paired
        row["improvement_vs_fixed_percent"] = (
            100 * (ref["travel_time_s"] - row["travel_time_s"]) / ref["travel_time_s"]
            if paired
            else None
        )
    for row in rows:
        del row["_input_hashes"]
    missing = {field: sum(r.get(field) is None for r in rows) for field in SCHEMA}
    if any(len([r for r in rows if r["run_id"] == run["run_id"]]) != 4 for run in runs):
        issues.append("Some runs do not contain exactly four probe records")
    return dict(
        source=name,
        plan=plan,
        rows=rows,
        runs=runs,
        issues=issues,
        export_code_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        schema=[
            dict(name=k, role=v[0], description=v[1], missing=missing[k]) for k, v in SCHEMA.items()
        ],
        notes=[
            f"Comparison policy: {plan.get('comparison_policy', 'strict_quality')}. Quality flags remain recorded independently.",
            "Demand levels are estimated reference inputs.",
            "Runs stop when the tracked vehicles arrive or the time limit is reached.",
            "Four tracked vehicles in one run share the same random seed.",
            "Travel time starts at actual network insertion and excludes departure delay.",
            "Each result records its signal transition policy.",
        ],
    )


def csv_text(rows):
    stream = io.StringIO(newline="")
    if rows:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return stream.getvalue()


def write_csv(path, rows):
    """Publish a complete CSV with a stable union of the available columns."""
    fields = list(dict.fromkeys(key for row in rows for key in row))
    temporary = path.with_suffix(".tmp")
    with temporary.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    temporary.replace(path)


def export_dataset(folder):
    """Write the main dataset, comparison tables and column metadata once."""
    folder = Path(folder).resolve()
    if folder.parent != BASE.resolve():
        raise ValueError("Dataset folders must be directly inside tan_binh_2026.")
    data = build_dataset(folder.name)
    rows = data["rows"]
    write_csv(folder / "dataset.csv", rows)
    write_csv(folder / "pairwise.csv", pairwise_rows(rows))
    groups = {}
    for row in rows:
        key = (row["demand_scale"], row["method"], row["probe_id"])
        groups.setdefault(key, []).append(row)
    summaries = []
    for (scale, method, probe), values in sorted(groups.items()):
        valid = [row["travel_time_s"] for row in values if row["valid_for_comparison"]]
        gains = [row["improvement_vs_fixed_percent"] for row in values if row["paired_valid"]]
        summaries.append(
            dict(
                demand_scale=scale,
                method=method,
                probe_id=probe,
                runs=len(values),
                valid_runs=len(valid),
                invalid_runs=len(values) - len(valid),
                event_affected_runs=sum(bool(row.get("collisions") or row.get("teleports")) for row in values),
                probe_teleported_runs=sum(row.get("probe_teleported") is True for row in values),
                probe_collision_runs=sum(row.get("probe_collision") is True for row in values),
                mean_travel_time_s=statistics.mean(valid) if valid else None,
                std_travel_time_s=statistics.stdev(valid) if len(valid) > 1 else None,
                paired_valid_runs=len(gains),
                mean_paired_improvement_percent=statistics.mean(gains) if gains else None,
            )
        )
    write_csv(folder / "summary.csv", summaries)
    metadata = {key: value for key, value in data.items() if key not in ("rows", "runs")}
    temporary = folder / "dataset_metadata.tmp"
    temporary.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(folder / "dataset_metadata.json")
    return data
