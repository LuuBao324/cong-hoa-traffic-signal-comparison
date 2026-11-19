"""Generate boundary and interior departure routes over the connected road network."""

from collections import defaultdict, deque
from functools import lru_cache
import math
import random
import heapq
from .vehicle_types import allows_vehicle, allows_lane

CORRIDOR_NAMES = {"Cộng Hòa", "Cầu vượt Hoàng Hoa Thám"}
LANE_CHANGE_PLANNING_DISTANCE_M = 30


class BoundaryDemand:
    def __init__(self, net):
        self.net = net
        self.bounds = net.getBoundary()
        self.origins = self.select_boundary_edges(entering=True)
        self.destinations = self.select_boundary_edges(entering=False)
        self.exit_ids = {edge.getID() for edge in self.destinations}
        self.path_cache = {}
        self.outgoing_cache = {}
        self.background_cache = {}
        self.covered_edges = set()
        if len(self.origins) < 8 or len(self.destinations) < 8:
            raise RuntimeError("Too few usable boundary roads for map-wide traffic.")
        print(
            f"Boundary roads: {len(self.origins)} entries, {len(self.destinations)} exits.",
            flush=True,
        )

    def select_boundary_edges(self, entering):
        xmin, ymin, xmax, ymax = self.bounds
        width, height = xmax - xmin, ymax - ymin
        centre = ((xmin + xmax) / 2, (ymin + ymax) / 2)
        band = min(width, height) * 0.09
        buckets = defaultdict(list)
        for edge in self.net.getEdges():
            if (
                not allows_vehicle(edge, "passenger")
                or not allows_vehicle(edge, "motorcycle")
                or edge.getLength() < 25
            ):
                continue
            if not entering:
                # Use terminal outward roads, so routes reach a real network outlet.
                if edge.getPriority() < 8:
                    continue
                has_continuation = any(
                    connection.getDirection() not in ("t", "T")
                    for vehicle_class in ("passenger", "motorcycle", "truck", "bus")
                    for connections in edge.getAllowedOutgoing(vehicle_class).values()
                    for connection in connections
                )
                if has_continuation:
                    continue
            points = edge.getShape()
            if len(points) < 2 or edge.getSpeed() < 8:
                continue
            point = points[0] if entering else points[-1]
            distances = (point[0] - xmin, xmax - point[0], point[1] - ymin, ymax - point[1])
            side = min(range(4), key=lambda i: distances[i])
            if distances[side] > band:
                continue
            dx, dy = points[-1][0] - points[0][0], points[-1][1] - points[0][1]
            inward = dx * (centre[0] - point[0]) + dy * (centre[1] - point[1])
            if (entering and inward <= 0) or (not entering and inward >= 0):
                continue
            position = (point[1] - ymin) / height if side < 2 else (point[0] - xmin) / width
            bucket = (side, min(11, int(position * 12)))
            score = (
                edge.getPriority() * 1000
                + len(edge.getLanes()) * 100
                + edge.getSpeed()
                + min(edge.getLength(), 200)
            )
            buckets[bucket].append((score, edge))
        return [
            edge
            for key in sorted(buckets)
            for _, edge in sorted(buckets[key], key=lambda pair: pair[0], reverse=True)[:2]
        ]

    def path(self, origin, destination, vehicle_class, avoid_corridor=False, initial_lanes=None, arrival_lanes=None):
        initial_lanes = tuple(sorted(initial_lanes)) if initial_lanes is not None else None
        arrival_lanes = tuple(sorted(arrival_lanes)) if arrival_lanes is not None else None
        key = (origin.getID(), destination.getID(), vehicle_class, avoid_corridor, initial_lanes, arrival_lanes)
        if key in self.path_cache:
            return self.path_cache[key]
        if not allows_vehicle(origin, vehicle_class) or not allows_vehicle(destination, vehicle_class):
            self.path_cache[key] = ()
            return ()
        # Retain the entering lane so short merge edges cannot hide infeasible turns.
        starts = [
            (origin.getID(), index) for index, lane in enumerate(origin.getLanes())
            if allows_lane(lane, vehicle_class)
            and (initial_lanes is None or index in initial_lanes)
        ]
        costs = {state: 0 for state in starts}
        parents = {state: None for state in starts}
        queue = [(0, state) for state in starts]
        heapq.heapify(queue)
        self.path_cache[key] = ()
        while queue:
            cost, state = heapq.heappop(queue)
            if cost != costs[state]:
                continue
            edge_id, lane_index = state
            if edge_id == destination.getID() and (arrival_lanes is None or lane_index in arrival_lanes):
                route = []
                while state is not None:
                    route.append(state[0])
                    state = parents[state]
                self.path_cache[key] = tuple(reversed(route))
                break
            for next_id, next_lane, travel_time in self.lane_successors(edge_id, lane_index, vehicle_class):
                if avoid_corridor and self.net.getEdge(next_id).getName() in CORRIDOR_NAMES:
                    continue
                next_cost = cost + travel_time
                next_state = (next_id, next_lane)
                if next_cost < costs.get(next_state, math.inf):
                    costs[next_state] = next_cost
                    parents[next_state] = state
                    heapq.heappush(queue, (next_cost, next_state))
        return self.path_cache[key]

    def lane_successors(self, edge_id, entry_lane, vehicle_class):
        edge = self.net.getEdge(edge_id)
        lanes = edge.getLanes()
        cache_key = (edge_id, vehicle_class)
        if cache_key not in self.outgoing_cache:
            self.outgoing_cache[cache_key] = [
                (target.getID(), connection.getFromLane().getIndex(), connection.getToLane().getIndex(),
                 target.getLength() / target.getSpeed())
                for target, connections in edge.getAllowedOutgoing(vehicle_class).items()
                for connection in connections
                if connection.getDirection() not in ("t", "T")
                and allows_lane(connection.getFromLane(), vehicle_class)
                and allows_lane(connection.getToLane(), vehicle_class)
            ]
        for target, source_lane, target_lane, travel_time in self.outgoing_cache[cache_key]:
            changes = abs(source_lane - entry_lane)
            if changes > 1 and changes * LANE_CHANGE_PLANNING_DISTANCE_M > edge.getLength():
                continue
            between = range(min(source_lane, entry_lane), max(source_lane, entry_lane) + 1)
            if all(allows_lane(lanes[index], vehicle_class) for index in between):
                yield target, target_lane, travel_time

    def reachable_lanes(self, route, vehicle_class, initial_lanes=None):
        if not route:
            return set()
        reachable = {
            index for index, lane in enumerate(self.net.getEdge(route[0]).getLanes())
            if allows_lane(lane, vehicle_class)
            and (initial_lanes is None or index in initial_lanes)
        }
        for edge_id, target in zip(route, route[1:]):
            reachable = {
                next_lane for lane in reachable
                for next_id, next_lane, _ in self.lane_successors(edge_id, lane, vehicle_class)
                if next_id == target
            }
            if not reachable:
                return set()
        return reachable

    def route_lane_feasible(self, route, vehicle_class):
        return bool(self.reachable_lanes(route, vehicle_class))

    def feasible_entry_lanes(self, route, vehicle_class):
        return {
            index for index in range(len(self.net.getEdge(route[0]).getLanes()))
            if self.reachable_lanes(route, vehicle_class, {index})
        }

    def validate_exit_routes(self, routes):
        for route in routes:
            if not route or route[-1] not in self.exit_ids:
                raise RuntimeError(
                    f"Route does not end at a selected network outlet: {route[-1:]}."
                )

    def near(self, edges, point):
        return sorted(edges, key=lambda e: math.dist(e.getFromNode().getCoord(), point))

    def corridor_pool(self, outer, centre, vehicle_class):
        start, finish = self.net.getEdge(outer[0]), self.net.getEdge(outer[-1])
        pool = []
        for core in (outer, centre):
            core_set = set(core)
            prefixes = []
            for edge in self.near(self.origins, start.getFromNode().getCoord()):
                if not allows_vehicle(edge, vehicle_class):
                    continue
                prefix = self.path(edge, start, vehicle_class)
                if prefix and not set(prefix[:-1]) & core_set:
                    prefixes.append(prefix)
                if len(prefixes) == 10:
                    break
            suffixes = []
            for edge in self.near(self.destinations, finish.getToNode().getCoord()):
                if not allows_vehicle(edge, vehicle_class):
                    continue
                suffix = self.path(finish, edge, vehicle_class)
                if suffix and not set(suffix[1:]) & core_set:
                    suffixes.append(suffix)
                if len(suffixes) == 10:
                    break
            for i, prefix in enumerate(prefixes):
                for suffix in suffixes[i % 3 :: 3]:
                    route = tuple(prefix[:-1]) + tuple(core) + tuple(suffix[1:])
                    if len(route) == len(set(route)) and self.route_lane_feasible(route, vehicle_class):
                        pool.append(route)
        pool = list(dict.fromkeys(pool))
        if not pool:
            raise RuntimeError(f"No boundary-to-boundary corridor routes for {vehicle_class}.")
        self.validate_exit_routes(pool)
        for route in pool:
            self.covered_edges.update(route)
        print(
            f"Corridor routes for {vehicle_class}: {len(pool)} boundary-to-boundary paths.",
            flush=True,
        )
        return pool

    def crossing_movements(self, vehicle_class):
        anchors = []
        for edge in self.net.getEdges():
            if edge.getName() in CORRIDOR_NAMES or not allows_vehicle(edge, vehicle_class):
                continue
            junction = edge.getToNode()
            if not any(e.getName() in CORRIDOR_NAMES for e in junction.getIncoming()):
                continue
            outgoing = edge.getAllowedOutgoing(vehicle_class)
            options = [
                (other, c)
                for other, connections in outgoing.items()
                for c in connections
                if c.getDirection() not in ("t", "T") and allows_vehicle(other, vehicle_class)
            ]
            options.sort(
                key=lambda item: (
                    item[0].getName() in CORRIDOR_NAMES,
                    item[1].getDirection() != "s",
                )
            )
            if options:
                anchors.append((edge, options[0][0]))
        return anchors

    def departure_pools(self, boundary_routes, corridor_start=None):
        """Keep full rim routes and add routes starting closer to active traffic."""
        interior = []
        for route in boundary_routes:
            if corridor_start is not None:
                # Corridor vehicles still traverse the complete measured corridor.
                start = route.index(corridor_start)
                interior.append(route[start:])
                continue
            lengths = [self.net.getEdge(edge_id).getLength() for edge_id in route]
            total = sum(lengths)
            for fraction in (0.25, 0.5, 0.7):
                travelled = 0
                for index, length in enumerate(lengths[:-1]):
                    travelled += length
                    if travelled >= total * fraction:
                        if total - travelled >= 500:
                            interior.append(route[index + 1 :])
                        break
        interior = list(dict.fromkeys(interior))
        if not interior:
            raise RuntimeError("No usable interior departure routes.")
        self.validate_exit_routes(interior)
        return {"boundary": boundary_routes, "interior": interior}

    def partial_corridor_pool(self, vehicle_class, side_records):
        """Extend side-entry journeys to rim origins without imposing a full arterial journey."""
        routes = []
        for record in side_records:
            tail = record["edges"]
            if not any(self.net.getEdge(edge_id).getName() in CORRIDOR_NAMES for edge_id in tail):
                continue
            entry = self.net.getEdge(tail[0])
            prefixes = 0
            for origin in self.near(self.origins, entry.getFromNode().getCoord()):
                if origin.getName() in CORRIDOR_NAMES:
                    continue
                prefix = self.path(origin, entry, vehicle_class, avoid_corridor=True,
                                   arrival_lanes=self.feasible_entry_lanes(tail, vehicle_class))
                route = prefix + tuple(tail[1:])
                if prefix and len(route) == len(set(route)) and self.route_lane_feasible(route, vehicle_class):
                    routes.append(route)
                    prefixes += 1
                if prefixes == 2:
                    break
        routes = list(dict.fromkeys(routes))
        self.validate_exit_routes(routes)
        for route in routes:
            self.covered_edges.update(route)
        return routes

    def side_departure_prefix(self, incoming, vehicle_class):
        """Find a connected upstream road without crossing Cong Hoa or making a U-turn."""
        queue = deque([([incoming], incoming.getLength())])
        visited = {incoming}
        best, best_length = None, 0
        while queue:
            prefix, length = queue.popleft()
            first = prefix[0]
            if first.getLength() >= 20 and length > best_length:
                best, best_length = prefix, length
                if length >= 250:
                    return prefix
            candidates = []
            for edge in first.getIncoming():
                links = edge.getAllowedOutgoing(vehicle_class).get(first, [])
                if (
                    edge not in visited
                    and allows_vehicle(edge, vehicle_class)
                    and edge.getName() not in CORRIDOR_NAMES
                    and any(link.getDirection() not in ("t", "T") for link in links)
                ):
                    candidates.append(edge)
            candidates.sort(
                key=lambda edge: (
                    edge.getName() == incoming.getName(),
                    edge.getPriority(),
                    edge.getLength(),
                ),
                reverse=True,
            )
            for edge in candidates:
                visited.add(edge)
                queue.append(([edge] + prefix, length + edge.getLength()))
        if best is None:
            raise RuntimeError(f"No safe departure edge upstream of {incoming.getID()}.")
        return best

    def side_approach_pool(self, vehicle_class):
        """Start upstream of each signalised side approach and cross its stop line."""
        records = []
        for incoming, _ in self.crossing_movements(vehicle_class):
            junction = incoming.getToNode()
            if "traffic_light" not in junction.getType():
                continue
            prefix = self.side_departure_prefix(incoming, vehicle_class)
            prefix_ids = tuple(edge.getID() for edge in prefix)
            incoming_lanes = self.reachable_lanes(prefix_ids, vehicle_class)
            if not incoming_lanes:
                prefix_ids = (incoming.getID(),)
                incoming_lanes = self.reachable_lanes(prefix_ids, vehicle_class)
            outgoing_options = incoming.getAllowedOutgoing(vehicle_class)
            outgoing_options = [
                edge
                for edge, links in outgoing_options.items()
                if allows_vehicle(edge, vehicle_class)
                and any(link.getDirection() not in ("t", "T") for link in links)
            ]
            outgoing_options.sort(key=lambda edge: edge.getName() in CORRIDOR_NAMES)
            approach_routes = []
            for outgoing in outgoing_options:
                entry_lanes = {
                    next_lane for lane in incoming_lanes
                    for next_id, next_lane, _ in self.lane_successors(incoming.getID(), lane, vehicle_class)
                    if next_id == outgoing.getID()
                }
                for destination in self.near(self.destinations, outgoing.getToNode().getCoord()):
                    if not allows_vehicle(destination, vehicle_class):
                        continue
                    tail = self.path(outgoing, destination, vehicle_class, initial_lanes=entry_lanes)
                    route = prefix_ids + tail
                    if tail and len(route) == len(set(route)) and self.route_lane_feasible(route, vehicle_class):
                        approach_routes.append(route)
                        break
                if len(approach_routes) == 3:
                    break
            if not approach_routes:
                raise RuntimeError(
                    f"No exit route for side approach {incoming.getID()} ({vehicle_class})."
                )
            for route in approach_routes:
                self.covered_edges.update(route)
                records.append(
                    {
                        "incoming_edge": incoming.getID(),
                        "junction": junction.getID(),
                        "road": incoming.getName(),
                        "edges": route,
                    }
                )
        if not records:
            raise RuntimeError(f"No signalised Cong Hoa side approaches for {vehicle_class}.")
        self.validate_exit_routes([record["edges"] for record in records])
        return records

    def airport_pool(self, vehicle_class, side_records):
        """Route vehicles from T3 terminal roads through a Cong Hoa approach."""
        origin_ids = ("1357708401", "1357708403", "1375824757#1", "1357708386")
        pool = []
        for origin_id in origin_ids:
            origin = self.net.getEdge(origin_id)
            if not allows_vehicle(origin, vehicle_class):
                continue
            targets = sorted(
                side_records,
                key=lambda record: math.dist(
                    origin.getToNode().getCoord(),
                    self.net.getEdge(record["incoming_edge"]).getToNode().getCoord(),
                ),
            )
            origin_routes = []
            for record in targets:
                incoming = self.net.getEdge(record["incoming_edge"])
                tail = record["edges"][record["edges"].index(incoming.getID()) + 1 :]
                before = self.path(origin, incoming, vehicle_class,
                                   arrival_lanes=self.feasible_entry_lanes((incoming.getID(),) + tuple(tail), vehicle_class))
                route = before + tail
                if before and len(route) == len(set(route)) and route not in origin_routes and self.route_lane_feasible(route, vehicle_class):
                    origin_routes.append(route)
                if len(origin_routes) == 3:
                    break
            if not origin_routes:
                raise RuntimeError(f"No T3-to-Cong-Hoa route from {origin_id} ({vehicle_class}).")
            pool.extend(origin_routes)
        if not pool:
            raise RuntimeError(f"No eligible T3 departure roads for {vehicle_class}.")
        self.validate_exit_routes(pool)
        for route in pool:
            self.covered_edges.update(route)
        return pool

    def background_pool(self, vehicle_class, size=384):
        if vehicle_class in self.background_cache:
            return self.background_cache[vehicle_class]
        rng = random.Random(20261111)
        origins = [e for e in self.origins if allows_vehicle(e, vehicle_class)]
        destinations = [e for e in self.destinations if allows_vehicle(e, vehicle_class)]
        diagonal = math.dist(self.bounds[:2], self.bounds[2:])
        pool = []
        for attempt in range(size * 8):
            origin = origins[attempt % len(origins)]
            far = [
                e
                for e in destinations
                if math.dist(origin.getFromNode().getCoord(), e.getToNode().getCoord())
                > diagonal * 0.3
            ]
            if not far:
                continue
            destination = rng.choice(far)
            route = self.path(origin, destination, vehicle_class)
            if route and len(route) == len(set(route)) and route not in pool:
                pool.append(route)
                if len(pool) % 48 == 0:
                    print(f"Background routes for {vehicle_class}: {len(pool)}/{size}.", flush=True)
            if len(pool) == size:
                break
        if len(pool) < 12:
            raise RuntimeError(f"Only {len(pool)} usable whole-map routes for {vehicle_class}.")
        self.validate_exit_routes(pool)
        for route in pool:
            self.covered_edges.update(route)
        self.background_cache[vehicle_class] = pool
        return pool


@lru_cache(maxsize=1)
def get_demand_builder(net):
    return BoundaryDemand(net)
