"""Apply the common fixed-time programmes to the network shown in NetEdit."""

from pathlib import Path
import copy
import gzip
import json
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from traffic_study import run_fixed_time as baseline
from traffic_study.fixed_time_signals import (
    build_programmes,
    parallel_carriageway_crossovers,
    roundabout_exit_connections,
    carriageway_split_connections,
    carriageway_merge_connections,
    crossing_roundabout_exits,
    redundant_lane_fans,
)


def configure():
    before = baseline.SOURCE_NET.read_bytes()
    raw = ET.fromstring(gzip.decompress(before))
    entry_id = "1409491216"
    entry_tls = "survey_CH_HVT_ENTRY"
    if raw.find(f"tlLogic[@id='{entry_tls}']") is None:
        entry = raw.find(f"junction[@id='{entry_id}']")
        entry.set("type", "traffic_light")
        entry_edges = {e.get("id") for e in raw.findall("edge") if e.get("to") == entry_id}
        connections = sorted(
            [c for c in raw.findall("connection") if c.get("from") in entry_edges],
            key=lambda c: (c.get("from"), int(c.get("fromLane")), c.get("to"), int(c.get("toLane"))),
        )
        for index, connection in enumerate(connections):
            connection.set("tl", entry_tls)
            connection.set("linkIndex", str(index))
        ET.SubElement(raw, "tlLogic", id=entry_tls, type="static", programID="0", offset="0")
    edges = {edge.get("id"): edge for edge in raw.findall("edge")}
    original_roads = {key: edge for key, edge in edges.items() if edge.get("function") != "internal"}
    nodes = {node.get("id"): node for node in raw.findall("junction")}
    restricted_turns = []
    crossing_exits = crossing_roundabout_exits(raw)
    lane_fans = redundant_lane_fans(raw)
    crossovers = parallel_carriageway_crossovers(raw, baseline.CENTER_WAY_IDS)
    roundabout_exits = roundabout_exit_connections(raw)
    split_connections = carriageway_split_connections(raw)
    merge_removals, merge_additions = carriageway_merge_connections(raw)
    additions = roundabout_exits + split_connections + merge_additions
    for connection in raw.findall("connection"):
        approach = edges[connection.get("from")]
        target = edges[connection.get("to")]
        centre_way = connection.get("from", "").lstrip("-").split("#")[0] in baseline.CENTER_WAY_IDS
        centre_turn = centre_way and (
            connection.get("dir") in ("l", "L", "t", "T")
            or target.get("name") not in ("Cộng Hòa", "Cầu vượt Hoàng Hoa Thám")
        )
        centre_reverse = False
        if centre_way and target.get("name") in ("Cộng Hòa", "Cầu vượt Hoàng Hoa Thám"):
            incoming_dx = float(nodes[approach.get("to")].get("x")) - float(
                nodes[approach.get("from")].get("x")
            )
            outgoing_dx = float(nodes[target.get("to")].get("x")) - float(
                nodes[target.get("from")].get("x")
            )
            centre_reverse = incoming_dx * outgoing_dx < 0
        centre_return = (
            connection.get("from"),
            connection.get("to"),
        ) in baseline.CENTER_RETURN_CONNECTIONS
        ut_tich_wrong_turn = (
            connection.get("tl") == "survey_CH_UT_TICH"
            and approach.get("name") == "Út Tịch"
            and (
                target.get("name") not in ("Cộng Hòa", "Cầu vượt Hoàng Hoa Thám")
                or connection.get("dir") not in ("r", "R", "l", "L")
            )
        )
        tktq_left = (
            approach.get("name") in ("Cộng Hòa", "Cầu vượt Hoàng Hoa Thám")
            and target.get("name") == "Tân Kỳ Tân Quý"
            and connection.get("dir") in ("l", "L")
        )
        if centre_turn or centre_reverse or centre_return or ut_tich_wrong_turn or tktq_left:
            restricted_turns.append(connection)
    restricted_turns.extend(c for c in crossovers if c not in restricted_turns)
    restricted_turns.extend(c for c in crossing_exits if c not in restricted_turns)
    restricted_turns.extend(c for c in lane_fans if c not in restricted_turns)
    restricted_turns.extend(c for c in merge_removals if c not in restricted_turns)
    affected_nodes = {edges[c.get("from")].get("to") for c in restricted_turns}
    affected_nodes.update(edges[c["from"]].get("to") for c in additions)
    lights, report = build_programmes(
        raw,
        baseline.BASE / "signals/survey_observations.csv",
        lambda network, logic: baseline.build_18e_phases(network, logic, validate_moves=False),
        baseline.TLS_18E,
    )
    generated = {logic.get("id"): logic for logic in lights.findall("tlLogic")}
    for source in list(raw.findall("tlLogic")):
        logic = copy.deepcopy(generated[source.get("id")])
        logic.set("programID", source.get("programID", "0"))
        index = list(raw).index(source)
        raw.remove(source)
        raw.insert(index, logic)
    ROOT.joinpath("tmp").mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="signal_conflicts_", dir=ROOT / "tmp") as folder:
        candidate = Path(folder) / "candidate.net.xml.gz"
        rebuilt = Path(folder) / "rebuilt.net.xml.gz"
        patch_file = Path(folder) / "centre_turns.con.xml"
        patch = ET.Element("connections")
        for connection in restricted_turns:
            ET.SubElement(
                patch,
                "delete",
                {key: connection.get(key) for key in ("from", "to", "fromLane", "toLane")},
            )
        for connection in additions:
            ET.SubElement(patch, "connection", connection)
        ET.ElementTree(patch).write(patch_file, encoding="utf-8", xml_declaration=True)
        candidate.write_bytes(
            gzip.compress(ET.tostring(raw, encoding="utf-8", xml_declaration=True), mtime=0)
        )
        result = subprocess.run(
            [
                baseline.sumo_binary("netconvert"),
                "--sumo-net-file",
                str(candidate),
                "--connection-files",
                str(patch_file),
                "--output-file",
                str(rebuilt),
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if result.returncode:
            raise RuntimeError(result.stdout + result.stderr)
        donor = ET.fromstring(gzip.decompress(rebuilt.read_bytes()))
        raw = donor
    # Recompute indications against the rebuilt conflict matrix and link indices.
    lights, report = build_programmes(
        raw,
        baseline.BASE / "signals/survey_observations.csv",
        baseline.build_18e_phases,
        baseline.TLS_18E,
    )
    generated = {logic.get("id"): logic for logic in lights.findall("tlLogic")}
    for source in list(raw.findall("tlLogic")):
        logic = copy.deepcopy(generated[source.get("id")])
        logic.set("programID", source.get("programID", "0"))
        index = list(raw).index(source)
        raw.remove(source)
        raw.insert(index, logic)
    source_18e = next(
        logic for logic in raw.findall("tlLogic") if logic.get("id") == baseline.TLS_18E
    )
    phases_18e, _ = baseline.build_18e_phases(raw, source_18e)
    for logic in raw.findall("tlLogic"):
        if logic.get("id") == baseline.TLS_18E:
            for phase in list(logic.findall("phase")):
                logic.remove(phase)
            for duration, state in phases_18e:
                ET.SubElement(logic, "phase", duration=f"{duration:g}", state=state)
    signal_widths = {}
    for connection in raw.findall("connection"):
        tls_id = connection.get("tl")
        if tls_id:
            signal_widths[tls_id] = max(
                signal_widths.get(tls_id, 0), int(connection.get("linkIndex")) + 1
            )
    for logic in raw.findall("tlLogic"):
        width = signal_widths[logic.get("id")]
        for phase in logic.findall("phase"):
            if len(phase.get("state")) < width:
                raise RuntimeError(f"Incomplete signal state at {logic.get('id')}.")
            phase.set("state", phase.get("state")[:width])
    # The final programmes must be included when rebuilding right-of-way.
    # Recomputing indications after deleting links can change g/G relationships.
    with tempfile.TemporaryDirectory(prefix="signal_final_", dir=ROOT / "tmp") as folder:
        candidate = Path(folder) / "candidate.net.xml.gz"
        rebuilt = Path(folder) / "rebuilt.net.xml.gz"
        candidate.write_bytes(
            gzip.compress(ET.tostring(raw, encoding="utf-8", xml_declaration=True), mtime=0)
        )
        result = subprocess.run(
            [
                baseline.sumo_binary("netconvert"),
                "--sumo-net-file", str(candidate),
                "--output-file", str(rebuilt),
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if result.returncode:
            raise RuntimeError(result.stdout + result.stderr)
        donor = ET.fromstring(gzip.decompress(rebuilt.read_bytes()))
        old_roads = original_roads
        new_roads = {e.get("id"): e for e in donor.findall("edge") if e.get("function") != "internal"}
        if old_roads.keys() != new_roads.keys():
            raise RuntimeError("Full junction rebuild changes the external road identifiers.")
        geometry_changes = []
        for edge_id, edge in old_roads.items():
            other = new_roads[edge_id]
            if (edge.get("from"), edge.get("to")) != (other.get("from"), other.get("to")):
                raise RuntimeError(f"Junction rebuild changes endpoints on {edge_id}.")
            if len(edge.findall("lane")) != len(other.findall("lane")):
                raise RuntimeError(f"Junction rebuild changes lane counts on {edge_id}.")
            for old_lane, new_lane in zip(edge.findall("lane"), other.findall("lane")):
                for attribute, default in [("speed", "0"), ("width", "3.2")]:
                    difference = abs(
                        float(old_lane.get(attribute, default))
                        - float(new_lane.get(attribute, default))
                    )
                    if difference > 0.01:  # SUMO serialises these attributes to two decimals.
                        raise RuntimeError(f"Junction rebuild changes {attribute} on {edge_id}.")
                for attribute in ("allow", "disallow"):
                    if set(old_lane.get(attribute, "").split()) != set(
                        new_lane.get(attribute, "").split()
                    ):
                        raise RuntimeError(f"Junction rebuild changes permissions on {edge_id}.")
                if old_lane.get("shape") != new_lane.get("shape"):
                    geometry_changes.append(
                        dict(
                            lane=old_lane.get("id"),
                            old_length=old_lane.get("length"),
                            new_length=new_lane.get("length"),
                        )
                    )
        raw = donor
        count = sum(node.get("type") != "internal" for node in raw.findall("junction"))
    if baseline.SOURCE_NET.read_bytes() != before:
        raise RuntimeError("Network changed while preparing signals. Save NetEdit and retry.")
    temporary = baseline.SOURCE_NET.with_suffix(".tmp")
    temporary.write_bytes(
        gzip.compress(ET.tostring(raw, encoding="utf-8", xml_declaration=True), mtime=0)
    )
    temporary.replace(baseline.SOURCE_NET)
    (baseline.BASE / "signals/network_rebuild.json").write_text(
        json.dumps(dict(junctions_rebuilt=count, adjusted_lane_geometries=geometry_changes), indent=2),
        encoding="utf-8",
    )
    print(f"Applied {len(report)} programmes and updated right-of-way at {count} junctions.")
    print(f"Removed {len(restricted_turns)} restricted centre/Ut Tich/Tan Ky Tan Quy connections.")
    print(f"Removed {len(crossovers)} parallel-carriageway crossovers.")
    print(f"Added {len(roundabout_exits)} parallel roundabout continuations.")
    print(f"Removed {len(crossing_exits)} crossing inner-lane roundabout exits.")
    print(f"Removed {len(lane_fans)} duplicate lane-to-road fan connections.")
    print(f"Added {len(split_connections)} bridge split connections.")
    print(f"Corrected C12 outer-lane mapping: {len(merge_removals)} removed, {len(merge_additions)} added.")


if __name__ == "__main__":
    configure()
