import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
import tempfile
import json
from unittest.mock import Mock, patch

from traffic_study import run_fixed_time as baseline
from traffic_study.boundary_demand import BoundaryDemand
from traffic_study.vehicle_types import allows_vehicle
from traffic_study.fixed_time_signals import (
    SignalNetwork,
    parallel_carriageway_crossovers,
    roundabout_exit_connections,
    carriageway_split_connections,
    carriageway_merge_connections,
    crossing_roundabout_exits,
    redundant_lane_fans,
    build_programmes,
    two_stage_phases,
)


class FixedTimeLaneMergeTests(unittest.TestCase):
    def test_c12_merge_keeps_three_main_lanes_separate(self):
        raw = ET.fromstring(
            '<net><edge id="197804068#3"><lane/><lane/></edge>'
            '<edge id="1511909557"><lane/><lane/><lane/></edge>'
            '<connection from="197804068#3" to="1511909557" fromLane="0" toLane="1"/>'
            '<connection from="197804068#3" to="1511909557" fromLane="1" toLane="2"/>'
            '<connection from="1511909548" to="1511909557" fromLane="0" toLane="2"/></net>'
        )
        removals, additions = carriageway_merge_connections(raw)
        self.assertEqual(len(removals), 2)
        self.assertEqual([(c["fromLane"], c["toLane"]) for c in additions], [("0", "0"), ("1", "1")])
        for c in removals:
            raw.remove(c)
        for c in additions:
            ET.SubElement(raw, "connection", c)
        self.assertEqual(carriageway_merge_connections(raw), ([], []))
        self.assertIsNotNone(raw.find("connection[@from='1511909548'][@toLane='2']"))

    def test_roundabout_survey_serves_the_cong_hoa_entry(self):
        raw = ET.Element("net")
        node = ET.SubElement(raw, "junction", id="j", intLanes=":j_0_0 :j_1_0 :j_2_0 :j_3_0")
        ET.SubElement(raw, "edge", id="exit")
        for index in range(4):
            name = "Vòng xoay Lăng Cha Cả" if index < 2 else "Cộng Hòa"
            ET.SubElement(raw, "edge", id=f"in{index}", name=name, to="j")
            ET.SubElement(node, "request", index=str(index), foes="0000")
            ET.SubElement(raw, "connection", attrib={
                "from": f"in{index}", "to": "exit", "fromLane": "0",
                "toLane": str(index % 2), "via": f":j_{index}_0",
                "tl": "survey_CH_HVT_ENTRY", "linkIndex": str(index), "dir": "s",
            })
        ET.SubElement(raw, "tlLogic", id="survey_CH_HVT_ENTRY", offset="0")
        lights, _ = build_programmes(
            raw, baseline.BASE / "signals/survey_observations.csv", None, "unused"
        )
        phases = lights.find("tlLogic").findall("phase")
        self.assertEqual(phases[0].get("duration"), "32")
        self.assertEqual(phases[0].get("state"), "rrGG")
        self.assertEqual(phases[2].get("state"), "GGrr")

    def test_each_input_lane_has_one_continuation_per_road(self):
        raw = ET.fromstring(
            '<net><edge id="a"><lane/><lane/><lane/></edge>'
            '<edge id="b"><lane/><lane/><lane/><lane/></edge>'
            '<connection from="a" to="b" fromLane="2" toLane="2" dir="s"/>'
            '<connection from="a" to="b" fromLane="2" toLane="3" dir="s"/></net>'
        )
        removals = redundant_lane_fans(raw)
        self.assertEqual([c.get("toLane") for c in removals], ["3"])

    def test_lane_fan_preserves_different_vehicle_permissions(self):
        raw = ET.fromstring(
            '<net><edge id="a"><lane/></edge>'
            '<edge id="b"><lane allow="motorcycle"/><lane allow="passenger"/></edge>'
            '<connection from="a" to="b" fromLane="0" toLane="0" dir="s"/>'
            '<connection from="a" to="b" fromLane="0" toLane="1" dir="s"/></net>'
        )
        self.assertEqual(redundant_lane_fans(raw), [])
    def road(self, name, width, length=10, lane_count=1):
        lanes = []
        for index in range(lane_count):
            lane = Mock()
            lane.getIndex.return_value = index
            lane.getWidth.return_value = width
            lane.allows.return_value = True
            lanes.append(lane)
        edge = Mock()
        edge.getID.return_value = name
        edge.getLanes.return_value = lanes
        edge.getLength.return_value = length
        edge.getSpeed.return_value = 10
        return edge

    def link(self, source, target, from_lane=0, to_lane=0):
        connection = Mock()
        connection.getDirection.return_value = "s"
        connection.getFromLane.return_value = source.getLanes()[from_lane]
        connection.getToLane.return_value = target.getLanes()[to_lane]
        return connection

    def test_road_width_uses_actual_vehicle_dimensions(self):
        narrow = self.road("narrow", 1.6)
        self.assertTrue(allows_vehicle(narrow, "motorcycle"))
        self.assertFalse(allows_vehicle(narrow, "passenger"))
        self.assertFalse(allows_vehicle(narrow, "bus"))
        narrow.getLanes()[0].allows.return_value = False
        self.assertFalse(allows_vehicle(narrow, "motorcycle"))

    def test_lane_based_car_cannot_combine_two_narrow_lanes(self):
        narrow = self.road("narrow", 1.6)
        narrow.getLanes.return_value = [narrow.getLanes()[0], narrow.getLanes()[0]]
        self.assertFalse(allows_vehicle(narrow, "passenger"))

    def test_routing_avoids_roads_too_narrow_for_the_vehicle(self):
        start, finish = self.road("start", 3.2), self.road("finish", 3.2)
        narrow, wide = self.road("narrow", 1.6, 1), self.road("wide", 3.2, 100)
        start.getAllowedOutgoing.return_value = {narrow: [self.link(start, narrow)], wide: [self.link(start, wide)]}
        narrow.getAllowedOutgoing.return_value = {finish: [self.link(narrow, finish)]}
        wide.getAllowedOutgoing.return_value = {finish: [self.link(wide, finish)]}
        edges = {e.getID(): e for e in [start, finish, narrow, wide]}
        builder = object.__new__(BoundaryDemand)
        builder.net = Mock()
        builder.net.getEdge.side_effect = edges.__getitem__
        builder.path_cache, builder.outgoing_cache = {}, {}
        self.assertEqual(builder.path(start, finish, "passenger"), ("start", "wide", "finish"))
        self.assertEqual(builder.path(start, finish, "motorcycle"), ("start", "narrow", "finish"))

    def test_route_uses_outer_approach_for_a_turn_after_a_short_merge(self):
        start = self.road("start", 3.2, 100)
        centre = self.road("centre", 3.2, 10)
        outer = self.road("outer", 3.2, 100, lane_count=2)
        merge = self.road("merge", 3.2, 20, lane_count=3)
        turn = self.road("turn", 3.2, 100)
        finish = self.road("finish", 3.2, 100)
        start.getAllowedOutgoing.return_value = {centre: [self.link(start, centre)], outer: [self.link(start, outer)]}
        centre.getAllowedOutgoing.return_value = {merge: [self.link(centre, merge, 0, 2)]}
        outer.getAllowedOutgoing.return_value = {merge: [self.link(outer, merge, 0, 0), self.link(outer, merge, 1, 1)]}
        merge.getAllowedOutgoing.return_value = {turn: [self.link(merge, turn)]}
        turn.getAllowedOutgoing.return_value = {finish: [self.link(turn, finish)]}
        edges = {e.getID(): e for e in [start, centre, outer, merge, turn, finish]}
        builder = object.__new__(BoundaryDemand)
        builder.net = Mock()
        builder.net.getEdge.side_effect = edges.__getitem__
        builder.path_cache, builder.outgoing_cache = {}, {}
        good = ("start", "outer", "merge", "turn", "finish")
        self.assertEqual(builder.path(start, finish, "passenger"), good)
        self.assertTrue(builder.route_lane_feasible(good, "passenger"))
        self.assertFalse(builder.route_lane_feasible(("centre", "merge", "turn"), "passenger"))
        self.assertEqual(builder.path(start, merge, "passenger"), ("start", "centre", "merge"))
        self.assertEqual(builder.path(start, merge, "passenger", arrival_lanes={0}), ("start", "outer", "merge"))
        self.assertEqual(builder.path(merge, finish, "passenger", initial_lanes={2}), ())
        self.assertEqual(builder.path(merge, finish, "passenger", initial_lanes={0}), ("merge", "turn", "finish"))
        self.assertEqual(builder.reachable_lanes(("merge", "turn"), "passenger", {1}), {0})

    def test_preview_reallocates_the_previous_total_demand(self):
        background = sum(baseline.NETWORK_BACKGROUND_PER_HOUR.values())
        self.assertEqual(baseline.DIRECT_CORRIDOR_SHARE, 0)
        self.assertAlmostEqual(
            background,
            baseline.REFERENCE_TOTAL_DEMAND_VPH * baseline.DEMAND_SCALE,
            delta=10,
        )
        self.assertEqual(baseline.REFERENCE_COUNT_10_MIN, 12000)

    def test_corridor_route_file_contains_only_tracked_vehicles(self):
        with tempfile.TemporaryDirectory(dir=baseline.ROOT) as folder:
            with (
                patch.object(baseline, "OUT", Path(folder)),
                patch.object(baseline, "find_route", return_value=["a", "b"]),
                patch.object(baseline, "find_center_route", return_value=["a", "c", "b"]),
            ):
                _, _, ordinary_count = baseline.create_traffic(None, None, None, None, None, [], [])
            root = ET.parse(Path(folder) / "traffic.rou.xml").getroot()
            self.assertEqual({v.get("id") for v in root.findall("vehicle")}, set(baseline.PROBES))
            self.assertEqual(ordinary_count, 0)

    def test_requested_corridor_journeys_include_side_entries_and_other_map_routes(self):
        edges = {}
        for edge_id in ("entry", "ch", "other", "exit", "side", "cross", "airport"):
            edge = Mock()
            edge.getID.return_value = edge_id
            edge.getName.return_value = "Cộng Hòa" if edge_id == "ch" else edge_id
            lane = Mock()
            lane.getIndex.return_value = 0
            lane.getWidth.return_value = 3.2
            lane.allows.return_value = True
            edge.getLanes.return_value = [lane]
            edge.getToNode.return_value.getID.return_value = "j"
            edges[edge_id] = edge
        edges["ch"].getAllowedOutgoing.return_value = {edges["exit"]: [self.link(edges["ch"], edges["exit"])]}
        net = Mock()
        net.getNodes.return_value = []
        net.getEdge.side_effect = edges.__getitem__
        builder = Mock()
        builder.background_pool.return_value = [("entry", "ch", "exit"), ("entry", "other", "exit")]
        builder.partial_corridor_pool.return_value = []
        builder.departure_pools.return_value = {
            "boundary": builder.background_pool.return_value,
            "interior": [("ch", "exit"), ("other", "exit")],
        }
        builder.side_approach_pool.return_value = [
            dict(incoming_edge="side", junction="j", road="side", edges=path)
            for path in [("side", "ch", "exit"), ("side", "cross", "exit")]
        ]
        builder.airport_pool.return_value = [("airport", "ch", "exit")]
        builder.origins, builder.destinations = [edges["entry"]], [edges["exit"]]
        builder.covered_edges = set(edges)
        with tempfile.TemporaryDirectory(dir=baseline.ROOT) as folder:
            with (
                patch.object(baseline, "OUT", Path(folder)),
                patch.object(baseline, "NETWORK_BACKGROUND_PER_HOUR", {"motorcycle": 270}),
                patch.object(baseline, "DEMAND_DURATION_S", 3600),
                patch("traffic_study.boundary_demand.get_demand_builder", return_value=builder),
            ):
                baseline.create_network_background(net)
            root = ET.parse(Path(folder) / "map_motorcycle.rou.xml").getroot()
            paths = {r.get("id"): r.get("edges").split() for r in root.findall("route")}
            vehicles = root.findall("vehicle")
            self.assertEqual(len(vehicles), 270)
            self.assertEqual(sum("ch" in paths[v.get("route")] for v in vehicles), 144)
            self.assertTrue(all(paths[v.get("route")][-1] == "exit" for v in vehicles))
            self.assertTrue(any(paths[v.get("route")][:2] == ["side", "ch"] for v in vehicles))
            self.assertTrue(any("ch" not in paths[v.get("route")] for v in vehicles))
            counts = json.loads((Path(folder) / "network_demand.json").read_text())
            self.assertEqual(counts["corridor_related_generated_vehicles"]["motorcycle"], 144)

    def test_competing_merges_both_receive_protected_service(self):
        raw = ET.fromstring(
            '<net><edge id="a" to="j"/><edge id="b" to="j"/>'
            '<edge id="exit"/><junction id="j" intLanes=":j_0_0 :j_1_0">'
            '<request index="0" foes="10"/><request index="1" foes="01"/>'
            '</junction><connection from="a" to="exit" fromLane="0" toLane="0" '
            'via=":j_0_0" tl="j" linkIndex="0" dir="s"/>'
            '<connection from="b" to="exit" fromLane="0" toLane="0" '
            'via=":j_1_0" tl="j" linkIndex="1" dir="s"/></net>'
        )
        network = SignalNetwork(raw)
        states = network.protected_states(network.connections["j"], {0, 1})
        self.assertEqual(states, ["Gr", "rG"])

    def test_clearance_wraps_across_three_stages(self):
        phases = two_stage_phases(["Grr", "rGr", "rrG"], [10, 10, 10])
        self.assertEqual(
            phases,
            [(10, "Grr"), (3, "yrr"), (10, "rGr"), (3, "ryr"), (10, "rrG"), (3, "rry")],
        )

    def test_roundabout_inner_lane_can_reach_existing_exit(self):
        raw = ET.fromstring(
            '<net><edge id="ring" name="Vòng xoay Lăng Cha Cả">'
            '<lane index="0"/><lane index="1"/></edge>'
            '<edge id="exit" name="Cộng Hòa">'
            '<lane index="0"/><lane index="1"/><lane index="2"/></edge>'
            '<connection from="ring" to="exit" fromLane="0" toLane="0"/></net>'
        )
        additions = roundabout_exit_connections(raw)
        self.assertEqual(roundabout_exit_connections(raw), [])

    def test_roundabout_connections_use_network_membership(self):
        raw = ET.fromstring(
            '<net><roundabout edges="ring next"/>'
            '<edge id="ring" name="Another roundabout"><lane/><lane/></edge>'
            '<edge id="next" name="Another roundabout"><lane/><lane/></edge>'
            '<edge id="exit" name="Side road"><lane/><lane/></edge>'
            '<connection from="ring" to="next" fromLane="1" toLane="1"/>'
            '<connection from="ring" to="exit" fromLane="0" toLane="0"/></net>'
        )
        additions = roundabout_exit_connections(raw)
        self.assertIn({"from": "ring", "to": "next", "fromLane": "0", "toLane": "0"}, additions)
        self.assertNotIn({"from": "ring", "to": "exit", "fromLane": "1", "toLane": "1"}, additions)

    def test_inner_exit_cannot_cross_parallel_ring_traffic(self):
        raw = ET.fromstring(
            '<net><roundabout edges="ring next"/>'
            '<connection from="ring" to="next" fromLane="0" toLane="0" dir="s"/>'
            '<connection from="ring" to="exit" fromLane="0" toLane="0" dir="r"/>'
            '<connection from="ring" to="exit" fromLane="1" toLane="1" dir="r"/></net>'
        )
        removed = crossing_roundabout_exits(raw)
        self.assertEqual([c.get("fromLane") for c in removed], ["1"])

    def test_bridge_split_connections_are_added_once(self):
        raw = ET.fromstring(
            '<net><edge id="1511909556"/><edge id="1511909552"/>'
            '<edge id="1424752054#0"/></net>'
        )
        additions = carriageway_split_connections(raw)
        self.assertEqual(len(additions), 2)
        for connection in additions:
            ET.SubElement(raw, "connection", connection)
        self.assertEqual(carriageway_split_connections(raw), [])

    def test_parallel_carriageways_keep_their_own_continuations(self):
        raw = ET.Element("net")
        for edge_id in ["centre#0", "centre#1", "outer_in", "outer_out"]:
            ET.SubElement(raw, "edge", id=edge_id, name="Cộng Hòa", to="junction")
        for approach, target in [
            ("centre#0", "centre#1"),
            ("centre#0", "outer_out"),
            ("outer_in", "outer_out"),
            ("outer_in", "centre#1"),
        ]:
            ET.SubElement(raw, "connection", attrib={"from": approach, "to": target, "dir": "s"})
        removed = parallel_carriageway_crossovers(raw, {"centre"})
        self.assertEqual(
            {(c.get("from"), c.get("to")) for c in removed},
            {("centre#0", "outer_out"), ("outer_in", "centre#1")},
        )

    def test_bridge_entry_with_no_parallel_approach_is_preserved(self):
        raw = ET.fromstring(
            '<net><edge id="outer" name="Cộng Hòa" to="junction"/>'
            '<edge id="centre" name="Cộng Hòa" to="downstream"/>'
            '<connection from="outer" to="centre" dir="s"/></net>'
        )
        self.assertEqual(parallel_carriageway_crossovers(raw, {"centre"}), [])

    def test_vehicle_types_use_lane_based_movement(self):
        routes = ET.Element("routes")
        baseline.create_vehicle_types(routes)
        self.assertEqual(len(routes.findall("vType")), 4)
        for vehicle in routes.findall("vType"):
            self.assertEqual(vehicle.get("laneChangeModel"), "LC2013")
            self.assertEqual(vehicle.get("carFollowModel"), "Krauss")
            self.assertEqual(vehicle.get("tau"), "1.0")
            self.assertIsNone(vehicle.get("lcSublane"))
            self.assertGreater(float(vehicle.get("lcSpeedGain")), 0)

    def test_configuration_uses_single_file_lanes(self):
        with tempfile.TemporaryDirectory(dir=baseline.ROOT) as folder:
            with patch.object(baseline, "OUT", Path(folder)):
                baseline.create_configuration()
            configuration = ET.parse(Path(folder) / "fixed_time.sumocfg")
            self.assertIsNone(configuration.getroot().find("processing/lateral-resolution"))
            self.assertEqual(configuration.getroot().find("time/step-length").get("value"), "0.25")
            self.assertEqual(
                configuration.getroot().find("processing/collision.mingap-factor").get("value"), "0"
            )
            self.assertEqual(
                configuration.getroot().find("processing/collision.check-junctions").get("value"), "true"
            )

    def test_internal_lane_indexes_follow_lane_order(self):
        raw = ET.fromstring(
            '<net><edge id=":j_3" function="internal">'
            '<lane id=":j_3_0" index="0"/>'
            '<lane id=":j_3_1" index="0"/>'
            '<lane id=":j_3_2" index="0"/>'
            "</edge></net>"
        )
        self.assertEqual(baseline.repair_internal_lane_indexes(raw), [":j_3_1", ":j_3_2"])
        self.assertEqual([lane.get("index") for lane in raw.findall("edge/lane")], ["0", "1", "2"])
        self.assertEqual(baseline.repair_internal_lane_indexes(raw), [])

    def test_internal_lane_repair_rejects_ambiguous_lane_ids(self):
        raw = ET.fromstring(
            '<net><edge id=":j_3" function="internal">' '<lane id=":j_3_2" index="0"/></edge></net>'
        )
        with self.assertRaises(ValueError):
            baseline.repair_internal_lane_indexes(raw)

    def test_atomic_xml_failure_preserves_previous_file(self):
        with tempfile.TemporaryDirectory(dir=baseline.ROOT) as folder:
            root = Path(folder)
            self.assertTrue(root.resolve().is_relative_to(baseline.ROOT.resolve()))
            path = root / "routes.xml"
            path.write_text("<routes/>", encoding="utf-8")
            with patch.object(ET.ElementTree, "write", side_effect=OSError("interrupted write")):
                with self.assertRaises(OSError):
                    baseline.write_xml(path, ET.Element("routes"))
            self.assertEqual(path.read_text(encoding="utf-8"), "<routes/>")
            self.assertEqual(list(root.iterdir()), [path])

    def make_network(self, direction):
        raw = ET.Element("net")
        for node_id, x in [("upstream", 0), (baseline.TLS_18E, 10), ("downstream", 20)]:
            node = ET.SubElement(raw, "junction", id=node_id, x=str(x), y="0")
            if node_id == baseline.TLS_18E:
                ET.SubElement(node, "request", index="0", foes="00")
                ET.SubElement(node, "request", index="1", foes="00")
        ET.SubElement(
            raw,
            "edge",
            id="-1523207559",
            name="Cộng Hòa",
            attrib={"from": "upstream", "to": baseline.TLS_18E},
        )
        ET.SubElement(
            raw,
            "edge",
            id=baseline.SIDE_18E_EDGE,
            name="Đường 18E",
            attrib={"from": "upstream", "to": baseline.TLS_18E},
        )
        ET.SubElement(
            raw,
            "edge",
            id="outer_exit",
            name="Cộng Hòa",
            attrib={"from": baseline.TLS_18E, "to": "downstream"},
        )
        for index, (edge_id, turn) in enumerate(
            [("-1523207559", direction), (baseline.SIDE_18E_EDGE, "r")]
        ):
            ET.SubElement(
                raw,
                "connection",
                attrib={
                    "from": edge_id,
                    "to": "outer_exit",
                    "fromLane": "0",
                    "toLane": "0",
                    "tl": baseline.TLS_18E,
                    "linkIndex": str(index),
                    "dir": turn,
                },
            )
        source = ET.SubElement(raw, "tlLogic", id=baseline.TLS_18E)
        return raw, source

    def test_forward_right_merge_receives_corridor_green(self):
        raw, source = self.make_network("r")
        phases, _ = baseline.build_18e_phases(raw, source)
        self.assertIn(phases[0][1][0], "Gg")
        self.assertEqual(phases[1][1][0], "y")
        self.assertEqual(phases[2][1][0], "r")

    def test_centre_left_turn_remains_rejected(self):
        raw, source = self.make_network("l")
        with self.assertRaises(RuntimeError):
            baseline.build_18e_phases(raw, source)

    def test_reverse_right_connection_is_rejected_before_running(self):
        raw, source = self.make_network("r")
        raw.find("junction[@id='downstream']").set("x", "-20")
        with self.assertRaises(RuntimeError):
            baseline.build_18e_phases(raw, source)


if __name__ == "__main__":
    unittest.main()
