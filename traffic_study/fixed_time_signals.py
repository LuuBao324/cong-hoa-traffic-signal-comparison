"""Build all fixed-time programmes from the shared survey table."""

import collections
import csv
import math
import xml.etree.ElementTree as ET

DEFAULT_GREEN_S = 30
YELLOW_S = 3
CORRIDOR_NAMES = {"Cộng Hòa", "Cầu vượt Hoàng Hoa Thám"}
SURVEY_CONTROLLERS = {
    "CH_HHT": "GS_cluster_2146838339_366467129",
    "CH_NGO_BE": "cluster13817051847_2079964894_366379261",
    "CH_AP_BAC": "cluster13817051847_2079964894_366379261",
    "CH_TKTQ": "cluster11399978032_13817051828_2533900283",
    "CH_AIRPORT": "cluster_12564865142_12765516717_12991340401_13441246343_#1more",
    "CH_UT_TICH": "survey_CH_UT_TICH",
    "CH_HVT_ROUNDABOUT": "survey_CH_HVT_ENTRY",
    "CH_TRUONG_CHINH_UTURN": "cluster_11453123766_11453135175_2079964012_5757491891",
}


def parallel_carriageway_crossovers(raw, centre_way_ids):
    """Find artificial lane crossovers where both carriageways continue separately."""
    edges = {edge.get("id"): edge for edge in raw.findall("edge")}
    connections = collections.defaultdict(list)
    for connection in raw.findall("connection"):
        approach = edges[connection.get("from")]
        target = edges[connection.get("to")]
        if approach.get("name") in CORRIDOR_NAMES and target.get("name") in CORRIDOR_NAMES:
            connections[approach.get("to")].append(connection)

    def is_centre(edge_id):
        return edge_id.lstrip("-").split("#")[0] in centre_way_ids

    crossovers = []
    for movements in connections.values():
        for connection in movements:
            if connection.get("dir") != "s":
                continue
            incoming = connection.get("from")
            outgoing = connection.get("to")
            if is_centre(incoming) == is_centre(outgoing):
                continue
            # Keep bridge entries/exits. Remove a crossover only when both
            # participating approaches have their own straight continuation.
            own_continuation = any(
                other.get("from") == incoming
                and other.get("dir") == "s"
                and is_centre(other.get("to")) == is_centre(incoming)
                for other in movements
            )
            other_approach = any(
                other.get("to") == outgoing
                and other.get("dir") == "s"
                and is_centre(other.get("from")) == is_centre(outgoing)
                for other in movements
            )
            if own_continuation and other_approach:
                crossovers.append(connection)
    return crossovers


def roundabout_exit_connections(raw):
    """Provide parallel ring continuations so the outside lane can keep moving."""
    edges = {edge.get("id"): edge for edge in raw.findall("edge")}
    ring_edges = {
        edge_id for circle in raw.findall("roundabout") for edge_id in circle.get("edges", "").split()
    }
    ring_edges.update(
        edge_id for edge_id, edge in edges.items()
        if edge.get("name") == "Vòng xoay Lăng Cha Cả"
    )
    movements = collections.defaultdict(list)
    for connection in raw.findall("connection"):
        approach = edges[connection.get("from")]
        target = edges[connection.get("to")]
        if (
            approach.get("id") in ring_edges
            and target.get("id") in ring_edges
            and len(approach.findall("lane")) > 1
            and len(target.findall("lane")) > 1
        ):
            movements[(approach.get("id"), target.get("id"))].append(connection)
    additions = []
    for (approach_id, target_id), connections in movements.items():
        connected = {c.get("fromLane") for c in connections}
        for index in range(min(len(edges[approach_id].findall("lane")), len(edges[target_id].findall("lane")))):
            if str(index) not in connected:
                additions.append(
                    {"from": approach_id, "to": target_id,
                     "fromLane": str(index), "toLane": str(index)}
                )
    return additions


def crossing_roundabout_exits(raw):
    """Identify inner exits crossing an outside lane that continues round the ring."""
    ring = {eid for q in raw.findall("roundabout") for eid in q.get("edges", "").split()}
    by_approach = collections.defaultdict(list)
    for connection in raw.findall("connection"):
        by_approach[connection.get("from")].append(connection)
    removals = []
    for approach, connections in by_approach.items():
        if approach not in ring:
            continue
        outer_continuations = [
            int(c.get("fromLane")) for c in connections if c.get("to") in ring
        ]
        for connection in connections:
            if (
                connection.get("to") not in ring
                and connection.get("dir") in ("r", "R")
                and any(lane < int(connection.get("fromLane")) for lane in outer_continuations)
            ):
                removals.append(connection)
    return removals


