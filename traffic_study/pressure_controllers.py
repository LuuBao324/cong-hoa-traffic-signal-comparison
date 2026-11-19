"""Shared signal transitions, movement observations and controller execution."""

from collections import defaultdict
import math
import traci.constants as tc

DECISION_S = 10
YELLOW_S = 3
ALL_RED_S = (
    0  # No extra all-red for this corridor experiment; configurable independently of pressure.
)
SWITCH_PROTECTION_K = 0.2  # Assumed tuning parameter, not calibrated to this network.


def yellow_transition(current, target):
    """Clear departing movements while preserving movements green in both phases."""
    if len(current) != len(target):
        raise ValueError("Signal states must have equal lengths")
    result = []
    for old, new in zip(current, target):
        if old in "Gg" and new in "Gg":
            result.append("g" if "g" in (old, new) else "G")
        elif old in "Gg":
            result.append("y")
        else:
            result.append("r")
    return "".join(result)


def served_lanes(movement, state):
    """Only lanes whose own connection has green, including shared turn lanes."""
    mapping = movement.get("link_lanes")
    if mapping is None:  # Compatibility with historic metadata/unit fixtures.
        return movement["lanes"] if any(state[i] in "Gg" for i in movement["links"]) else set()
    return {lane for index, lanes in mapping.items() if state[index] in "Gg" for lane in lanes}


def served_out_lanes(movement, state):
    mapping = movement.get("link_out_lanes")
    if mapping is None:
        return movement["out_lanes"] if served_lanes(movement, state) else set()
    return {lane for index, lanes in mapping.items() if state[index] in "Gg" for lane in lanes}


