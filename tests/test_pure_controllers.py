"""Numerical checks against paper examples and policy-changing edge cases."""

import unittest
from unittest.mock import Mock
from traffic_study.pure_controllers import (
    normalized_pressure,
    group_c_mp,
    queue_responsive_targets,
    auction_bid,
    auction_scores,
)
from traffic_study.pure_controllers import PureController
from traffic_study.pressure_controllers import served_lanes, served_out_lanes
from traffic_study.research_controllers import ResearchController
import traci.constants as tc
from collections import deque


class PureFormulaTest(unittest.TestCase):
    def test_td_delay_window_and_published_switching_factor(self):
        controller = PureController.__new__(PureController)
        controller.method = "td_mp_2023"
        controller.cyclic = False
        controller.interval = 5
        controller.signals = {"tls": {"state": "rG"}}
        controller.history = {"v": {"delay": 20}}
        controller.move_data = {("down", "out"): [("d", "lane", 0, 0)]}
        controller.window = deque([(1, {("down", "out"): 2})])
        movement = {"lanes": {"in"}, "links": {0}}
        value = controller.paper_score(
            "tls", "Gr", "up", "down", movement, [("v", "in", 0, 0)], [], 5
        )
        self.assertAlmostEqual(value, (20 - 2) * (1 - (5 - 3) / 5))
        controller.signals["tls"]["state"] = "Gr"
        self.assertEqual(
            controller.paper_score("tls", "Gr", "up", "down", movement, [("v", "in", 0, 0)], [], 5),
            18,
        )

    def test_switching_loss_extension_uses_busiest_lane(self):
        controller = PureController.__new__(PureController)
        controller.method = "switching_loss_mp"
        controller.diagnostics = {"paper_phase_decisions": 0}
        controller.edge_data = {
            "up": [("a", "in0", 0, 0), ("b", "in0", 0, 0), ("c", "in0", 0, 0), ("d", "in1", 0, 0)],
            "down": [],
        }

        def lane_info(lane):
            lane_object = Mock()
            lane_object.getLength.return_value = 60
            lane_object.getEdge.return_value.getID.return_value = "down" if lane == "out" else "up"
            return lane_object

        controller.net = Mock()
        controller.net.getLane.side_effect = lane_info
        signal = {
            "greens": ["G"],
            "movements": {
                ("up", "down"): {"links": {0}, "lanes": {"in0", "in1"}, "out_lanes": {"out"}}
            },
        }
        extensions = {}
        controller.paper_phase("tls", signal, 10, {}, {}, extensions)
        self.assertEqual(extensions["G"], 3 / 0.5 + 2)

    def test_cv_pressure_uses_current_network_free_flow_speed(self):
        controller = ResearchController.__new__(ResearchController)
        controller.method = "cv_mp_2025"
        controller.cyclic = False
        controller.history = {"v": {"road": "up", "entered": 0}}
        controller.net = Mock()
        controller.net.getEdge.return_value.getLength.return_value = 100
        controller.net.getEdge.return_value.getSpeed.return_value = 20
        controller.edge_data = {}
        result = controller.paper_score("tls", "G", "up", "down", {}, [("v", "lane", 0, 0)], [], 10)
        self.assertEqual(result, 2)

    def test_cv_applies_its_published_switching_discount(self):
        controller = PureController.__new__(PureController)
        controller.method = "cv_mp_2025"
        controller.cyclic = False
        controller.interval = 10
        controller.signals = {"tls": {"state": "rG"}}
        controller.history = {"v": {"road": "up", "entered": 0}}
        controller.net = Mock()
        controller.net.getEdge.return_value.getLength.return_value = 100
        controller.net.getEdge.return_value.getSpeed.return_value = 20
        controller.edge_data = {}
        movement = {"lanes": {"in"}, "links": {0}}
        value = controller.paper_score(
            "tls", "Gr", "up", "down", movement, [("v", "in", 0, 0)], [], 10
        )
        self.assertAlmostEqual(value, 2 * 0.7)
        controller.signals["tls"]["state"] = "Gr"
        self.assertEqual(
            controller.paper_score(
                "tls", "Gr", "up", "down", movement, [("v", "in", 0, 0)], [], 10
            ),
            2,
        )

    def test_queue_metrics_keep_accumulated_wait_after_moving(self):
        controller = ResearchController.__new__(ResearchController)
        controller.history = {"v": {"waiting_at_entry": 10}}
        controller.vehicle_data = {
            "v": {tc.VAR_WAITING_TIME: 0, tc.VAR_ACCUMULATED_WAITING_TIME: 25}
        }
        controller.move_data = {("up", "down"): [("v", "lane", 10, 1)]}
        controller.net = Mock()
        controller.net.getLane.return_value.getLength.return_value = 100
        signal = {"movements": {("up", "down"): {"links": {0}, "lanes": {"lane"}}}}
        self.assertEqual(controller.phase_metrics(signal, "G")["wait"], 15)

    def test_red_lane_does_not_gain_service_from_another_lane_green(self):
        movement = dict(
            lanes={"lane0", "lane1"}, links={0, 1}, link_lanes={0: {"lane0"}, 1: {"lane1"}}
        )
        self.assertEqual(served_lanes(movement, "Gr"), {"lane0"})
        self.assertEqual(served_lanes(movement, "rG"), {"lane1"})
        self.assertEqual(served_lanes(movement, "yr"), set())
        movement.update(out_lanes={"out0", "out1"}, link_out_lanes={0: {"out0"}, 1: {"out1"}})
        self.assertEqual(served_out_lanes(movement, "Gr"), {"out0"})

    def test_ecc2024_table_one(self):
        # ECC2024 Table I: two-lane and one-lane movements both contain 5 vehicles.
        self.assertEqual(normalized_pressure("cn_mp_2024", 5, 2, 1), 2.5)
        self.assertEqual(normalized_pressure("wncn_mp_2024", 5, 2, 1), 1.25)
        self.assertEqual(normalized_pressure("wncn_mp_2024", 5, 1, 0.5), 2.5)
        # Eq.8 supplies a capacity-aware weight of .5; Eq.6 vs7 remains distinct.
        self.assertEqual(normalized_pressure("wstar_cn_mp_2024", 0.5, 2, 1), 0.25)
        self.assertEqual(normalized_pressure("wstar_ncn_mp_2024", 0.5, 2, 1), 0.125)

    def test_c_mp_distinguishes_downstream_platoons_per_turn(self):
        value = group_c_mp(10, 0, 10, [(0.25, 2, 10, 10), (0.75, 6, 0, 10)])
        self.assertAlmostEqual(value, 5.5)
        # Taking an edge-wide speed before weighting would incorrectly yield 6.25.
        self.assertNotAlmostEqual(value, 6.25)

    def test_c_mp_empty_movement_does_not_create_a_zero_denominator(self):
        controller = PureController.__new__(PureController)
        controller.method = "c_mp"
        controller.net = Mock()
        controller.net.getEdge.return_value.getSpeed.return_value = 10
        controller.move_data = {("down", "a"): [], ("down", "b"): [("v", "lane", 5, 0)]}
        result = controller.paper_score(
            "tls", "G", "up", "down", {"lanes": {"in"}}, [("u", "in", 2, 0)], [], 500
        )
        self.assertEqual(result, 0)

    def test_qr_clamps_individually_not_water_filling(self):
        values = queue_responsive_targets([1000, 0, 0, 0], 100)
        self.assertEqual(values, [60, 15, 15, 15])
        self.assertEqual(sum(values), 105)
        self.assertEqual(queue_responsive_targets([0] * 4, 80), [20] * 4)

    def test_auction_budget_and_default_nonconnected_bid(self):
        self.assertEqual(auction_bid(100, 4), 25)
        values = auction_scores(
            {"a": [10, 20], "b": [20]}, {"a": 2}, {"b": [5]}, {"a": 110, "b": 110}, 120, 120, 1000
        )
        self.assertEqual(values, {"a": 60, "b": 25})

    def test_auction_starvation_matches_prose_not_printed_typo(self):
        values = auction_scores({"a": [1], "b": [100]}, {}, {}, {"a": 0, "b": 119}, 120, 120, 1000)
        self.assertGreater(values["a"], values["b"])


if __name__ == "__main__":
    unittest.main()