def redundant_lane_fans(raw):
    """Keep one parallel continuation per input lane and destination road."""
    edges = {edge.get("id"): edge for edge in raw.findall("edge")}
    groups = collections.defaultdict(list)
    for connection in raw.findall("connection"):
        approach = edges[connection.get("from")]
        if approach.get("function") == "internal":
            continue
        destination = edges[connection.get("to")]
        lane = destination.findall("lane")[int(connection.get("toLane"))]
        permissions = tuple(
            (element.get("allow", ""), element.get("disallow", ""))
            for element in (connection, lane)
        )
        key = (
            connection.get("from"), connection.get("to"), connection.get("fromLane"),
            connection.get("dir", "").lower(), lane.get("width", "3.2"), permissions,
        )
        groups[key].append(connection)
    removals = []
    for connections in groups.values():
        if len(connections) < 2:
            continue
        first = connections[0]
        source_count = len(edges[first.get("from")].findall("lane"))
        target_count = len(edges[first.get("to")].findall("lane"))
        lane = int(first.get("fromLane"))
        preferred = lane
        if first.get("dir", "").lower() == "l":
            preferred = target_count - source_count + lane
        preferred = max(0, min(target_count - 1, preferred))
        chosen = min(connections, key=lambda c: abs(int(c.get("toLane")) - preferred))
        removals.extend(c for c in connections if c is not chosen)
    return removals


def carriageway_merge_connections(raw):
    """Keep the two outer lanes separate from the centre lane at the C12 merge."""
    approach, target = "197804068#3", "1511909557"
    edges = {edge.get("id"): edge for edge in raw.findall("edge")}
    if not {approach, target} <= edges.keys():
        return [], []
    if len(edges[approach].findall("lane")) != 2 or len(edges[target].findall("lane")) != 3:
        raise ValueError("C12 merge lane counts changed; verify its lane mapping.")
    connections = [c for c in raw.findall("connection") if c.get("from") == approach and c.get("to") == target]
    removals = [c for c in connections if c.get("fromLane") != c.get("toLane")]
    existing = {(c.get("fromLane"), c.get("toLane")) for c in connections}
    additions = [
        {"from": approach, "to": target, "fromLane": lane, "toLane": lane}
        for lane in ("0", "1") if (lane, lane) not in existing
    ]
    return removals, additions


def carriageway_split_connections(raw):
    """Allow adjacent lanes to reach either side of the two verified bridge splits."""
    splits = {
        "1511909556": ("1511909552", "1424752054#0"),
        "197804036": ("1511909549", "1412930634#0"),
    }
    existing = {
        tuple(c.get(key) for key in ("from", "to", "fromLane", "toLane"))
        for c in raw.findall("connection")
    }
    additions = []
    edges = {edge.get("id") for edge in raw.findall("edge")}
    for approach, (centre, outer) in splits.items():
        if not {approach, centre, outer} <= edges:
            continue
        for target, source_lane, target_lane in [(centre, "1", "0"), (outer, "2", "1")]:
            if (approach, target, source_lane, target_lane) not in existing:
                additions.append(
                    {"from": approach, "to": target,
                     "fromLane": source_lane, "toLane": target_lane}
                )
    return additions


