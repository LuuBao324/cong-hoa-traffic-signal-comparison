"""Prepare mixed traffic and measure tracked journeys using fixed-time signals."""

from pathlib import Path
import argparse
import collections
import csv
import gzip
import heapq
import json
import math
import random
import xml.etree.ElementTree as ET
import hashlib
import sys
import tempfile
import sumolib
from .vehicle_types import VEHICLE_TYPES, allows_vehicle, allows_lane

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "tan_binh_2026"
OUT = BASE / "baseline_fixed_time"  # Interactive preparation folder.
SOURCE_NET = BASE / "tan_binh.net.xml.gz"
NET = OUT / "network_snapshot.net.xml.gz"
# Demand, random seed and tracked-vehicle departure settings.
SEED = 42  # Repeatable demand generation.
DEMAND_DURATION_S = 1800  # Generate traffic for 30 minutes; rates below are vehicles per hour.
SIMULATION_END_S = 2400  # Stop earlier when all tracked vehicles arrive.
PROBE_ID = "probe_car"  # Tracked passenger-car identifier.
PROBE_DEPART_S = 300  # Five-minute warm-up before tracked vehicles depart.
DEMAND_SCALE = 1.0  # Feasible reference preview; batches also use 0.1 and 0.5.
SIMULATION_STEP_S = 0.25
MAX_SPEED_KMH = 60  # Speed cap; lower network limits are retained.
INTERIOR_DEPARTURE_SHARE = 0.5  # Half of background departures originate inside the network.
SIDE_APPROACH_BACKGROUND_SHARE = (
    0.2  # Background share entering from signalised corridor side roads.
)
AIRPORT_BACKGROUND_SHARE = 0.02  # Background share originating near terminal T3.
# Approximate passage flow inferred by the user from a ten-minute video.
CORRIDOR_OBSERVED_TOTAL_VPS = 20
OBSERVATION_DURATION_S = 600
REFERENCE_CORRIDOR_DEMAND_VPH = 36000  # Requested reference of ten corridor-related journeys/second, both directions.
CORRIDOR_COUNT_NODE = "2079964787"  # Cong Hoa / Duong 20 Cong Hoa.
CORRIDOR_COUNT_OFFSET_M = 40  # Adjacent section clear of junction-internal lanes.
REVERSE_DEMAND_RATIO = 1.0  # Assumed reverse demand relative to the estimated direction.
REFERENCE_TOTAL_DEMAND_VPH = 67500  # Corridor-related demand plus a separate 31,500 vehicles/hour elsewhere.
DIRECT_CORRIDOR_SHARE = 0.0  # Only the four tracked vehicles have imposed corridor journeys.
REFERENCE_COUNT_10_MIN = CORRIDOR_OBSERVED_TOTAL_VPS * OBSERVATION_DURATION_S
VEHICLE_SHARES = {"motorcycle": 0.76, "car": 0.21, "truck": 0.02, "bus": 0.01}
MAP_DEMAND_MULTIPLIER = 1.0
REFERENCE_MAP_PER_HOUR = {
    kind: round(REFERENCE_TOTAL_DEMAND_VPH * share) for kind, share in VEHICLE_SHARES.items()
}
NETWORK_BACKGROUND_PER_HOUR = {
    kind: round(rate * DEMAND_SCALE * MAP_DEMAND_MULTIPLIER)
    for kind, rate in REFERENCE_MAP_PER_HOUR.items()
}
CROSS_FLOW_VEHICLES = 0
CENTER_WAY_IDS = {"1511909547", "1515746229", "1511909550", "1523207559", "235240683"}
# Explicit reverse connections at the centre carriageway endpoints.
CENTER_RETURN_CONNECTIONS = {("1511909549", "1511909548"), ("1511909552", "1511909551")}

PROBES = {
    "probe_car": ("car", "outer"),
    "probe_motorcycle": ("motorcycle", "outer"),
    "probe_car_center": ("car", "center"),
    "probe_motorcycle_center": ("motorcycle", "center"),
}

# Surveyed 18E stages: corridor 67 s; side road and outer turns 29 s.
FIXED_18E_GREEN_SECONDS = (67, 29)
FIXED_18E_YELLOW_SECONDS = 3
TLS_18E = "cluster12834017505_13817051850_2079964423"
CENTER_18E_EDGES = {"-1523207559", "1511909550"}
OUTER_18E_EDGES = {"1424752054#4", "1424752055#1"}
SIDE_18E_EDGE = "-1094755428#1"


def sumo_binary(name):
    """Use the project-pinned SUMO tools for both GUI and command-line runs."""
    import sumo

    suffix = ".exe" if sys.platform == "win32" else ""
    return str(Path(sumo.SUMO_HOME) / "bin" / (name + suffix))


