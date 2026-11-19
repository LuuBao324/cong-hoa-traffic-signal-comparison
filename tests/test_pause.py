"""Pause checkpoints must remain resumable and must not start queued simulations."""

import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from traffic_study import batch_experiments as batch


class PauseTests(unittest.TestCase):
    def test_interrupted_result_is_rerun_on_resume(self):
        with tempfile.TemporaryDirectory(dir=batch.ROOT) as directory:
            folder = Path(directory).resolve()
            self.assertTrue(folder.is_relative_to(batch.ROOT))
            path = folder / "result.json"
            result = dict(status="paused", signature={"network": "same"}, simulation_end_s=2400)
            path.write_text(json.dumps(result), encoding="utf-8")
            self.assertFalse(batch.complete_result(path, result["signature"], 2400))
            result["status"] = "complete"
            path.write_text(json.dumps(result), encoding="utf-8")
            self.assertTrue(batch.complete_result(path, result["signature"], 2400))

    def test_pause_prevents_queued_cases_and_input_generation(self):
        with tempfile.TemporaryDirectory(dir=batch.ROOT) as directory:
            folder = Path(directory).resolve()
            self.assertTrue(folder.is_relative_to(batch.ROOT))
            (folder / ".pause_requested").touch()
            args = SimpleNamespace(output=folder)
            with patch.object(batch.subprocess, "run") as launch:
                self.assertEqual(batch.run_case(args, 0.1, 100, ["fixed_time"]), 0)
                batch.worker(args)
                launch.assert_not_called()


if __name__ == "__main__":
    unittest.main()
