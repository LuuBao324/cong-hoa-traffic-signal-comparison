"""Nonlearning controllers with complete scoring rules and explicit network adapters.

Formula provenance, source ambiguities and scenario parameters:
docs/PURE_NONRL_AUDIT.md. No learned policy, person occupancy, or invented
replacement for a missing estimator is used here.
"""

from collections import defaultdict
import math
import hashlib
import traci.constants as tc
from .research_controllers import ResearchController, clamp
from .pressure_controllers import served_lanes, served_out_lanes, YELLOW_S, ALL_RED_S


def normalized_pressure(model, weight, lanes, saturation):
    """Zoabi/Haddad ECC2024 Eq.6/7. Return a movement's pressure contribution."""
    if lanes <= 0:
        raise ValueError("Movement must have at least one lane")
    divisor = lanes if model in ("cn_mp_2024", "wstar_cn_mp_2024") else lanes * lanes
    return weight * saturation / divisor


def group_c_mp(up_count, up_speed, up_free_speed, downstream_groups):
    """Ahmed Eq.6: apply each downstream movement's own SMS before summing."""
    upstream = up_count * (1 + min(1, up_speed / up_free_speed))
    downstream = sum(
        ratio * count * (1 - min(1, speed / free))
        for ratio, count, speed, free in downstream_groups
    )
    return upstream - downstream


def queue_responsive_targets(scores, budget):
    """Algorithm1 lines14–15: proportional raw green, then independent clamps.

    Do not replace this with bounded water filling: that changes the controller.
    The sum after clamping is not guaranteed to equal the requested budget.
    """
    total = sum(scores)
    return [clamp(budget * s / total, 15, 60) if total > 0 else 20 for s in scores]


def auction_bid(budget, remaining_signals):
    return budget / max(1, remaining_signals)


def auction_scores(local, nonconnected, propagated, last_green, now, starvation_s, bonus):
    """Paper Algorithm3, with starvation inequality as stated in its prose.

    Algorithm3 line10 prints '<'; Section3 describes a lane waiting *longer*
    than the threshold. Use >=, and disclose this source inconsistency.
    """
    scores = {}
    for lane in set(local) | set(nonconnected) | set(propagated):
        bids = local.get(lane, [])
        default = sum(bids) / len(bids) if bids else 0
        scores[lane] = (
            sum(bids) + default * nonconnected.get(lane, 0) + sum(propagated.get(lane, []))
        )
        if now - last_green.get(lane, 0) >= starvation_s:
            scores[lane] += bonus
    return scores


