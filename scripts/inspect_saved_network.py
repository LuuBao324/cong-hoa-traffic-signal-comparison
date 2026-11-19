"""Compare the saved NetEdit network with the prepared simulation snapshot."""

from pathlib import Path
import gzip
import hashlib
import json
import xml.etree.ElementTree as ET

BASE = Path(__file__).resolve().parents[1] / "tan_binh_2026"


def read(path):
    data = path.read_bytes()
    root = ET.fromstring(gzip.decompress(data))
    return root, hashlib.sha256(data).hexdigest()


def audit():
    current, current_hash = read(BASE / "tan_binh.net.xml.gz")
    previous, previous_hash = read(BASE / "baseline_fixed_time/network_snapshot.net.xml.gz")
    nodes = {n.get("id"): n for n in current.findall("junction") if n.get("type") != "internal"}
    old_nodes = {
        n.get("id"): n for n in previous.findall("junction") if n.get("type") != "internal"
    }
    tls_id = "cluster12834017505_13817051850_2079964423"

    def links(root):
        return sorted(
            (
                c.get("linkIndex"),
                c.get("from"),
                c.get("fromLane"),
                c.get("to"),
                c.get("toLane"),
                c.get("dir"),
            )
            for c in root.findall("connection")
            if c.get("tl") == tls_id
        )

    report = {
        "source_sha256": current_hash,
        "snapshot_sha256": previous_hash,
        "same_network": current_hash == previous_hash,
        "removed_junctions": sorted(old_nodes.keys() - nodes.keys()),
        "added_junctions": [
            dict(nodes[key].attrib) for key in sorted(nodes.keys() - old_nodes.keys())
        ],
        "source_tls_controllers": len({t.get("id") for t in current.findall("tlLogic")}),
        "18e_connection_mapping_unchanged": links(current) == links(previous),
        "18e_connections": links(current),
        "locations": {},
    }
    for label, token in [
        ("18E", "2079964423"),
        ("Ap Bac", "366379261"),
        ("Tan Ky Tan Quy", "11399978032"),
    ]:
        matched = [n for key, n in nodes.items() if token in key]
        details = []
        for node in matched:
            incoming = set(node.get("incLanes", "").split())
            edges = {e.get("id") for e in current.findall("edge") if e.get("to") == node.get("id")}
            controllers = {
                c.get("tl")
                for c in current.findall("connection")
                if c.get("from") in edges and c.get("tl")
            }
            details.append(
                {
                    "junction": dict(node.attrib),
                    "incoming_lanes": len(incoming),
                    "controllers": sorted(controllers),
                    "programs": [
                        dict(t.attrib, phases=[dict(p.attrib) for p in t.findall("phase")])
                        for t in current.findall("tlLogic")
                        if t.get("id") in controllers
                    ],
                }
            )
        report["locations"][label] = details
    baseline_path = BASE / "baseline_fixed_time/network_snapshot.net.xml.gz"
    if baseline_path.exists():
        baseline, baseline_hash = read(baseline_path)
        report["baseline_snapshot"] = {
            "sha256": baseline_hash,
            "matches_source": baseline_hash == current_hash,
            "location_junctions": {
                label: [
                    dict(id=n.get("id"), type=n.get("type"))
                    for n in baseline.findall("junction")
                    if token in n.get("id", "") and n.get("type") != "internal"
                ]
                for label, token in [
                    ("18E", "2079964423"),
                    ("Ap Bac", "366379261"),
                    ("Tan Ky Tan Quy", "11399978032"),
                ]
            },
        }
    out = BASE / "signals/saved_network_audit.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                "same_trial_network": report["same_network"],
                "tls_controllers": report["source_tls_controllers"],
                "18e_mapping_unchanged": report["18e_connection_mapping_unchanged"],
                "current_locations": {
                    label: [item["junction"]["id"] for item in items]
                    for label, items in report["locations"].items()
                },
                "baseline_snapshot": report.get("baseline_snapshot"),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    audit()
