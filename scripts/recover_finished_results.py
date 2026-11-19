"""Promote fully written worker results stranded by Windows rename locks.

Never synthesizes results or changes signatures. Require a completed JSON
matching the plan, matching the simulator result already written by run(), and
closed tripinfo XML. During a live batch only revisit cases already finished.
"""

import argparse
import json
from pathlib import Path
import time
import xml.etree.ElementTree as ET


def read(path):
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return {}


def recover(folder):
    folder = Path(folder).resolve()
    plan = read(folder / "plan.json")
    signature = {k: v for k, v in plan.get("signature", {}).items() if k != "end_s"}
    if not signature:
        raise ValueError("Missing experiment signature")
    allowed = {f"d{c['scale']:g}_s{c['seed']}" for c in plan.get("failed_cases", [])}
    live = plan.get("status") == "running"
    recovered = []
    skipped = []
    for temporary in sorted((folder / "runs").glob("*/*/result.tmp")):
        method = temporary.parent.name
        scenario = temporary.parent.parent.name
        if live and scenario not in allowed:
            continue
        candidate = read(temporary)
        destination = temporary.with_suffix(".json")
        existing = read(destination)
        if (
            candidate.get("status") != "complete"
            or candidate.get("signature") != signature
            or candidate.get("simulation_end_s") != plan.get("end_s")
            or candidate.get("method") != method
            or method not in plan.get("methods", [])
            or candidate.get("seed") not in plan.get("seeds", [])
            or candidate.get("demand_scale") not in plan.get("scales", [])
            or scenario != f"d{candidate.get('demand_scale',-1):g}_s{candidate.get('seed')}"
            or not candidate.get("input_hashes")
            or len(candidate.get("probes", [])) != 4
        ):
            skipped.append(str(temporary.relative_to(folder)))
            continue
        keys = (
            "method",
            "seed",
            "actual_end_s",
            "probes",
            "collisions",
            "teleports",
            "engine_version",
        )
        if any(existing.get(k) != candidate.get(k) for k in keys):
            skipped.append(str(temporary.relative_to(folder)))
            continue
        try:
            trips = {
                t.get("id"): t
                for t in ET.parse(temporary.parent / "tripinfo.xml").getroot().findall("tripinfo")
            }
            for probe in candidate["probes"]:
                trip = trips[probe["probe_id"]]
                arrived = float(trip.get("arrival")) >= 0
                if arrived != probe["completed"]:
                    raise ValueError("Arrival differs")
                if arrived and abs(float(trip.get("duration")) - probe["travel_time_s"]) > 1e-6:
                    raise ValueError("Duration differs")
        except (OSError, ET.ParseError, KeyError, TypeError, ValueError):
            skipped.append(str(temporary.relative_to(folder)))
            continue
        # A reader/antivirus can temporarily deny FILE_SHARE_DELETE on Windows.
        for attempt in range(30):
            try:
                temporary.replace(destination)
                recovered.append(str(destination.relative_to(folder)))
                break
            except PermissionError:
                if attempt == 29:
                    skipped.append(str(temporary.relative_to(folder)))
                else:
                    time.sleep(0.1)
    return dict(recovered=recovered, skipped=skipped, simulations_rerun=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(recover(args.output), ensure_ascii=False, indent=2))