def write_xml(path, root):
    """Publish a complete, parsed XML file through a temporary file in the same folder."""
    path = Path(path)
    ET.indent(root, space="  ")
    with tempfile.NamedTemporaryFile(
        dir=path.parent, prefix=path.name + ".", suffix=".tmp", delete=False
    ) as stream:
        temporary = Path(stream.name)
        try:
            ET.ElementTree(root).write(stream, encoding="utf-8", xml_declaration=True)
        except Exception:
            stream.close()
            temporary.unlink(missing_ok=True)
            raise
    try:
        ET.parse(temporary)
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def build_18e_phases(raw, source, validate_moves=True):
    """Build the two surveyed stages with yielding at crossing and merging links."""
    connections = sorted(
        (c for c in raw.findall("connection") if c.get("tl") == source.get("id")),
        key=lambda c: int(c.get("linkIndex")),
    )
    junction = next(j for j in raw.findall("junction") if j.get("id") == source.get("id"))
    requests = sorted(junction.findall("request"), key=lambda q: int(q.get("index")))
    if not connections or len(requests) != len(connections):
        raise RuntimeError("Check the 18E connection and conflict mapping.")
    if validate_moves and any(
        c.get("from") in CENTER_18E_EDGES and c.get("dir") in ("l", "L", "t", "T")
        for c in connections
    ):
        raise RuntimeError("Remove left turns and U-turns from the centre carriageway at 18E.")
    network_edges = {edge.get("id"): edge for edge in raw.findall("edge")}
    network_nodes = {node.get("id"): node for node in raw.findall("junction")}
    durations = [float(value) for value in FIXED_18E_GREEN_SECONDS]
    if len(durations) != 2 or any(not math.isfinite(d) or d <= 0 for d in durations):
        raise ValueError(
            "18E requires two positive green durations for the corridor and side road."
        )

    count = max(int(c.get("linkIndex")) for c in connections) + 1
    states = []
    audit = []
    for name, duration in zip(("cong_hoa_through", "18e_left_outer_uturn"), durations):
        selected = []
        for request_index, connection in enumerate(connections):
            approach = connection.get("from")
            incoming = network_edges[approach]
            outgoing = network_edges[connection.get("to")]
            incoming_dx = float(network_nodes[incoming.get("to")].get("x")) - float(
                network_nodes[incoming.get("from")].get("x")
            )
            outgoing_dx = float(network_nodes[outgoing.get("to")].get("x")) - float(
                network_nodes[outgoing.get("from")].get("x")
            )
            forward_merge = (
                connection.get("dir") in ("r", "R")
                and outgoing.get("name") == "Cộng Hòa"
                and incoming_dx * outgoing_dx > 0
            )
            through = connection.get("dir") == "s" or forward_merge
            right_into_18e = connection.get("to") == "1094755428#0" and connection.get("dir") == "r"
            if name == "cong_hoa_through":
                enabled = approach in CENTER_18E_EDGES | OUTER_18E_EDGES and (
                    through or right_into_18e
                )
                priority = 1 if approach in CENTER_18E_EDGES else 0
            else:
                enabled = approach == SIDE_18E_EDGE or (
                    approach in OUTER_18E_EDGES and not through and not right_into_18e
                )
                priority = 0 if approach == SIDE_18E_EDGE else 1
            if enabled:
                selected.append((priority, request_index, connection))
        state = ["r"] * count
        protected = []
        occupied_targets = set()
        for _, index, connection in sorted(selected, key=lambda item: (item[0], item[1])):
            target = (connection.get("to"), connection.get("toLane"))
            conflicting = target in occupied_targets or any(
                requests[index].get("foes")[-1 - other] == "1"
                or requests[other].get("foes")[-1 - index] == "1"
                for other in protected
            )
            state[int(connection.get("linkIndex"))] = "g" if conflicting else "G"
            if not conflicting:
                protected.append(index)
                occupied_targets.add(target)
        state = "".join(state)
        if not any(c in "Gg" for c in state):
            raise RuntimeError(f"Stage {name} serves no connections at 18E.")
        states.append(state)
        audit.append(
            {
                "movement_group": name,
                "duration_s": duration,
                "state": state,
                "timing_source": "field_survey",
                "served_connections": [dict(c.attrib) for _, _, c in selected],
            }
        )

    if validate_moves:
        unserved = [
            c for c in connections if all(state[int(c.get("linkIndex"))] == "r" for state in states)
        ]
        if unserved:
            moves = ", ".join(f"{c.get('from')} -> {c.get('to')}" for c in unserved)
            raise RuntimeError(
                f"18E connections never receive green: {moves}. Check lane connections."
            )
    phases = []
    for index, (state, duration) in enumerate(zip(states, durations)):
        following = states[(index + 1) % len(states)]
        yellow = "".join(
            "y" if a in "Gg" and b not in "Gg" else a for a, b in zip(state, following)
        )
        phases.extend([(duration, state), (FIXED_18E_YELLOW_SECONDS, yellow)])
    audit.append(
        {
            "cycle_s": sum(d for d, _ in phases),
            "through_red_s": durations[1] + FIXED_18E_YELLOW_SECONDS,
            "side_red_s": durations[0] + FIXED_18E_YELLOW_SECONDS,
            "reported_side_red_s": 67,
            "red_duration_note": "Program red is 70s with two separate 3s yellow transitions.",
        }
    )
    return phases, audit


def select_endpoints(net):
    """Select corridor endpoints using road names and coordinates."""
    corridor = [
        e
        for e in net.getEdges()
        if e.getName() == "Cộng Hòa" and allows_vehicle(e, "passenger") and (e.getLength() > 20)
    ]

    def dx(e):
        return e.getToNode().getCoord()[0] - e.getFromNode().getCoord()[0]

    west = [e for e in corridor if dx(e) < -5]
    east = [e for e in corridor if dx(e) > 5]
    start = max(west, key=lambda e: e.getFromNode().getCoord()[0])
    finish = min(west, key=lambda e: e.getToNode().getCoord()[0])
    reverse_start = min(east, key=lambda e: e.getFromNode().getCoord()[0])
    reverse_finish = max(east, key=lambda e: e.getToNode().getCoord()[0])
    return (start, finish, reverse_start, reverse_finish)


