"""Controller invariants independent of the expensive real-network pilot."""

import unittest
from unittest.mock import Mock, patch
from traffic_study.pressure_controllers import PressureController, yellow_transition
from traffic_study import pressure_controllers as module
from traffic_study.compare_pressure import METHODS
from traffic_study.batch_experiments import AVAILABLE
from traffic_study.paper_methods import PAPERS, RESEARCH_METHODS


class PressureMethodsTest(unittest.TestCase):
    def test_transition_preserves_shared_green(self):
        self.assertEqual(yellow_transition("GgGr", "GrrG"), "Gyyr")
        self.assertEqual(yellow_transition("GGr", "gGG"), "gGr")

    def test_one_hz_observation_is_independent_of_simulation_step(self):
        c = self.controller()
        c.observe = Mock()
        c.signals["j"]["until"] = 100
        for tick in range(1, 21):
            c.step(tick / 10, [])
        self.assertEqual(c.observe.call_count, 2)

    def test_fixed_decision_grid_includes_yellow_in_the_slot(self):
        c = self.controller()
        c.method = "cv_mp_2025"
        c.paper_algorithm = True
        c.paper_phase = Mock(return_value="rG")
        c.use_fairness_wrapper = False
        c.fixed_decision_grid = True
        c.decisions = c.switches = 0
        c.signals["j"].update(
            stage="green",
            until=10,
            since=0,
            greens=["Gr", "rG"],
            movements={},
            last={"Gr": 0, "rG": 0},
        )
        with patch.object(module, "ALL_RED_S", 0):
            c.step(10, [])
            self.assertEqual(c.signals["j"]["target_duration"], 7)
            c.step(13, [])
        self.assertEqual(c.signals["j"]["until"], 20)

    def test_ten_distinct_registered_methods(self):
        self.assertEqual(len(METHODS), 11)
        self.assertEqual(len(set(METHODS)), 11)
        self.assertEqual(len(RESEARCH_METHODS), 10)
        self.assertEqual(len({p["url"] for p in PAPERS.values()}), 7)
        self.assertTrue(
            all(not p["uses_rl"] and not p["requires_training"] for p in PAPERS.values())
        )
        self.assertTrue({"cn_mp_2024", "wncn_mp_2024", "wstar_ncn_mp_2024"} <= set(METHODS))
        self.assertTrue(
            {
                "g2p_rule_2025",
                "mamdani_2025",
                "smoothing_mp_2024",
                "heuristic_fuzzy_2025",
                "qd_mp_2025",
            }.isdisjoint(METHODS)
        )
        self.assertTrue(all(p["year"] >= 2023 for p in PAPERS.values()))
        self.assertEqual(tuple(AVAILABLE), METHODS)
        self.assertNotIn("occ_mp", METHODS)

    def controller(self):
        c = PressureController.__new__(PressureController)
        c.api = Mock()
        c.api.vehicle.getAllSubscriptionResults.return_value = {}
        c.net = Mock()
        c.routes, c.types = {}, {}
        c.interval = 10
        c.signals = {
            "j": dict(
                stage="yellow",
                until=3,
                target="rG",
                state="Gr",
                last={"Gr": 0, "rG": 0},
                target_duration=17,
            )
        }
        return c

    def test_zero_all_red_activates_target_at_yellow_end(self):
        c = self.controller()
        with patch.object(module, "ALL_RED_S", 0):
            c.step(3, [])
        c.api.trafficlight.setRedYellowGreenState.assert_called_once_with("j", "rG")
        self.assertEqual(c.signals["j"]["stage"], "green")
        self.assertEqual(c.signals["j"]["until"], 20)  # dynamic extension retained

    def test_optional_all_red_is_a_separate_stage(self):
        c = self.controller()
        with patch.object(module, "ALL_RED_S", 2):
            c.step(3, [])
            self.assertEqual(c.signals["j"]["stage"], "red")
            c.api.trafficlight.setRedYellowGreenState.assert_called_with("j", "rr")
            c.step(5, [])
        c.api.trafficlight.setRedYellowGreenState.assert_called_with("j", "rG")
        self.assertEqual(c.signals["j"]["stage"], "green")


if __name__ == "__main__":
    unittest.main()