class PressureController:
    def observe(self, now, vehicles, edge_vehicles, movements):
        pass

    def paper_score(self, tid, state, up, down, movement, upstream, downstream, now):
        raise NotImplementedError(self.method)

    def paper_phase(self, tid, signal, now, scores, demand, extensions):
        return None

    def __init__(self, api, net, method):
        self.api, self.net, self.method = api, net, method
        self.routes = {}
        self.signals = {}
        self.switches = 0
        self.decisions = 0
        self.next_observation = 1.0
        for tid in api.trafficlight.getIDList():
            logic = next(
                l
                for l in api.trafficlight.getAllProgramLogics(tid)
                if l.programID == api.trafficlight.getProgram(tid)
            )
            greens = list(
                dict.fromkeys(
                    p.state
                    for p in logic.phases
                    if any(c in "Gg" for c in p.state) and "y" not in p.state
                )
            )
            if len(greens) < 2:
                continue
            links = api.trafficlight.getControlledLinks(tid)
            movements = defaultdict(
                lambda: {
                    "lanes": set(),
                    "out_lanes": set(),
                    "links": set(),
                    "link_lanes": defaultdict(set),
                    "link_out_lanes": defaultdict(set),
                }
            )
            for index, group in enumerate(links):
                for incoming, outgoing, _ in group:
                    pair = (
                        net.getLane(incoming).getEdge().getID(),
                        net.getLane(outgoing).getEdge().getID(),
                    )
                    movements[pair]["lanes"].add(incoming)
                    movements[pair]["out_lanes"].add(outgoing)
                    movements[pair]["links"].add(index)
                    movements[pair]["link_lanes"][index].add(incoming)
                    movements[pair]["link_out_lanes"][index].add(outgoing)
            # Use existing green states; do not invent conflicting combinations.
            current = api.trafficlight.getRedYellowGreenState(tid)
            chosen = current if current in greens else greens[0]
            api.trafficlight.setRedYellowGreenState(tid, chosen)
            self.signals[tid] = dict(
                greens=greens,
                movements=movements,
                state=chosen,
                target=None,
                stage="green",
                until=DECISION_S,
                since=0,
                last={s: 0 for s in greens},
            )
        self.interval = DECISION_S
        for signal in self.signals.values():
            signal["until"] = self.interval

    def activate_target(self, tid, signal, now):
        self.api.trafficlight.setRedYellowGreenState(tid, signal["target"])
        signal.update(
            stage="green",
            state=signal["target"],
            since=now,
            until=now + signal.get("target_duration", self.interval),
        )
        signal["last"][signal["state"]] = now

    def step(self, now, departed):
        api = self.api
        for vid in departed:
            self.routes[vid] = api.vehicle.getRoute(vid)
            api.vehicle.subscribe(
                vid,
                (
                    tc.VAR_ROAD_ID,
                    tc.VAR_LANE_ID,
                    tc.VAR_LANEPOSITION,
                    tc.VAR_SPEED,
                    tc.VAR_ROUTE_INDEX,
                    tc.VAR_WAITING_TIME,
                    tc.VAR_ACCUMULATED_WAITING_TIME,
                ),
            )
        if now + 1e-7 < getattr(self, "next_observation", 1.0):
            return
        self.next_observation = math.floor(now + 1e-7) + 1
        # SUMO subscriptions avoid one socket request per vehicle measurement.
        vehicles = api.vehicle.getAllSubscriptionResults()
        movements = defaultdict(list)
        edge_vehicles = defaultdict(list)
        for vid, values in vehicles.items():
            road = values.get(tc.VAR_ROAD_ID, "")
            if road.startswith(":") or road not in self.net._id2edge:
                continue
            idx = values[tc.VAR_ROUTE_INDEX]
            route = self.routes.get(vid, ())
            info = (vid, values[tc.VAR_LANE_ID], values[tc.VAR_LANEPOSITION], values[tc.VAR_SPEED])
            edge_vehicles[road].append(info)
            if idx + 1 < len(route):
                movements[(road, route[idx + 1])].append(info)
        self.observe(now, vehicles, edge_vehicles, movements)
        for tid, signal in self.signals.items():
            if now + 1e-6 < signal["until"]:
                continue
            if signal["stage"] == "yellow":
                if ALL_RED_S > 0:
                    api.trafficlight.setRedYellowGreenState(tid, "r" * len(signal["state"]))
                    signal.update(stage="red", until=now + ALL_RED_S)
                else:
                    self.activate_target(tid, signal, now)
                continue
            if signal["stage"] == "red":
                self.activate_target(tid, signal, now)
                continue
            scores, demand, extensions = {}, {}, {}
            for state in signal["greens"]:
                score = requested = 0
                movement_scores = []
                for (up, down), movement in signal["movements"].items():
                    if not any(state[i] in "Gg" for i in movement["links"]):
                        continue
                    active_lanes = served_lanes(movement, state)
                    upstream = [v for v in movements[(up, down)] if v[1] in active_lanes]
                    downstream = edge_vehicles[down]
                    count = len(upstream)
                    requested += count
                    if self.method == "switching_loss_mp":
                        upstream = [vehicle for vehicle in upstream if vehicle[3] < 0.1]
                        count = len(upstream)
                    active_movement = dict(
                        movement, lanes=active_lanes, out_lanes=served_out_lanes(movement, state)
                    )
                    pressure = self.paper_score(
                        tid, state, up, down, active_movement, upstream, downstream, now
                    )
                    saturation = (
                        1 if self.method == "queue_responsive_2026" else len(active_lanes) / 2
                    )
                    movement_scores.append(pressure * saturation)
                    score += pressure * saturation
                if self.method == "switching_loss_mp":
                    score = max(movement_scores, default=0)  # Sun et al. Eq.5, not phase sum.
                scores[state], demand[state] = score, requested
            self.decisions += 1
            best = max(signal["greens"], key=lambda s: (scores[s], s == signal["state"]))
            if getattr(self, "paper_algorithm", False):
                paper_best = self.paper_phase(tid, signal, now, scores, demand, extensions)
                if paper_best is not None:
                    best = paper_best
            if (
                self.method == "switching_loss_mp"
                and (1 + SWITCH_PROTECTION_K) * scores[signal["state"]] >= scores[best]
            ):
                best = signal["state"]  # Eq.7: protect current phase against marginal gains.
            if best != signal["state"]:
                yellow = yellow_transition(signal["state"], best)
                api.trafficlight.setRedYellowGreenState(tid, yellow)
                target_duration = extensions.get(best, self.interval)
                if getattr(self, "fixed_decision_grid", False):
                    target_duration = self.interval - YELLOW_S - ALL_RED_S
                    if target_duration <= 0:
                        raise ValueError("Decision interval must exceed the transition clearance")
                signal.update(
                    stage="yellow",
                    target=best,
                    until=now + YELLOW_S,
                    target_duration=target_duration,
                )
                self.switches += 1
            else:
                signal["last"][best] = now
                signal["until"] = now + extensions.get(best, self.interval)