def find_route(net, a, b, vclass="passenger"):
    """Find a corridor-preferred route through vehicle-permitted connections."""
    queue = [(0, a.getID(), [a.getID()])]
    seen = set()
    while queue:
        cost, key, path = heapq.heappop(queue)
        if key in seen:
            continue
        seen.add(key)
        if key == b.getID():
            return path
        for nxt, links in net.getEdge(key).getOutgoing().items():
            if not allows_vehicle(nxt, vclass):
                continue
            if not any(
                c.getFromLane().allows(vclass) and c.getToLane().allows(vclass) and c.allows(vclass)
                for c in links
            ):
                continue
            penalty = 1 if nxt.getName() in ("Cộng Hòa", "Cầu vượt Hoàng Hoa Thám") else 50
            heapq.heappush(
                queue, (cost + nxt.getLength() * penalty, nxt.getID(), path + [nxt.getID()])
            )
    raise RuntimeError("No connected route for " + vclass)


def create_fixed_time_lights(raw):
    """Build network signal programmes from the shared survey table."""
    from .fixed_time_signals import build_programmes

    lights, report = build_programmes(
        raw, BASE / "signals/survey_observations.csv", build_18e_phases, TLS_18E
    )
    write_xml(OUT / "fixed.add.xml", lights)
    (OUT / "signal_plan.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def find_center_route(net, start, finish, vehicle_class):
    """Find the centre-carriageway route through the existing network connections."""
    direction = 1 if finish.getToNode().getCoord()[0] > start.getFromNode().getCoord()[0] else -1
    anchors = [
        edge
        for edge in net.getEdges()
        if edge.getID().lstrip("-").split("#")[0] in CENTER_WAY_IDS
        and allows_vehicle(edge, vehicle_class)
        and (edge.getToNode().getCoord()[0] - edge.getFromNode().getCoord()[0]) * direction > 0
    ]
    anchors.sort(key=lambda edge: edge.getFromNode().getCoord()[0] * direction)
    if not anchors:
        raise RuntimeError("Centre-carriageway and bridge edges are missing from the network.")
    path = [start.getID()]
    current = start
    for waypoint in anchors + [finish]:
        part = find_route(net, current, waypoint, vehicle_class)
        path.extend(part[1:])
        current = waypoint
    if len(path) != len(set(path)):
        raise RuntimeError("The centre route contains a loop. Check the connections in NetEdit.")
    return path


def repair_internal_lane_indexes(raw):
    """Restore numeric lane indexes after internal edges have been combined."""
    repaired = []
    for edge in raw.findall("edge"):
        if edge.get("function") != "internal":
            continue
        for index, lane in enumerate(edge.findall("lane")):
            expected_id = f"{edge.get('id')}_{index}"
            if lane.get("id") != expected_id:
                raise ValueError(f'Unexpected internal lane order: {lane.get("id")}')
            if lane.get("index") != str(index):
                repaired.append(lane.get("id"))
                lane.set("index", str(index))
    return repaired


def repair_source_network():
    before = SOURCE_NET.read_bytes()
    raw = ET.fromstring(gzip.decompress(before))
    repaired = repair_internal_lane_indexes(raw)
    if repaired:
        temporary = SOURCE_NET.with_suffix(".tmp")
        temporary.write_bytes(
            gzip.compress(ET.tostring(raw, encoding="utf-8", xml_declaration=True), mtime=0)
        )
        if SOURCE_NET.read_bytes() != before:
            temporary.unlink()
            raise RuntimeError("Source network changed during repair.")
        temporary.replace(SOURCE_NET)
    print(f"Repaired {len(repaired)} internal lane indexes: {repaired}")


def create_vehicle_types(routes):
    """Create mixed vehicle classes with single-file lane-based movement."""
    types = VEHICLE_TYPES
    for name, (vehicle_class, length, width, gap) in types.items():
        ET.SubElement(
            routes,
            "vType",
            id=name,
            vClass=vehicle_class,
            length=length,
            width=width,
            minGap=gap,
            tau="1.0",
            maxSpeed=f"{MAX_SPEED_KMH / 3.6:.6f}",
            speedFactor="1.0",
            speedDev="0",
            carFollowModel="Krauss",
            laneChangeModel="LC2013",
            lcAssertive="1",
            lcStrategic="5",
            lcCooperative="1",
            lcSpeedGain="0.5",
            jmAdvance="0",
            jmTimegapMinor="3",
            jmExtraGap="3",
            jmSigmaMinor="0",
        )
    return types


def create_traffic(net, start, finish, reverse_start, reverse_finish, forward, backward):
    """Create the four tracked journeys; ordinary traffic uses map-wide routes."""
    routes = ET.Element("routes")
    types = create_vehicle_types(routes)
    probe_routes = {}
    variant_paths = {}
    for kind in sorted({kind for kind, _ in PROBES.values()}):
        vehicle_class = types[kind][0]
        paths = {
            "outer": find_route(net, start, finish, vehicle_class),
            "center": find_center_route(net, start, finish, vehicle_class),
        }
        for variant, path in paths.items():
            route_id = f"probe_{kind}_{variant}_route"
            ET.SubElement(routes, "route", id=route_id, edges=" ".join(path))
            variant_paths[route_id] = path
            probe_routes[(kind, variant)] = route_id
    for probe_id, (kind, variant) in PROBES.items():
        ET.SubElement(
            routes,
            "vehicle",
            id=probe_id,
            type=kind,
            route=probe_routes[(kind, variant)],
            depart=f"{PROBE_DEPART_S:.3f}",
            departLane="best",
            departSpeed="max",
        )
    write_xml(OUT / "traffic.rou.xml", routes)
    (OUT / "route_variants.json").write_text(
        json.dumps(
            {
                "route_choice": "Frozen permitted routes; no imposed 50/50 carriageway split",
                "paths": variant_paths,
                "probes": {
                    pid: {"type": kind, "variant": variant, "route": probe_routes[(kind, variant)]}
                    for pid, (kind, variant) in PROBES.items()
                },
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return (collections.Counter(), 0, 0)


def create_network_background(net):
    """Generate boundary and interior journeys, including corridor side roads."""
    from .boundary_demand import get_demand_builder, LANE_CHANGE_PLANNING_DISTANCE_M

    builder = get_demand_builder(net)
    rng = random.Random(SEED + 100)
    generated_counts = {}
    template_counts = {}
    crossing_template_counts = {}
    side_approach_counts = {}
    airport_counts = {}
    corridor_counts = {}
    origin_counts = {}
    network_routes = []
    crossing_nodes = {
        node.getID()
        for node in net.getNodes()
        if any(e.getName() in ("Cộng Hòa", "Cầu vượt Hoàng Hoa Thám") for e in node.getIncoming())
    }
    for kind, rate in NETWORK_BACKGROUND_PER_HOUR.items():
        vehicle_class = {
            "car": "passenger",
            "motorcycle": "motorcycle",
            "truck": "truck",
            "bus": "bus",
        }[kind]
        pool = builder.background_pool(vehicle_class)
        side_records = builder.side_approach_pool(vehicle_class)
        pool = list(dict.fromkeys([*pool, *builder.partial_corridor_pool(vehicle_class, side_records)]))
        template_counts[kind] = len(pool)
        crossing_template_counts[kind] = sum(
            any(
                net.getEdge(edge_id).getToNode().getID() in crossing_nodes
                and net.getEdge(edge_id).getName() not in ("Cộng Hòa", "Cầu vượt Hoàng Hoa Thám")
                for edge_id in path[:-1]
            )
            for path in pool
        )
        routes = ET.Element("routes")
        pools = builder.departure_pools(pool)
        pools["interior"] = list(dict.fromkeys([
            *pools["interior"], *(record["edges"] for record in side_records)
        ]))
        airport_paths = builder.airport_pool(vehicle_class, side_records)
        pools["airport"] = airport_paths
        candidate_paths = [path for paths in pools.values() for path in paths]
        candidate_paths.extend(record["edges"] for record in side_records)
        if any(not builder.route_lane_feasible(path, vehicle_class) for path in candidate_paths):
            raise RuntimeError(f"Lane-infeasible route template for {vehicle_class}.")
        side_groups = collections.defaultdict(list)
        approach_counts = collections.Counter()
        route_ids = collections.defaultdict(list)
        route_uses_corridor = {}
        route_approaches = {}
        route_paths = {}
        for origin_type, paths in pools.items():
            for number, path in enumerate(paths):
                route_id = f"map_{kind}_{origin_type}_{number}"
                ET.SubElement(routes, "route", id=route_id, edges=" ".join(path))
                route_ids[origin_type].append(route_id)
                route_paths[route_id] = path
                route_uses_corridor[route_id] = any(
                    net.getEdge(edge_id).getName() in ("Cộng Hòa", "Cầu vượt Hoàng Hoa Thám")
                    for edge_id in path
                )
        for number, record in enumerate(side_records):
            route_id = f"map_{kind}_side_approach_{number}"
            ET.SubElement(routes, "route", id=route_id, edges=" ".join(record["edges"]))
            side_groups[record["incoming_edge"]].append(route_id)
            route_ids["side_approach"].append(route_id)
            route_approaches[route_id] = record["incoming_edge"]
            route_paths[route_id] = record["edges"]
            route_uses_corridor[route_id] = any(
                net.getEdge(edge_id).getName() in ("Cộng Hòa", "Cầu vượt Hoàng Hoa Thám")
                for edge_id in record["edges"]
            )
        side_edges = sorted(side_groups)
        if not (
            0 <= INTERIOR_DEPARTURE_SHARE <= 1
            and SIDE_APPROACH_BACKGROUND_SHARE >= 0
            and AIRPORT_BACKGROUND_SHARE >= 0
            and SIDE_APPROACH_BACKGROUND_SHARE + AIRPORT_BACKGROUND_SHARE
            <= INTERIOR_DEPARTURE_SHARE
        ):
            raise ValueError(
                "Side-road and T3 shares must fit inside the interior departure share."
            )
        corridor_share = REFERENCE_CORRIDOR_DEMAND_VPH / REFERENCE_TOTAL_DEMAND_VPH
        if not 0 <= corridor_share <= 1:
            raise ValueError("Corridor-related demand must fit inside the whole-map demand budget.")
        origin_weights = {
            "boundary": 1 - INTERIOR_DEPARTURE_SHARE,
            "interior": INTERIOR_DEPARTURE_SHARE - SIDE_APPROACH_BACKGROUND_SHARE - AIRPORT_BACKGROUND_SHARE,
            "side_approach": SIDE_APPROACH_BACKGROUND_SHARE,
            "airport": AIRPORT_BACKGROUND_SHARE,
        }
        choices = {
            uses_corridor: {
                origin: [route_id for route_id in ids if route_uses_corridor[route_id] == uses_corridor]
                for origin, ids in route_ids.items()
            }
            for uses_corridor in (False, True)
        }
        exit_groups = {}
        for origin, ids in choices[True].items():
            groups = collections.defaultdict(list)
            weights = {}
            for route_id in ids:
                path = route_paths[route_id]
                incoming_id, exit_id = next(
                    (a, b) for a, b in zip(path, path[1:])
                    if net.getEdge(a).getName() in ("Cộng Hòa", "Cầu vượt Hoàng Hoa Thám")
                    and net.getEdge(b).getName() not in ("Cộng Hòa", "Cầu vượt Hoàng Hoa Thám")
                )
                exit_edge = net.getEdge(exit_id)
                road = exit_edge.getName() or exit_edge.getID()
                groups[road].append(route_id)
                connections = net.getEdge(incoming_id).getAllowedOutgoing(vehicle_class)[exit_edge]
                permitted = [c for c in connections if allows_lane(c.getFromLane(), vehicle_class) and allows_lane(c.getToLane(), vehicle_class)]
                movement_lanes = min(
                    len({c.getFromLane().getIndex() for c in permitted}),
                    len({c.getToLane().getIndex() for c in permitted}),
                )
                weights[road] = max(weights.get(road, 0), movement_lanes)
            exit_groups[origin] = (groups, weights)
        airport_count = 0
        amount = round(rate * DEMAND_DURATION_S / 3600)
        corridor_amount = round(amount * corridor_share)
        actual_origins = collections.Counter()
        for i in range(amount):
            depart = (i + rng.random()) * DEMAND_DURATION_S / amount
            uses_corridor = (i + 1) * corridor_amount // amount > i * corridor_amount // amount
            available = [origin for origin, ids in choices[uses_corridor].items() if ids and origin_weights[origin] > 0]
            if not available:
                raise RuntimeError(f"No departure templates for corridor use={uses_corridor}, vehicle={kind}.")
            origin_type = rng.choices(available, weights=[origin_weights[origin] for origin in available])[0]
            if uses_corridor:
                groups, weights = exit_groups[origin_type]
                roads = list(groups)
                road = rng.choices(roads, weights=[weights[name] for name in roads])[0]
                selected_route = rng.choice(groups[road])
            else:
                selected_route = rng.choice(choices[False][origin_type])
            interior = origin_type != "boundary"
            actual_origins[origin_type] += 1
            airport_count += int(origin_type == "airport")
            if origin_type == "side_approach":
                approach_counts[route_approaches[selected_route]] += 1
            ET.SubElement(
                routes,
                "vehicle",
                id=f"map_{kind}_{i}",
                type=kind,
                route=selected_route,
                depart=f"{depart:.3f}",
                departLane="best",
                departSpeed="max",
                departPos="random" if interior else "base",
            )
        name = f"map_{kind}.rou.xml"
        write_xml(OUT / name, routes)
        generated_counts[kind] = amount
        corridor_counts[kind] = corridor_amount
        origin_counts[kind] = dict(actual_origins)
        airport_counts[kind] = {
            "generated_vehicles": airport_count,
            "requested_per_hour": round(airport_count * 3600 / DEMAND_DURATION_S, 2),
            "departure_edges": sorted({path[0] for path in airport_paths}),
        }
        side_approach_counts[kind] = [
            {
                "incoming_edge": approach,
                "road": net.getEdge(approach).getName(),
                "junction": net.getEdge(approach).getToNode().getID(),
                "generated_vehicles": approach_counts[approach],
                "requested_per_hour": round(
                    approach_counts[approach] * 3600 / DEMAND_DURATION_S, 2
                ),
            }
            for approach in side_edges
        ]
        network_routes.append(name)
    (OUT / "network_demand.json").write_text(
        json.dumps(
            {
                "requested_per_hour": NETWORK_BACKGROUND_PER_HOUR,
                "generated_vehicles": generated_counts,
                "reference_corridor_related_vph": REFERENCE_CORRIDOR_DEMAND_VPH,
                "corridor_related_generated_vehicles": corridor_counts,
                "actual_departure_origins": origin_counts,
                "corridor_demand_definition": "Requested journeys using at least one Cong Hoa segment, including side-road entries and departures. Four probes traverse the complete corridor. Passage counts at a single section are recorded separately.",
                "corridor_exit_selection": "Select a departure origin group, then a first exit road weighted by the number of permitted movement lanes, then a route. Includes rim-to-side-entry paths. Road width and template multiplicity do not set turn capacity.",
                "background_route_templates": template_counts,
                "route_templates_using_cong_hoa_side_approaches": crossing_template_counts,
                "distinct_edges_on_generated_routes": len(builder.covered_edges),
                "boundary_origins": [e.getID() for e in builder.origins],
                "boundary_destinations": [e.getID() for e in builder.destinations],
                "exit_policy": "Outward terminal arterial edges in the boundary band, with no non-U-turn continuation for the simulated vehicle classes.",
                "background_routing_policy": "Fastest permitted lane-feasible paths, respecting vehicle width and excluding U-turn connections.",
                "lane_feasible_route_templates_verified": True,
                "multi_lane_change_route_planning_distance_m_per_lane": LANE_CHANGE_PLANNING_DISTANCE_M,
                "boundary_band_fraction": 0.09,
                "background_multiplier": MAP_DEMAND_MULTIPLIER,
                "interior_departure_share": INTERIOR_DEPARTURE_SHARE,
                "side_approach_background_share": SIDE_APPROACH_BACKGROUND_SHARE,
                "airport_background_share": AIRPORT_BACKGROUND_SHARE,
                "airport_departures": airport_counts,
                "signalised_side_approach_departures": side_approach_counts,
                "note": "Boundary, interior, side-road and T3 weights are departure preferences within available corridor/non-corridor route pools. Actual origin allocations are recorded. All journeys end at peripheral outlets. Bus journeys are synthetic.",
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return network_routes


def create_configuration():
    """Write SUMO input paths and output settings."""
    config = ET.Element("configuration")
    inputs = ET.SubElement(config, "input")
    ET.SubElement(inputs, "net-file", value="network_snapshot.net.xml.gz")
    ET.SubElement(
        inputs,
        "route-files",
        value="traffic.rou.xml,"
        + ",".join(f"map_{kind}.rou.xml" for kind in NETWORK_BACKGROUND_PER_HOUR),
    )
    ET.SubElement(inputs, "additional-files", value="fixed.add.xml")
    ET.SubElement(inputs, "route-steps", value="0")  # Load the complete route input at startup.
    time = ET.SubElement(config, "time")
    ET.SubElement(time, "end", value=str(SIMULATION_END_S))
    ET.SubElement(time, "step-length", value=str(SIMULATION_STEP_S))
    processing = ET.SubElement(config, "processing")
    ET.SubElement(processing, "time-to-teleport", value="-1")
    ET.SubElement(processing, "collision.mingap-factor", value="0")
    ET.SubElement(processing, "collision.check-junctions", value="true")
    ET.SubElement(processing, "waiting-time-memory", value=str(SIMULATION_END_S + 10))
    randomness = ET.SubElement(config, "random_number")
    ET.SubElement(randomness, "seed", value=str(SEED))
    output = ET.SubElement(config, "output")
    ET.SubElement(output, "tripinfo-output", value="tripinfo.xml")
    ET.SubElement(output, "tripinfo-output.write-unfinished", value="true")
    ET.SubElement(output, "summary-output", value="summary.xml")
    write_xml(OUT / "fixed_time.sumocfg", config)
    output.find("tripinfo-output").set("value", "view_tripinfo.xml")
    output.find("summary-output").set("value", "view_summary.xml")
    write_xml(OUT / "view.sumocfg", config)


def create_corridor_counters(net, forward):
    """Place vehicle-class counters across the corridor in 600-second intervals."""
    x, y = net.getNode(CORRIDOR_COUNT_NODE).getCoord()
    target = (x + CORRIDOR_COUNT_OFFSET_M, y)
    tree = ET.parse(OUT / "fixed.add.xml")
    stations = []
    for edge in net.getEdges():
        if edge.getName() not in ("Cộng Hòa", "Cầu vượt Hoàng Hoa Thám"):
            continue
        for lane in edge.getLanes():
            distance = 0
            for a, b in zip(lane.getShape(), lane.getShape()[1:]):
                segment = math.dist(a, b)
                if min(a[0], b[0]) <= target[0] < max(a[0], b[0]):
                    fraction = (target[0] - a[0]) / (b[0] - a[0])
                    y = a[1] + fraction * (b[1] - a[1])
                    if abs(y - target[1]) < 100:
                        position = min(
                            lane.getLength() - 0.1, max(0.1, distance + fraction * segment)
                        )
                        direction = "truong_chinh" if b[0] < a[0] else "hoang_van_thu"
                        for kind in VEHICLE_SHARES:
                            detector_id = f"ch_count_{direction}_{kind}_{lane.getID()}"
                            ET.SubElement(
                                tree.getroot(),
                                "inductionLoop",
                                id=detector_id,
                                lane=lane.getID(),
                                pos=f"{position:.2f}",
                                period="600",
                                file="cong_hoa_counts.xml",
                                vTypes=kind,
                            )
                        stations.append(
                            {"lane": lane.getID(), "direction": direction, "position_m": position}
                        )
                    break
                distance += segment
    if not stations or len({s["direction"] for s in stations}) != 2:
        raise RuntimeError("Could not place counters for both corridor directions.")
    write_xml(OUT / "fixed.add.xml", tree.getroot())
    return stations


def summarize_corridor_counts(count_file=None):
    """Export recorded corridor crossings in ten-minute intervals."""
    count_file = Path(count_file) if count_file else OUT / "cong_hoa_counts.xml"
    parser = ET.XMLPullParser(events=("end",))
    intervals = []
    with count_file.open(encoding="utf-8") as stream:
        for chunk in iter(lambda: stream.read(65536), ""):
            parser.feed(chunk)
            for _, element in parser.read_events():
                if element.tag == "interval":
                    intervals.append(dict(element.attrib))
    totals = collections.defaultdict(collections.Counter)
    seen_detectors = collections.defaultdict(set)
    expected_detectors = len(ET.parse(OUT / "fixed.add.xml").getroot().findall("inductionLoop"))
    for interval in intervals:
        detector = interval.get("id")
        for direction in ("truong_chinh", "hoang_van_thu"):
            for kind in VEHICLE_SHARES:
                if detector.startswith(f"ch_count_{direction}_{kind}_"):
                    key = (float(interval.get("begin")), float(interval.get("end")))
                    totals[key][kind] += int(float(interval.get("nVehEntered", "0")))
                    seen_detectors[key].add(detector)
    rows = []
    for (begin, end), counts in sorted(totals.items()):
        total = sum(counts.values())
        rows.append(
            {
                "begin_s": begin,
                "end_s": end,
                **{kind: counts[kind] for kind in VEHICLE_SHARES},
                "total_both_directions": total,
                "target_600s": REFERENCE_COUNT_10_MIN,
                "target_source": "Approximate two-direction passage estimate from a ten-minute video",
                "demand_scale": DEMAND_SCALE,
                "complete_600s_window": abs(end - begin - 600) < 0.1
                and len(seen_detectors[(begin, end)]) == expected_detectors,
                "motorcycle_percent": round(100 * counts["motorcycle"] / total, 2) if total else 0,
            }
        )
    if rows:
        with (OUT / "traffic_count_comparison.csv").open(
            "w", newline="", encoding="utf-8-sig"
        ) as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
    print(json.dumps(rows, ensure_ascii=False, indent=2))


def save_scenario(net, start, finish, forward, counts, side_count):
    """Record route IDs, endpoint coordinates, input hashes and assumptions."""
    manifest = {
        "network_sha256": hashlib.sha256(NET.read_bytes()).hexdigest(),
        "source_network_sha256": hashlib.sha256(SOURCE_NET.read_bytes()).hexdigest(),
        "seed": SEED,
        "probe_type": "passenger car and motorcycle on outer and center routes",
        "probe_ids": list(PROBES),
        "route_choice": "Frozen generated routes and specified centre/outer probe paths",
        "demand_scale": DEMAND_SCALE,
        "direct_corridor_share": DIRECT_CORRIDOR_SHARE,
        "reference_total_requested_vph": REFERENCE_TOTAL_DEMAND_VPH,
        "corridor_related_requested_vph": sum(NETWORK_BACKGROUND_PER_HOUR.values()) * REFERENCE_CORRIDOR_DEMAND_VPH / REFERENCE_TOTAL_DEMAND_VPH,
        "corridor_related_generated_vehicles": json.loads((OUT / "network_demand.json").read_text(encoding="utf-8"))["corridor_related_generated_vehicles"],
        "map_demand_multiplier": MAP_DEMAND_MULTIPLIER,
        "network_background_requested_per_hour": NETWORK_BACKGROUND_PER_HOUR,
        "network_background_generated": json.loads(
            (OUT / "network_demand.json").read_text(encoding="utf-8")
        )["generated_vehicles"],
        "requested_depart_s": PROBE_DEPART_S,
        "demand_duration_s": DEMAND_DURATION_S,
        "corridor_vehicles_per_hour_per_direction": 0,
        "corridor_requested_vph_forward": 0,
        "corridor_requested_vph_reverse": 0,
        "corridor_observation": {
            "estimated_vehicles_per_second_both_directions": CORRIDOR_OBSERVED_TOTAL_VPS,
            "equivalent_vehicles_per_hour": CORRIDOR_OBSERVED_TOTAL_VPS * 3600,
            "video_duration_s": OBSERVATION_DURATION_S,
            "source": "User estimate based on a ten-minute video",
            "counting_location": "Cong Hoa Garden / Duong 20 Cong Hoa; adjacent section 40 m east of junction 2079964787",
            "calibration_status": "Video estimate retained separately. User-selected reference requests ten corridor-related journeys/second. Realised passage at this section is measured separately.",
        },
        "reverse_demand_ratio": REVERSE_DEMAND_RATIO,
        "corridor_mix": dict(VEHICLE_SHARES),
        "dedicated_short_cross_routes": side_count,
        "cross_vehicles_per_hour_per_route": CROSS_FLOW_VEHICLES,
        "background_counts": dict(counts),
        "route_edges": forward,
        "route_length_m": sum((net.getEdge(e).getLength() for e in forward)),
        "route_street_names": dict(
            collections.Counter((net.getEdge(e).getName() for e in forward))
        ),
        "start_xy": start.getFromNode().getCoord(),
        "end_xy": finish.getToNode().getCoord(),
        "start_junction": start.getFromNode().getID(),
        "end_junction": finish.getToNode().getID(),
        "signal_policy": "Common corridor survey table; inverse crossing phases; other competing approaches 30s green and 3s yellow",
        "survey_18e": {
            "through_green_s": FIXED_18E_GREEN_SECONDS[0],
            "side_left_outer_uturn_green_s": FIXED_18E_GREEN_SECONDS[1],
            "yellow_s": FIXED_18E_YELLOW_SECONDS,
            "reported_side_red_s": 67,
            "program_side_red_s": 70,
        },
        "demand_status": "Ordinary vehicles use distributed map-wide routes. Only tracked vehicles have imposed full-corridor journeys. The estimated passage target is 20 vehicles/second for both directions from a ten-minute video. The total map demand budget is a separate scenario assumption; passage flow requires calibration.",
        "vehicle_movement_model": "lane_based",
        "lane_change_model": "LC2013",
        "car_follow_model": "Krauss",
        "junction_model": {"minor_time_gap_s": 3, "extra_gap_m": 3, "minor_imperfection": 0},
        "collision_detection": {
            "minimum_gap_factor": 0,
            "check_junctions": True,
            "definition": "Physical body contact/overlap; desired-gap violations alone do not trigger teleport",
        },
        "motorcycle_model": "LC2013; single-file movement within each lane; normal strategic/cooperative lane changes; width 0.8 m; tau 1 s; step 0.25 s",
        "simulation_end_s": SIMULATION_END_S,
    }
    (OUT / "scenario.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def run_sumo(gui=False, full_network=False):
    """Run the prepared scenario with its frozen routes and fixed-time signals."""
    import traci

    configuration = OUT / ("view.sumocfg" if gui else "fixed_time.sumocfg")
    command = [
        sumo_binary("sumo-gui" if gui else "sumo"),
        "-c",
        str(configuration),
        "--no-step-log",
        "true",
    ]
    if gui:
        command += ["--start", "--delay", "0"]
    traci.start(command)
    completed = set()
    try:
        while (
            traci.simulation.getMinExpectedNumber() > 0
            and traci.simulation.getTime() < SIMULATION_END_S
        ):
            traci.simulationStep()
            completed.update(set(traci.simulation.getArrivedIDList()) & PROBES.keys())
            if not gui and not full_network and len(completed) == len(PROBES):
                break
    finally:
        traci.close()


def read_probe_result(probe_id=PROBE_ID):
    """Read tracked journey duration and its separate insertion delay."""
    trips = ET.parse(OUT / "tripinfo.xml").getroot()
    probe = next((t for t in trips.findall("tripinfo") if t.get("id") == probe_id), None)
    if probe is None:
        raise RuntimeError("Probe did not enter network")
    completed = float(probe.get("arrival")) >= 0
    steps = ET.parse(OUT / "summary.xml").getroot().findall("step")
    last = steps[-1]
    row = {
        "probe_id": probe_id,
        "vehicle_type": PROBES[probe_id][0],
        "route_variant": PROBES[probe_id][1],
        "method": "Fixed-time",
        "completed": completed,
        "travel_time_s": probe.get("duration") if completed else "",
        "travel_time_min": round(float(probe.get("duration")) / 60, 2) if completed else "",
        "waiting_time_s": probe.get("waitingTime"),
        "stops": probe.get("waitingCount"),
        "depart_delay_s": probe.get("departDelay"),
        "actual_depart_s": probe.get("depart"),
        "arrival_s": probe.get("arrival"),
        "route_length_m": probe.get("routeLength"),
        "time_loss_s": probe.get("timeLoss"),
        "collisions": last.get("collisions"),
        "teleports": last.get("teleports"),
        "inserted_vehicles": last.get("inserted"),
        "pending_vehicles": last.get("waiting"),
        "total_time_including_insertion_queue_s": (
            round(float(probe.get("duration")) + float(probe.get("departDelay")), 2)
            if completed
            else ""
        ),
        "note": "Single run; assumed demand; static nominal phases, not validated real-world baseline",
        "valid_for_comparison": completed
        and int(last.get("collisions", "0")) == 0
        and int(last.get("teleports", "0")) == 0,
    }
    return row


def save_result(measurements):
    """Write measured SUMO journeys to CSV and JSON."""
    with (OUT / "comparison.csv").open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(measurements[0]))
        writer.writeheader()
        writer.writerows(measurements)
    (OUT / "result.json").write_text(
        json.dumps(measurements, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(measurements, ensure_ascii=False, indent=2), flush=True)


def main(prepare_only=False):
    OUT.mkdir(exist_ok=True)
    source_bytes = SOURCE_NET.read_bytes()
    # Parse the source before writing the simulation snapshot.
    snapshot = ET.fromstring(gzip.decompress(source_bytes))
    capped_lanes = 0
    for edge in snapshot.findall("edge"):
        if edge.get("function") == "internal":
            continue
        for lane in edge.findall("lane"):
            if float(lane.get("speed")) > MAX_SPEED_KMH / 3.6:
                lane.set("speed", f"{MAX_SPEED_KMH / 3.6:.6f}")
                capped_lanes += 1
    NET.write_bytes(
        gzip.compress(ET.tostring(snapshot, encoding="utf-8", xml_declaration=True), mtime=0)
    )
    net = sumolib.net.readNet(str(NET))
    raw = ET.fromstring(gzip.decompress(NET.read_bytes()))
    start, finish, reverse_start, reverse_finish = select_endpoints(net)
    forward = find_route(net, start, finish)
    backward = find_route(net, reverse_start, reverse_finish)
    print("Tracked vehicles:", ", ".join(PROBES), start.getID(), "→", finish.getID(), flush=True)
    create_fixed_time_lights(raw)
    counts, side_count, vehicle_count = create_traffic(
        net, start, finish, reverse_start, reverse_finish, forward, backward
    )
    create_network_background(net)
    stations = create_corridor_counters(net, forward)
    create_configuration()
    save_scenario(net, start, finish, forward, counts, side_count)
    scenario_path = OUT / "scenario.json"
    scenario = json.loads(scenario_path.read_text(encoding="utf-8"))
    scenario.update(
        reference_count_10_min_both_directions=REFERENCE_COUNT_10_MIN,
        departure_origins="mixed_boundary_and_interior",
        interior_departure_share=INTERIOR_DEPARTURE_SHARE,
        max_speed_kmh=MAX_SPEED_KMH,
        capped_external_lanes=capped_lanes,
        traffic_counters=stations,
        counter_period_s=600,
        map_multiplier=MAP_DEMAND_MULTIPLIER,
    )
    scenario_path.write_text(json.dumps(scenario, ensure_ascii=False, indent=2), encoding="utf-8")
    if prepare_only:
        print("Prepared scenario inputs. Open the simulation with --view.", flush=True)
        return
    print("Starting SUMO; requested corridor vehicles:", vehicle_count, flush=True)
    run_sumo(full_network="--full-network" in sys.argv)
    measurements = [read_probe_result(probe_id) for probe_id in PROBES]
    save_result(measurements)


def cli():
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_mutually_exclusive_group()
    actions.add_argument(
        "--prepare", action="store_true", help="Generate scenario inputs without running SUMO."
    )
    actions.add_argument(
        "--view", action="store_true", help="Open the prepared scenario in SUMO GUI."
    )
    actions.add_argument(
        "--counts", action="store_true", help="Summarise recorded corridor detector counts."
    )
    actions.add_argument(
        "--repair-network", action="store_true", help="Repair duplicated internal lane indexes."
    )
    parser.add_argument("--count-file", type=Path)
    parser.add_argument(
        "--full-network", action="store_true", help="Continue after tracked vehicles arrive."
    )
    args = parser.parse_args()
    if args.counts:
        summarize_corridor_counts(args.count_file)
    elif args.view:
        run_sumo(gui=True)
    elif args.repair_network:
        repair_source_network()
    else:
        main(prepare_only=args.prepare)


if __name__ == "__main__":
    cli()