class SignalNetwork:
    def __init__(self, raw):
        self.edges = {edge.get("id"): edge for edge in raw.findall("edge")}
        self.junctions = {node.get("id"): node for node in raw.findall("junction")}
        self.roundabout_edges = {
            eid for circle in raw.findall("roundabout") for eid in circle.get("edges", "").split()
        }
        self.connections = collections.defaultdict(list)
        self.continuations = collections.defaultdict(list)
        for connection in raw.findall("connection"):
            self.continuations[(connection.get("from"), connection.get("fromLane"))].append(
                connection
            )
            if connection.get("tl"):
                self.connections[connection.get("tl")].append(connection)

    def request(self, connection):
        junction_id = self.edges[connection.get("from")].get("to")
        junction = self.junctions[junction_id]
        internal = junction.get("intLanes", "").split()
        via = connection.get("via", "")
        visited = set()
        while via and via not in internal and via not in visited:
            visited.add(via)
            edge_id, lane = via.rsplit("_", 1)
            following = [
                c
                for c in self.continuations[(edge_id, lane)]
                if c.get("to") == connection.get("to")
                and c.get("toLane") == connection.get("toLane")
            ]
            via = following[0].get("via", "") if following else ""
        if via not in internal:
            return None
        index = internal.index(via)
        request = next(q for q in junction.findall("request") if int(q.get("index")) == index)
        return junction_id, index, request.get("foes", "")

    def name(self, connection):
        return self.edges[connection.get("from")].get("name", "")

    def axis(self, connection):
        lane = self.edges[connection.get("from")].findall("lane")[int(connection.get("fromLane"))]
        points = [tuple(map(float, p.split(","))) for p in lane.get("shape").split()]
        dx, dy = points[-1][0] - points[-2][0], points[-1][1] - points[-2][1]
        return math.atan2(dy, dx) % math.pi

    def green_state(self, connections, allowed, permanent=()):
        """Choose protected links without simultaneous geometric/merge conflicts."""
        size = max(int(c.get("linkIndex")) for c in connections) + 1
        state = ["r"] * size
        protected = []
        targets = set()
        permanent = set(permanent)
        selected = [c for c in connections if int(c.get("linkIndex")) in set(allowed) | permanent]
        selected.sort(
            key=lambda c: (
                int(c.get("linkIndex")) not in permanent,
                c.get("dir") != "s",
                int(c.get("linkIndex")),
            )
        )
        for connection in selected:
            index = int(connection.get("linkIndex"))
            request = self.request(connection)
            target = (connection.get("to"), connection.get("toLane"))
            conflict = target in targets or request is None
            if request is not None:
                jid, number, foes = request
                conflict |= any(
                    jid == other_jid
                    and (foes[-1 - other_number] == "1" or other_foes[-1 - number] == "1")
                    for other_jid, other_number, other_foes in protected
                )
            indication = "g" if conflict else "G"
            # Shared signal indices receive the more restrictive green.
            state[index] = "g" if state[index] == "g" else indication
            if not conflict:
                protected.append(request)
                targets.add(target)
        return "".join(state)

    def protected_states(self, connections, allowed):
        """Partition conflicting movements into separately protected green states."""
        pending = set(allowed)
        states = []
        while pending:
            candidate = self.green_state(connections, pending)
            served = {index for index in pending if candidate[index] == "G"}
            if not served:
                raise RuntimeError("Cannot create a protected stage for the remaining movements.")
            states.append(
                "".join("G" if index in served else "r" for index in range(len(candidate)))
            )
            pending -= served
        return states


def two_stage_phases(states, durations):
    phases = []
    for index, (state, duration) in enumerate(zip(states, durations)):
        following = states[(index + 1) % len(states)]
        yellow = "".join(
            "y" if a in "Gg" and b not in "Gg" else a for a, b in zip(state, following)
        )
        phases.extend([(float(duration), state), (YELLOW_S, yellow)])
    return phases


def merge_rebuilt_signals(original, rebuilt, extra_nodes=()):
    """Use netconvert's complete internal junction model for controlled nodes."""
    import copy

    old_edges = {e.get("id"): e for e in original.findall("edge")}
    new_edges = {e.get("id"): e for e in rebuilt.findall("edge")}
    controlled = {
        old_edges[c.get("from")].get("to") for c in original.findall("connection") if c.get("tl")
    }
    controlled.update(extra_nodes)
    rebuild_all = {
        node.get("id") for node in original.findall("junction") if node.get("type") != "internal"
    } <= controlled
    prefixes = tuple(":" + node + "_" for node in controlled)
    tls_ids = {t.get("id") for t in original.findall("tlLogic")}
    for edge_id, edge in old_edges.items():
        if edge.get("function") == "internal":
            continue
        if edge.get("from") in controlled or edge.get("to") in controlled:
            other = new_edges[edge_id]
            if [q.attrib for q in edge.findall("lane")] != [
                q.attrib for q in other.findall("lane")
            ]:
                raise RuntimeError(f"Controlled junction rebuild changes external road {edge_id}.")

    def selected(element, edges):
        if element.tag == "tlLogic":
            return element.get("id") in tls_ids
        if rebuild_all:
            if element.tag == "edge":
                return element.get("function") == "internal"
            return element.tag in ("junction", "connection")
        if element.tag in ("edge", "junction"):
            return element.get("id") in controlled or element.get("id", "").startswith(prefixes)
        if element.tag == "connection":
            approach = element.get("from", "")
            return (
                element.get("tl") in tls_ids
                or approach.startswith(prefixes)
                or element.get("to", "").startswith(prefixes)
                or edges.get(approach, {}).get("to") in controlled
            )
        return False

    original[:] = [element for element in original if not selected(element, old_edges)]
    for element in rebuilt:
        if selected(element, new_edges):
            original.append(copy.deepcopy(element))
    return original, len(controlled)