class PureController(ResearchController):
    use_fairness_wrapper = False  # Do not override the paper's phase choice.

    def __init__(self, api, net, method):
        super().__init__(api, net, method)
        self.fixed_decision_grid = method not in ("switching_loss_mp", "queue_responsive_2026")
        self.qr_next_review = 120
        self.phase_updates = 0
        self.budgets = {}
        self.last_approach = {}
        self.current_bids = {}
        self.server = {}
        self.auction_last_green = defaultdict(float)
        self.route_signals = {}
        self.lane_to_tid = {}
        for tid, signal in self.signals.items():
            for pair, movement in signal["movements"].items():
                for lane in movement["lanes"]:
                    self.lane_to_tid[lane] = tid
        self.diagnostics.update(
            protocol="pure_nonrl_v1",
            use_fairness_wrapper=False,
            model_variant=method,
            paper_phase_decisions=0,
            decision_interval_s=self.interval,
            fixed_decision_grid=self.fixed_decision_grid,
            c_mp_alpha=1.0 if method == "c_mp" else None,
            c_mp_beta=1.0 if method == "c_mp" else None,
        )
        if method == "coordinated_auction_2024":
            self.diagnostics.update(
                connected_penetration=1.0,
                propagation_hops=5,
                initial_budget="deterministic uniform integers 1..100",
                eta_threshold_s=10,
                starvation_s=120,
                source_typo="Algorithm3 line10 inequality corrected to match Section3 prose",
            )

    def downstream_groups(self, down):
        groups = defaultdict(list)
        for (up, nxt), vehicles in self.move_data.items():
            if up == down and vehicles:
                groups[nxt] = vehicles
        return groups

    def paper_score(self, tid, state, up, down, movement, upstream, downstream, now):
        n = len(movement["lanes"])
        if self.method == "c_mp":
            groups = self.downstream_groups(down)
            total = sum(len(vs) for vs in groups.values())
            return group_c_mp(
                len(upstream),
                sum(v[3] for v in upstream) / max(1, len(upstream)),
                self.net.getEdge(up).getSpeed(),
                (
                    [
                        (
                            len(vs) / total,
                            len(vs),
                            sum(v[3] for v in vs) / len(vs),
                            self.net.getEdge(down).getSpeed(),
                        )
                        for vs in groups.values()
                    ]
                    if total
                    else []
                ),
            )
        if self.method == "switching_loss_mp":
            # Upstream is already restricted to stopped vehicles by the base collector.
            return len(upstream) - self.downstream_weight(down, lambda v: float(v[3] < 0.1))
        if self.method in ("cn_mp_2024", "wncn_mp_2024", "wstar_ncn_mp_2024", "wstar_cn_mp_2024"):
            # x_lm in the store-and-forward model includes all vehicles on that movement.
            if self.method in ("wstar_ncn_mp_2024", "wstar_cn_mp_2024"):
                capacity = sum(self.net.getLane(l).getLength() / 6 for l in movement["lanes"])
                upstream_metric = len(upstream) / max(1e-9, capacity / n)
                groups = self.downstream_groups(down)
                total = sum(len(vs) for vs in groups.values())
                downstream_metric = 0
                for nxt, vs in groups.items():
                    lanes = {
                        c.getFromLane().getID()
                        for c in self.net.getEdge(down).getOutgoing().get(self.net.getEdge(nxt), [])
                    }
                    cap = sum(self.net.getLane(l).getLength() / 6 for l in lanes)
                    if lanes and total:
                        downstream_metric += len(vs) / total * len(vs) / max(1e-9, cap / len(lanes))
                weight = upstream_metric - downstream_metric
            else:
                weight = len(upstream) - self.downstream_weight(down, lambda v: 1)
            # Base multiplies by saturation afterwards; divide only by the paper's n terms here.
            return weight / (n if self.method in ("cn_mp_2024", "wstar_cn_mp_2024") else n * n)
        if self.method == "coordinated_auction_2024":
            return 0  # Lane auction, not a pressure phase sum; selection is in paper_phase.
        value = super().paper_score(tid, state, up, down, movement, upstream, downstream, now)
        if self.method in ("td_mp_2023", "cv_mp_2025"):
            current = self.signals[tid]["state"]
            served = any(current[i] in "Gg" for i in movement["links"])
            if not served:
                lost_time = YELLOW_S + ALL_RED_S
                # Preserve the distinct loss factors printed in the two sources.
                if self.method == "td_mp_2023":
                    value *= 1 - (self.interval - lost_time) / self.interval
                else:
                    value *= (self.interval - lost_time) / self.interval
        return value

    def observe(self, now, vehicles, edges, movements):
        super().observe(now, vehicles, edges, movements)
        if self.method == "queue_responsive_2026" and now >= self.qr_next_review:
            for tid, signal in self.signals.items():
                metrics = [self.phase_metrics(signal, s) for s in signal["greens"]]
                scores = [
                    0.35 * m["queue"] / max(1, m["lanes"])
                    + 0.35 * m["wait"]
                    + 0.30 / max(m["speed"], 0.1)
                    for m in metrics
                ]
                proposed = queue_responsive_targets(scores, clamp(sum(scores), 80, 160))
                for state, target in zip(signal["greens"], proposed):
                    self.smooth[(tid, state)].append(target)
                    averaged = sum(self.smooth[(tid, state)]) / len(self.smooth[(tid, state)])
                    self.plans[tid][state] += clamp(averaged - self.plans[tid][state], -5, 5)
                self.phase_updates += 1
            self.qr_next_review += 120
            self.diagnostics["cycle_plan_updates"] = self.phase_updates
        if self.method == "coordinated_auction_2024":
            self.observe_auction(now, vehicles, movements)

    def signal_path(self, vid, route_index):
        route = self.routes.get(vid, ())
        key = tuple(route)
        if key not in self.route_signals:
            path = []
            for index, (up, down) in enumerate(zip(route, route[1:])):
                for tid, movement in self.incoming.get((up, down), []):
                    path.append((index, tid, up, down, tuple(sorted(movement["lanes"]))))
            self.route_signals[key] = path
        return [p for p in self.route_signals[key] if p[0] >= route_index]

    def observe_auction(self, now, vehicles, movements):
        # Central server records are refreshed by vehicle/target, never appended
        # repeatedly for the same message. Remove messages when a vehicle reaches
        # the target or leaves the simulation.
        self.current_bids = {}
        for signal in self.signals.values():
            if signal["stage"] == "green":
                for movement in signal["movements"].values():
                    for lane in served_lanes(movement, signal["state"]):
                        self.auction_last_green[lane] = now
        present = set(vehicles)
        for key in list(self.server):
            vid, target_index = key
            if vid not in present or vehicles[vid].get(tc.VAR_ROUTE_INDEX, 0) >= target_index:
                del self.server[key]
        for vid, values in vehicles.items():
            road = values.get(tc.VAR_ROAD_ID, "")
            lane = values.get(tc.VAR_LANE_ID, "")
            idx = values.get(tc.VAR_ROUTE_INDEX, 0)
            previous = self.last_approach.get(vid)
            if previous and previous[0] != road:
                self.budgets[vid] = max(0, self.budgets.get(vid, 100) - previous[1])
                self.last_approach.pop(vid, None)
            if lane not in self.lane_to_tid:
                continue
            path = self.signal_path(vid, idx)
            if not path or path[0][0] != idx:
                continue
            fraction = int(hashlib.sha256(vid.encode()).hexdigest()[:8], 16) / 2**32
            budget = self.budgets.setdefault(vid, float(1 + int(100 * fraction)))
            bid = auction_bid(budget, len(path))
            self.current_bids[vid] = (lane, bid)
            self.last_approach[vid] = (road, bid)
            distance = max(
                0, self.net.getEdge(road).getLength() - values.get(tc.VAR_LANEPOSITION, 0)
            )
            elapsed = distance / self.net.getEdge(road).getSpeed()
            # Algorithm1 uses half bid at the first downstream signal (p=1).
            for hop, entry in enumerate(path[1:6], 1):
                prior_index = path[hop - 1][0]
                for edge_id in self.routes[vid][prior_index + 1 : entry[0] + 1]:
                    edge = self.net.getEdge(edge_id)
                    elapsed += edge.getLength() / edge.getSpeed()
                _, tid, _, _, lanes = entry
                self.server[(vid, entry[0])] = (tid, lanes, bid * 0.5**hop, now + elapsed)
        for vid in set(self.last_approach) - present:
            self.last_approach.pop(vid, None)
            self.budgets.pop(vid, None)

    def paper_phase(self, tid, signal, now, scores, demand, extensions):
        self.diagnostics["paper_phase_decisions"] += 1
        if self.method == "switching_loss_mp":
            for state in signal["greens"]:
                incoming = set()
                outgoing = set()
                for (up, down), movement in signal["movements"].items():
                    if any(state[i] in "Gg" for i in movement["links"]):
                        incoming.update(served_lanes(movement, state))
                        outgoing.update(served_out_lanes(movement, state))
                queued = lambda lane: sum(
                    v[1] == lane and v[3] < 0.1
                    for v in self.edge_data.get(self.net.getLane(lane).getEdge().getID(), [])
                )
                clear = max((queued(lane) / 0.5 + 2 for lane in incoming), default=1)
                space = min(
                    (
                        (self.net.getLane(lane).getLength() / 6 - queued(lane)) / 0.5
                        for lane in outgoing
                    ),
                    default=1,
                )
                extensions[state] = clamp(min(clear, space), 1, 60)
            return None
        if self.method == "queue_responsive_2026":
            extensions.update(self.plans[tid])
            states = signal["greens"]
            return states[(states.index(signal["state"]) + 1) % len(states)]
        if self.method == "coordinated_auction_2024":
            lanes = {lane for m in signal["movements"].values() for lane in m["lanes"]}
            local = {lane: [] for lane in lanes}
            for lane, bid in self.current_bids.values():
                if lane in lanes:
                    local[lane].append(bid)
            propagated = defaultdict(list)
            for dtid, target_lanes, bid, eta in self.server.values():
                if dtid == tid and eta - now <= 10:
                    # A future lane is not known before route following selects it.
                    # Assign once to a feasible lane, not once per possible lane.
                    lane = next((l for l in target_lanes if l in lanes), None)
                    if lane:
                        propagated[lane].append(bid)
            capacity = max((self.net.getLane(l).getLength() / 6 for l in lanes), default=1)
            bonus = max(30000, math.ceil(capacity) * 100 * max(1, len(lanes)) + 1)
            bids = auction_scores(local, {}, propagated, self.auction_last_green, now, 120, bonus)
            active = [l for l in lanes if local[l] or propagated[l]]
            if not active:
                return signal["state"]
            winner = max(sorted(active), key=lambda lane: bids[lane])
            states = [
                s
                for s in signal["greens"]
                if any(winner in served_lanes(m, s) for m in signal["movements"].values())
            ]

            # Preserve the lane auction winner, then serve its actual turning
            # intentions using one of the existing compatible SUMO phases.
            def winner_service(state):
                total = 0
                for (up, down), movement in signal["movements"].items():
                    if winner not in served_lanes(movement, state):
                        continue
                    for v in self.move_data.get((up, down), []):
                        if v[1] == winner and v[0] in self.current_bids:
                            total += self.current_bids[v[0]][1]
                return total

            chosen = max(states, key=lambda s: (winner_service(s), s == signal["state"]))
            self.auction_last_green[winner] = now
            self.diagnostics["propagated_messages"] = len(self.server)
            return chosen
        return super().paper_phase(tid, signal, now, scores, demand, extensions)
