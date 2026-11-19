"""2023+ no-training paper adaptations. Sources and deviations: docs/PAPER_IMPLEMENTATIONS.md."""

from collections import defaultdict, deque
import traci.constants as tc
from .pressure_controllers import PressureController, served_lanes


def clamp(x, lower, upper):
    return max(lower, min(upper, x))


class ResearchController(PressureController):
    paper_algorithm = True

    def __init__(self, api, net, method):
        super().__init__(api, net, method)
        self.cyclic = method == "queue_responsive_2026"
        self.history = {}
        self.edge_data = self.move_data = self.vehicle_data = {}
        self.window = deque()
        self.plans = {}
        self.smooth = defaultdict(lambda: deque(maxlen=5))
        self.diagnostics = dict(
            observation_hz=1, cv_penetration=1.0 if method == "cv_mp_2025" else None
        )
        self.incoming = defaultdict(list)
        for tid, signal in self.signals.items():
            for pair, movement in signal["movements"].items():
                self.incoming[pair].append((tid, movement))
            self.plans[tid] = {s: 20.0 for s in signal["greens"]}
            if self.cyclic:
                signal["until"] = 20
        if method == "td_mp_2023":
            self.interval = 5
            for signal in self.signals.values():
                signal["until"] = 5

    def observe(self, now, vehicles, edges, movements):
        self.edge_data, self.move_data, self.vehicle_data = edges, movements, vehicles
        queues = {pair: sum(v[3] < 0.1 for v in vs) for pair, vs in movements.items()}
        self.window.append((now, queues))
        while self.window and self.window[0][0] <= now - self.interval:
            self.window.popleft()
        present = set()
        for vid, values in vehicles.items():
            road = values.get(tc.VAR_ROAD_ID, "")
            old = self.history.get(vid)
            if old and old["road"] != road:
                self.history.pop(vid, None)
                old = None
            if road.startswith(":") or road not in self.net._id2edge:
                continue
            present.add(vid)
            position = values[tc.VAR_LANEPOSITION]
            if old is None:
                route = self.routes.get(vid, ())
                idx = values[tc.VAR_ROUTE_INDEX]
                old = dict(
                    road=road,
                    entered=now,
                    start_pos=position,
                    delay=0,
                    waiting_at_entry=values.get(tc.VAR_ACCUMULATED_WAITING_TIME, 0),
                    pair=(road, route[idx + 1] if idx + 1 < len(route) else ""),
                )
                self.history[vid] = old
            free_speed = self.net.getEdge(road).getSpeed()
            old["delay"] = max(
                0, now - old["entered"] - max(0, position - old["start_pos"]) / free_speed
            )
        for vid in set(self.history) - present:
            self.history.pop(vid, None)

    def downstream_weight(self, down, value):
        groups = defaultdict(list)
        for v in self.edge_data.get(down, []):
            route = self.routes.get(v[0], ())
            idx = self.vehicle_data[v[0]][tc.VAR_ROUTE_INDEX]
            if idx + 1 < len(route):
                groups[route[idx + 1]].append(v)
        total = sum(len(v) for v in groups.values())
        return (
            sum(len(v) / total * sum(value(x) for x in v) for v in groups.values()) if total else 0
        )

    def paper_score(self, tid, state, up, down, movement, upstream, downstream, now):
        if self.cyclic:
            return sum(v[3] < 0.1 for v in upstream)
        if self.method == "cv_mp_2025":

            def normalized(v):
                h = self.history.get(v[0])
                if not h:
                    return 0
                edge = self.net.getEdge(h["road"])
                return (now - h["entered"]) / (edge.getLength() / edge.getSpeed())

            return sum(normalized(v) for v in upstream) - self.downstream_weight(down, normalized)
        if self.method == "td_mp_2023":
            up_delay = sum(self.history.get(v[0], {}).get("delay", 0) for v in upstream)
            next_counts = defaultdict(int)
            for (road, nxt), vs in self.move_data.items():
                if road == down:
                    next_counts[nxt] = len(vs)
            total = sum(next_counts.values())
            recent = (
                sum(
                    (n / total) * sum(q.get((down, nxt), 0) for _, q in self.window)
                    for nxt, n in next_counts.items()
                )
                if total
                else 0
            )
            return up_delay - recent
        raise ValueError(self.method)

    def phase_metrics(self, signal, state):
        lanes = set()
        outgoing = []
        eligible = {}
        for (up, down), movement in signal["movements"].items():
            if any(state[i] in "Gg" for i in movement["links"]):
                lanes.update(served_lanes(movement, state))
                outgoing.append(down)
                for v in self.move_data.get((up, down), []):
                    if v[1] in served_lanes(movement, state):
                        eligible[v[0]] = v
        vs = list(eligible.values())
        queued = sum(v[3] < 0.1 for v in vs)
        wait = sum(
            max(
                0,
                self.vehicle_data[v[0]].get(tc.VAR_ACCUMULATED_WAITING_TIME, 0)
                - self.history.get(v[0], {}).get("waiting_at_entry", 0),
            )
            for v in vs
        )
        speed = (
            sum(v[3] for v in vs) / len(vs)
            if vs
            else max((self.net.getLane(l).getSpeed() for l in lanes), default=13.89)
        )
        capacity = sum(self.net.getLane(l).getLength() / 6 for l in lanes)
        return dict(
            queue=queued,
            lanes=len(lanes),
            wait=wait,
            mean_wait=wait / max(1, len(vs)),
            speed=speed,
            ratio=queued / max(1, capacity),
            down=outgoing,
        )