def build_programmes(raw, survey_path, build_18e, tls_18e, shared_record="CH_AP_BAC"):
    with survey_path.open(encoding="utf-8-sig", newline="") as stream:
        records = {row["record_id"]: row for row in csv.DictReader(stream)}
    specifications = {}
    for record_id, tls_id in SURVEY_CONTROLLERS.items():
        if record_id in ("CH_NGO_BE", "CH_AP_BAC") and record_id != shared_record:
            continue
        specifications[tls_id] = records[record_id]

    network = SignalNetwork(raw)
    lights = ET.Element("additional")
    report = []
    for source in raw.findall("tlLogic"):
        tls_id = source.get("id")
        connections = network.connections[tls_id]
        if not connections:
            continue
        logic = ET.SubElement(
            lights,
            "tlLogic",
            id=tls_id,
            type="static",
            programID="baseline_fixed",
            offset=source.get("offset", "0"),
        )
        record = specifications.get(tls_id)
        if tls_id == tls_18e:
            phases, _ = build_18e(raw, source)
            basis = "18E surveyed 67/29"
        else:
            permanent = set()
            if record:
                red, green = float(record["red_s"]), float(record["green_s"])
                if record["record_id"] == "CH_UT_TICH":
                    primary = {
                        int(c.get("linkIndex"))
                        for c in connections
                        if (c.get("dir") in ("t", "T") and network.name(c) in CORRIDOR_NAMES)
                        or (
                            network.name(c) == "Út Tịch"
                            and network.edges[c.get("to")].get("name") in CORRIDOR_NAMES
                            and c.get("dir") in ("r", "R", "l", "L")
                        )
                    }
                elif record["record_id"] == "CH_TRUONG_CHINH_UTURN":
                    # Cong Hoa and Truong Chinh merge into the same exit lanes.
                    # Give each approach a protected stage instead of leaving
                    # Cong Hoa permanently yielding to Truong Chinh.
                    primary = {
                        int(c.get("linkIndex"))
                        for c in connections
                        if network.name(c) in CORRIDOR_NAMES
                    }
                elif record["record_id"] == "CH_HVT_ROUNDABOUT":
                    primary = {
                        int(c.get("linkIndex"))
                        for c in connections
                        if network.name(c) in CORRIDOR_NAMES
                    }
                else:
                    movements = (
                        ("s", "r", "R", "l", "L", "t", "T")
                        if record["record_id"] == "CH_HHT"
                        else ("s", "r")
                    )
                    primary = {
                        int(c.get("linkIndex"))
                        for c in connections
                        if network.name(c) in CORRIDOR_NAMES and c.get("dir") in movements
                    }
                durations = (green, max(1, red - YELLOW_S))
                basis = record["record_id"]
            else:
                # Two approach axes give approximately 30s green / 33s red.
                anchor = next((c for c in connections if c.get("dir") == "s"), connections[0])
                axis = network.axis(anchor)
                primary = {
                    int(c.get("linkIndex"))
                    for c in connections
                    if abs(math.cos(network.axis(c) - axis)) >= math.sqrt(0.5)
                }
                durations = (DEFAULT_GREEN_S, DEFAULT_GREEN_S)
                basis = "default_30_30"
                ring = {
                    int(c.get("linkIndex")) for c in connections
                    if c.get("from") in network.roundabout_edges
                }
                incoming = {int(c.get("linkIndex")) for c in connections}
                if ring and ring != incoming:
                    primary = ring
                    basis = "default_roundabout_entry_30_30"
            all_indices = {int(c.get("linkIndex")) for c in connections}
            secondary = all_indices - primary - permanent
            if not primary or not secondary:
                # A single approach with no competing movement can remain green.
                phases = [(60, network.green_state(connections, all_indices))]
                basis += "_single_group"
            else:
                first = network.green_state(connections, primary, permanent)
                second = network.green_state(connections, secondary, permanent)
                # Permanent through links use one indication throughout the cycle.
                for index in permanent:
                    char = "g" if first[index] == "g" or second[index] == "g" else "G"
                    first = first[:index] + char + first[index + 1 :]
                    second = second[:index] + char + second[index + 1 :]
                phases = two_stage_phases((first, second), durations)
                if record and record["record_id"] == "CH_TRUONG_CHINH_UTURN":
                    states, times = [], []
                    for indices, duration in zip((primary, secondary), durations):
                        protected = network.protected_states(connections, indices)
                        states.extend(protected)
                        times.extend([duration / len(protected)] * len(protected))
                    phases = two_stage_phases(states, times)
        if record is None and tls_id != tls_18e:
            # Unmeasured intersections use protected movements. This avoids
            # vehicles waiting inside a permissive turn when its phase ends.
            protected = network.protected_states(connections, all_indices)
            phases = (
                [(60, protected[0])] if len(protected) == 1
                else two_stage_phases(protected, [DEFAULT_GREEN_S] * len(protected))
            )
            basis = "default_protected_30s_green_3s_yellow"
        for duration, state in phases:
            ET.SubElement(logic, "phase", duration=f"{duration:g}", state=state)
        report.append(
            {
                "tls_id": tls_id,
                "basis": basis,
                "cycle_s": sum(d for d, _ in phases),
                "phase_durations_s": [d for d, _ in phases],
                "states": [s for _, s in phases],
            }
        )
    return lights, report
