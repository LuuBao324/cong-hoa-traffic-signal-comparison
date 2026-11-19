"""Extract reproducible network and signal provenance for the methodology chapter."""

import argparse
import csv
from collections import Counter, defaultdict
from datetime import datetime, timezone
import gzip
import hashlib
from importlib.metadata import version
import json
from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from traffic_study.vehicle_types import VEHICLE_TYPES


def read_xml(path):
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rb") as stream:
        return ET.parse(stream).getroot()


def usable_lane(lane):
    allowed = lane.get("allow")
    allowed = set(allowed.split()) if allowed is not None else None
    forbidden = set(lane.get("disallow", "").split())
    width = float(lane.get("width", "3.2"))
    return any(
        (allowed is None or "all" in allowed or vehicle_class in allowed)
        and vehicle_class not in forbidden
        and "all" not in forbidden
        and width + 1e-6 >= float(body_width)
        for vehicle_class, _, body_width, _ in VEHICLE_TYPES.values()
    )


def inventory(root):
    edges = [e for e in root.findall("edge") if e.get("function", "normal") == "normal"]
    usable = [e for e in edges if any(usable_lane(lane) for lane in e.findall("lane"))]
    nodes = [j for j in root.findall("junction") if j.get("type") != "internal" and not j.get("id").startswith(":")]
    programmes = root.findall("tlLogic")
    states = defaultdict(set)
    for programme in programmes:
        states[programme.get("id")].update(p.get("state") for p in programme.findall("phase"))
    return {
        "non_internal_junctions": len(nodes),
        "normal_directed_edges": len(edges),
        "normal_lanes": sum(len(e.findall("lane")) for e in edges),
        "study_vehicle_usable_nodes": len({e.get(key) for e in usable for key in ("from", "to")}),
        "study_vehicle_usable_edges": len(usable),
        "study_vehicle_usable_lanes": sum(usable_lane(lane) for e in edges for lane in e.findall("lane")),
        "unique_signal_controllers": len(states),
        "signalised_junction_nodes": sum("traffic_light" in j.get("type", "") for j in nodes),
        "switching_controllers": sum(len(s) > 1 for s in states.values()),
        "constant_green_controllers": sorted(tls for tls, s in states.items() if len(s) == 1 and set(next(iter(s))) <= {"G", "g"}),
        "junction_types": dict(Counter(j.get("type") for j in nodes)),
        "georeference": root.find("location").attrib,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", default="dataset_cong_hoa")
    parser.add_argument("--scenario", default="d1_s102")
    args = parser.parse_args()
    base = ROOT / "tan_binh_2026"
    inputs = base / args.dataset / "inputs" / args.scenario
    network_path = inputs / "network_snapshot.net.xml.gz"
    original_path = base / "source/wizard_original.net.xml.gz"
    osm_path = base / "source/map.osm.xml.gz"
    timing_path = inputs / "signal_plan.json"
    survey_path = base / "signals/survey_observations.csv"
    network, original, osm = map(read_xml, (network_path, original_path, osm_path))
    timing = {p["tls_id"]: p for p in json.loads(timing_path.read_text(encoding="utf-8"))}
    with survey_path.open(encoding="utf-8-sig", newline="") as stream:
        survey = list(csv.DictReader(stream))
    with gzip.open(original_path, "rt", encoding="utf-8") as stream:
        header = stream.read(10000)
    generated = re.search(r"generated on (.*?) by Eclipse SUMO netconvert ([^\s]+)", header)
    config_text = re.search(r"<netconvertConfiguration.*?</netconvertConfiguration>", header, re.S)
    options = {}
    if config_text:
        options = {node.tag: node.get("value") for node in ET.fromstring(config_text.group()).iter() if node.get("value") is not None}
    original_ids = {p.get("id") for p in original.findall("tlLogic")}
    current_ids = {p.get("id") for p in network.findall("tlLogic")}
    if current_ids != timing.keys():
        raise ValueError("The effective timing inventory differs from the frozen network.")
    edges = {edge.get("id"): edge for edge in network.findall("edge")}
    junctions, roads, links = defaultdict(set), defaultdict(set), Counter()
    for connection in network.findall("connection"):
        tls = connection.get("tl")
        if not tls:
            continue
        approach = edges[connection.get("from")]
        junctions[tls].add(approach.get("to"))
        roads[tls].add(approach.get("name") or approach.get("id"))
        links[tls] += 1
    rows = []
    for tls in sorted(current_ids):
        plan = timing[tls]
        origin = "post_import_edit"
        if tls in original_ids:
            origin = "wizard_signal_inference_GS_prefix" if tls.startswith("GS_") else "original_wizard_controller"
        rows.append({
            "tls_id": tls,
            "position_origin": origin,
            "controlled_junction_count": len(junctions[tls]),
            "controlled_junction_ids": " | ".join(sorted(junctions[tls])),
            "incoming_roads": " | ".join(sorted(roads[tls])),
            "timing_source": "assumed_default" if plan["basis"].startswith("default") else "survey_informed",
            "timing_basis": plan["basis"],
            "cycle_s": plan["cycle_s"],
            "phase_durations_s": " | ".join(map(str, plan["phase_durations_s"])),
            "phase_states": " | ".join(plan["states"]),
            "controlled_connections": links[tls],
        })
    report = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "frozen_network": inventory(network),
        "original_wizard_network": inventory(original),
        "original_wizard_generation": {"timestamp": generated.group(1), "netconvert_version": generated.group(2)} if generated else None,
        "original_import_options": options,
        "osm_extract": {
            "snapshot_utc": osm.find("meta").get("osm_base"),
            "nodes": len(osm.findall("node")),
            "ways": len(osm.findall("way")),
            "signal_tagged_nodes": sum(n.find("tag[@k='highway'][@v='traffic_signals']") is not None for n in osm.findall("node")),
        },
        "signal_position_origins": dict(Counter(row["position_origin"] for row in rows)),
        "programme_timing_sources": dict(Counter(row["timing_source"] for row in rows)),
        "controllers_added_after_original_import": sorted(current_ids - original_ids),
        "field_timing_register": {
            "movement_records": len(survey),
            "named_locations": len({row["location"] for row in survey}),
            "records_with_survey_date": sum(bool(row["survey_date"]) for row in survey),
            "records_with_survey_time": sum(bool(row["survey_time"]) for row in survey),
        },
        "runtime_packages": {name: version(name) for name in ("sumolib", "traci", "libsumo", "eclipse-sumo")},
        "source_files": {
            str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in (network_path, original_path, osm_path, timing_path, survey_path)
        },
        "definitions": {
            "junctions": "SUMO junction records excluding internal junctions.",
            "edges": "Non-internal directed edges, including representations outside the study-vehicle subgraph.",
            "usable": "At least one study vehicle class is permitted on an individual lane wide enough for its body.",
            "controllers": "Unique tlLogic IDs. A controller may serve several signalised junction nodes.",
            "positions": "Position provenance records the model construction history. Survey-informed timing records identify the timing source.",
        },
    }
    output = ROOT / "docs/evidence"
    output.mkdir(parents=True, exist_ok=True)
    (output / "network_inventory.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    with (output / "signal_inventory.csv").open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(json.dumps({"network": report["frozen_network"], "position_origins": report["signal_position_origins"], "timing_sources": report["programme_timing_sources"], "survey": report["field_timing_register"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
