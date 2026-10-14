"""Contract and native parser checks for the opt-in profile; never start a daemon."""
import configparser
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
KEY = "OPENCV_THREAD_POOL_ACTIVE_WAIT_WORKER"
PROFILE = ROOT / "systemd/examples/90-opencv-worker-no-spin.conf"
DOC = ROOT / "docs/opencv-worker-wait.md"


class OpenCVWorkerProfileTests(unittest.TestCase):
    def test_only_worker_wait_is_overridden(self):
        parser = configparser.ConfigParser(interpolation=None)
        parser.optionxform = lambda optionstr: optionstr
        parser.read_string(PROFILE.read_text())
        self.assertEqual(parser.sections(), ["Service"])
        self.assertEqual(dict(parser["Service"]), {"Environment": KEY + "=0"})

    def test_default_unit_is_not_changed(self):
        self.assertNotIn(KEY, (ROOT / "systemd/xr-driver.service").read_text())
        self.assertFalse((ROOT / "systemd/xr-driver.service.d").exists())

    def test_documentation_has_opt_in_and_rollback_boundary(self):
        text = DOC.read_text()
        for contract in ("opt-in", "latency", "not a fix for image jitter", "cached",
                         "systemctl --user daemon-reload", "systemctl --user restart xr-driver.service",
                         "DropInPaths", "13.2", "0.229"):
            with self.subTest(contract=contract):
                self.assertIn(contract, text)
        self.assertNotIn("systemctl restart xr-driver", text)

    def test_native_systemd_parser_accepts_sample(self):
        with tempfile.TemporaryDirectory(prefix="xr-profile-verify-") as name:
            directory = Path(name)
            unit = directory / "xr-driver.service"
            unit.write_text("[Unit]\nDescription=Inert profile syntax fixture\n"
                            "[Service]\nType=oneshot\nExecStart=/usr/bin/true\n")
            overrides = directory / "xr-driver.service.d"
            overrides.mkdir()
            (overrides / PROFILE.name).write_bytes(PROFILE.read_bytes())
            result = subprocess.run(["systemd-analyze", "--user", "verify", "--man=no", str(unit)],
                                    env=os.environ | {"SYSTEMD_UNIT_PATH": str(directory) + ":"},
                                    capture_output=True, text=True, timeout=15)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
