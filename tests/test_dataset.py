"""Checks provenance pairing and missing metrics without running SUMO."""

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from traffic_study import dataset as dataset


class DatasetTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=dataset.ROOT, prefix=".dataset-test-")
        self.root = Path(self.temp.name)
        self.folder = self.root / "sample"
        self.folder.mkdir()
        self.signature = {"network": "version-a"}
        self.write(
            self.folder / "plan.json",
            dict(
                methods=["fixed_time", "c_mp"],
                scales=[0.5],
                seeds=[100],
                end_s=2400,
                signature={**self.signature, "end_s": 2400},
                planned_runs=2,
            ),
        )
        self.patch = patch.object(dataset, "BASE", self.root)
        self.patch.start()
        for method, duration in [("fixed_time", 100), ("c_mp", 80)]:
            path = self.folder / "runs" / "d0.5_s100" / method
            path.mkdir(parents=True)
            result = dict(
                method=method,
                seed=100,
                demand_scale=0.5,
                simulation_end_s=2400,
                signature=self.signature,
                backend="libsumo",
                engine_version=[22, "SUMO 1.28.0"],
                status="complete",
                input_hashes={"traffic": "same"},
                collisions=0,
                teleports=0,
                probes=[
                    dict(
                        method=method,
                        probe_id="probe_car",
                        vehicle_type="car",
                        route_variant="outer",
                        completed=True,
                        valid_for_comparison=True,
                        travel_time_s=duration,
                        waiting_time_s=10,
                        depart_delay_s=2,
                    )
                ],
            )
            self.write(path / "result.json", result)
            (path / "tripinfo.xml").write_text(
                '<tripinfos><tripinfo id="probe_car" routeLength="1000" timeLoss="12" waitingCount="2"/></tripinfos>'
            )

    def write(self, path, data):
        path.write_text(json.dumps(data), encoding="utf-8")

    def edit_result(self, **changes):
        path = self.folder / "runs/d0.5_s100/c_mp/result.json"
        result = json.loads(path.read_text())
        result.update(changes)
        self.write(path, result)

    def tearDown(self):
        self.patch.stop()
        assert self.root.resolve().is_relative_to(dataset.ROOT.resolve())
        self.temp.cleanup()

    def test_paired_reduction_and_speed(self):
        row = next(r for r in dataset.build_dataset("sample")["rows"] if r["method"] == "c_mp")
        self.assertTrue(row["paired_valid"])
        self.assertAlmostEqual(row["improvement_vs_fixed_percent"], 20)
        self.assertAlmostEqual(row["mean_speed_kmh"], 45)
        self.assertEqual(row["travel_time_s"], 80)  # excludes depart_delay

    def test_export_uses_one_dataset_and_preserves_recorded_results(self):
        result_files = list(self.folder.glob("runs/*/*/result.json"))
        original = {path: path.read_bytes() for path in result_files}
        exported = dataset.export_dataset(self.folder)
        self.assertEqual(len(exported["rows"]), 2)
        self.assertTrue((self.folder / "dataset.csv").exists())
        self.assertTrue((self.folder / "dataset_metadata.json").exists())
        self.assertTrue((self.folder / "pairwise.csv").exists())
        self.assertFalse((self.folder / "features.csv").exists())
        self.assertEqual(original, {path: path.read_bytes() for path in result_files})

    def test_different_inputs_cannot_pair(self):
        self.edit_result(input_hashes={"traffic": "different"})
        row = next(r for r in dataset.build_dataset("sample")["rows"] if r["method"] == "c_mp")
        self.assertFalse(row["paired_valid"])
        self.assertIsNone(row["improvement_vs_fixed_percent"])

    def test_different_simulator_versions_cannot_pair(self):
        self.edit_result(engine_version=[22, "SUMO 1.27.1"])
        row = next(r for r in dataset.build_dataset("sample")["rows"] if r["method"] == "c_mp")
        self.assertFalse(row["paired_valid"])

    def test_pairwise_comparison_preserves_vehicle_strata(self):
        rows = dataset.build_dataset("sample")["rows"]
        pairs = dataset.pairwise_rows(rows)
        self.assertEqual(len(pairs), 1)
        self.assertTrue(pairs[0]["paired_valid"])
        self.assertEqual(pairs[0]["difference_a_minus_b_s"], -20)
        self.assertAlmostEqual(pairs[0]["improvement_a_vs_b_percent"], 20)
        self.assertEqual(pairs[0]["vehicle_type"], "car")

    def test_analysis_rows_exclude_bibliography(self):
        row = dataset.build_dataset("sample")["rows"][0]
        self.assertNotIn("paper_url", row)
        self.assertNotIn("paper_year", row)

    def test_detector_outputs_do_not_change_frozen_input_digest(self):
        inputs = self.root / "inputs"
        inputs.mkdir()
        (inputs / "fixed_time.sumocfg").write_text(
            '<configuration><input><net-file value="net.xml"/>'
            '<route-files value="traffic.xml"/><additional-files value="signals.xml"/>'
            "</input></configuration>",
            encoding="utf-8",
        )
        hashes = {
            "fixed_time.sumocfg": "config",
            "net.xml": "network",
            "traffic.xml": "routes",
            "signals.xml": "signals",
            "cong_hoa_counts.xml": "first-output",
        }
        original = dataset.input_digest(hashes, inputs)
        hashes["cong_hoa_counts.xml"] = "different-output"
        self.assertEqual(dataset.input_digest(hashes, inputs), original)
        hashes["traffic.xml"] = "different-input"
        self.assertNotEqual(dataset.input_digest(hashes, inputs), original)

    def test_missing_metadata_is_not_zero_demand(self):
        self.assertIsNone(dataset.build_dataset("sample")["rows"][0]["map_requested_vph"])

    def test_mixed_code_version_excluded(self):
        self.edit_result(signature={"network": "version-b"})
        data = dataset.build_dataset("sample")
        self.assertEqual(len(data["runs"]), 1)
        self.assertTrue(data["issues"])

    def test_unfinished_probe_not_given_distance(self):
        path = self.folder / "runs/d0.5_s100/c_mp/result.json"
        result = json.loads(path.read_text())
        result["probes"][0].update(completed=False, valid_for_comparison=False, travel_time_s=None)
        self.write(path, result)
        row = next(r for r in dataset.build_dataset("sample")["rows"] if r["method"] == "c_mp")
        self.assertIsNone(row["route_length_m"])
        self.assertIsNone(row["mean_speed_kmh"])
        self.assertFalse(row["paired_valid"])

    def test_unknown_path_rejected(self):
        with self.assertRaises(ValueError):
            dataset.build_dataset("../sample")

    def enable_arrival_policy(self):
        path = self.folder / "plan.json"
        plan = json.loads(path.read_text())
        plan["comparison_policy"] = "all_four_arrived"
        self.write(path, plan)
        for path in self.folder.glob("runs/*/*/result.json"):
            result = json.loads(path.read_text())
            template = result["probes"][0]
            result["probes"] = [
                dict(template, probe_id=pid, vehicle_type=kind, route_variant=route)
                for pid, kind, route in [
                    ("probe_car", "car", "outer"),
                    ("probe_motorcycle", "motorcycle", "outer"),
                    ("probe_car_center", "car", "center"),
                    ("probe_motorcycle_center", "motorcycle", "center"),
                ]
            ]
            self.write(path, result)

    def test_arrival_policy_includes_event_runs_and_preserves_warnings(self):
        self.enable_arrival_policy()
        self.edit_result(collisions=1, teleports=1)
        folder = self.folder / "runs/d0.5_s100/c_mp"
        (folder / "sumo.log").write_text(
            "Warning: Teleporting vehicle 'probe_car'; junction collision with vehicle 'background_1'."
        )
        data = dataset.export_dataset(self.folder)
        rows = [r for r in data["rows"] if r["method"] == "c_mp"]
        self.assertTrue(all(r["paired_valid"] for r in rows))
        self.assertTrue(all(not r["clean_run"] for r in rows))
        car = next(r for r in rows if r["probe_id"] == "probe_car")
        self.assertTrue(car["probe_teleported"])
        self.assertTrue(car["probe_collision"])
        self.assertEqual(car["improvement_vs_fixed_percent"], 20)
        self.assertEqual(car["collisions"], 1)
        self.assertFalse(dataset.pairwise_rows(data["rows"])[0]["clean_pair"])

    def test_arrival_policy_requires_all_four_even_for_an_arrived_member(self):
        self.enable_arrival_policy()
        path = self.folder / "runs/d0.5_s100/c_mp/result.json"
        result = json.loads(path.read_text())
        result["probes"][-1].update(completed=False, travel_time_s=None)
        self.write(path, result)
        rows = [r for r in dataset.build_dataset("sample")["rows"] if r["method"] == "c_mp"]
        self.assertTrue(rows[0]["completed"])
        self.assertTrue(all(not r["valid_for_comparison"] for r in rows))
        self.assertTrue(all(not r["paired_valid"] for r in rows))


if __name__ == "__main__":
    unittest.main()
