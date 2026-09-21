"""Exercise split-repository install ownership in an isolated filesystem."""
import contextlib
import hashlib
import io
import json
from pathlib import Path
import runpy
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
INSTALLER = ROOT / "scripts/install-device.py"
UNINSTALLER = ROOT / "scripts/uninstall-device.py"


class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="ay3-installer-")
        self.root = Path(self.temp.name)
        self.stage = self.root / "stage"
        self.home = self.root / "home/tester"
        self.state = self.root / "var/lib/ay3-fancontrol"
        self.native = self.home / ".local/share/opengamepadui/plugins/ayaneo-fan-control.zip"
        self.decky = self.home / "homebrew/plugins/ay3-fancontrol"
        self.units = self.root / "etc/systemd/system"
        self.home.mkdir(parents=True)
        self.state.parent.mkdir(parents=True)
        self.commands = []

    def tearDown(self):
        self.temp.cleanup()

    def stage_files(self, native=False):
        files = {
            "backend/ay3_fancontrol.py": "# Backend fixture; never executed\n",
            "systemd/ay3-fancontrol.service": "[Service]\nGroup=bazzite\n",
            "systemd/ay3-fancontrol-sleep.service": "[Service]\nType=oneshot\n",
        }
        if native:
            files["native/plugin.json"] = json.dumps({"plugin.version": "0.5.0"})
            files["dist/ayaneo-fan-control-0.5.0.zip"] = "Native ZIP fixture"
        manifest = {}
        for name, content in files.items():
            destination = self.stage / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(content)
            manifest[name] = hashlib.sha256(destination.read_bytes()).hexdigest()
        (self.stage / "deploy-manifest.json").write_text(json.dumps(manifest))

    def isolated_path(self, value):
        original = type(self.root)(value)
        if str(original).startswith(("/var/lib/ay3-fancontrol", "/etc/systemd/system", "/sys/class/hwmon",
                                     "/sys/devices/platform/ayaneo-ec/hwmon")):
            return self.root / original.relative_to("/")
        return original

    def fake_run(self, command, **_kwargs):
        self.commands.append(list(command))
        return subprocess.CompletedProcess(command, 0, stdout="{}", stderr="")

    def run_installer(self, *options):
        account = SimpleNamespace(pw_dir=str(self.home), pw_uid=1000, pw_gid=1000)
        with patch("sys.argv", [str(INSTALLER), str(self.stage), "--user", "tester", *options]), \
             patch("os.geteuid", return_value=0), patch("os.chown"), \
             patch("pwd.getpwnam", return_value=account), \
             patch("pathlib.Path", side_effect=self.isolated_path), \
             patch("subprocess.run", side_effect=self.fake_run), contextlib.redirect_stdout(io.StringIO()):
            runpy.run_path(str(INSTALLER), run_name="__main__")

    def test_backend_only_needs_no_frontend_payload(self):
        self.stage_files()
        self.run_installer("--backend-only")
        record = json.loads((self.state / "installation.json").read_text())
        self.assertEqual(record["schema_version"], 2)
        self.assertEqual(len(record["files"]), 3)
        self.assertFalse((self.home / ".local").exists())
        self.assertFalse((self.home / "homebrew").exists())

    def test_default_installs_native_without_decky(self):
        self.stage_files(native=True)
        self.run_installer()
        self.assertTrue(self.native.is_file())
        self.assertFalse(self.decky.exists())
        self.assertEqual(len(json.loads((self.state / "installation.json").read_text())["files"]), 4)

    def test_v04_marker_detaches_and_preserves_decky(self):
        self.stage_files(native=True)
        self.state.mkdir()
        (self.state / "app").mkdir()
        backend = self.state / "app/ay3_fancontrol.py"
        backend.write_text("old backend")
        self.native.parent.mkdir(parents=True)
        self.native.write_text("old native")
        self.decky.mkdir(parents=True)
        decky_file = self.decky / "plugin.json"
        decky_file.write_text('{"name":"Ayaneo3 Fans"}')
        self.units.mkdir(parents=True)
        unit = self.units / "ay3-fancontrol.service"
        sleep = self.units / "ay3-fancontrol-sleep.service"
        unit.write_text("old unit")
        sleep.write_text("old sleep unit")
        files = {str(path): "old-digest" for path in [backend, self.native, decky_file, unit, sleep]}
        (self.state / "installation.json").write_text(json.dumps({
            "project": "ay3-fancontrol", "uid": 1000, "user_home": str(self.home), "files": files
        }))
        saved = {"mode": "quiet", "percent": 15, "curve": [10, 30, 40, 70, 100]}
        (self.state / "config.json").write_text(json.dumps(saved))

        self.run_installer()

        updated = json.loads((self.state / "installation.json").read_text())
        self.assertEqual(updated["schema_version"], 2)
        self.assertNotIn(str(decky_file.resolve()), updated["files"])
        self.assertEqual(decky_file.read_text(), '{"name":"Ayaneo3 Fans"}')
        migration = json.loads((self.state / "detached-decky-v0.5.0.json").read_text())
        self.assertIn(str(decky_file), migration["preserved_files"])
        self.assertEqual(json.loads((self.state / "config.json").read_text()), saved)

    def test_backend_refresh_retains_native_ownership_and_settings(self):
        self.stage_files(native=True)
        self.run_installer()
        saved = {"mode": "curve", "percent": 20, "curve": [0, 20, 40, 70, 100]}
        (self.state / "config.json").write_text(json.dumps(saved))
        original = json.loads((self.state / "installation.json").read_text())["files"]
        self.stage_files()
        self.run_installer("--backend-only")
        self.assertEqual(json.loads((self.state / "installation.json").read_text())["files"], original)
        self.assertTrue(self.native.is_file())
        self.assertEqual(json.loads((self.state / "config.json").read_text()), saved)

    def test_uninstaller_preserves_decky_from_legacy_marker(self):
        self.state.mkdir()
        backend = self.state / "app/ay3_fancontrol.py"
        backend.parent.mkdir()
        backend.write_text("backend")
        self.native.parent.mkdir(parents=True)
        self.native.write_text("native")
        self.decky.mkdir(parents=True)
        decky_file = self.decky / "plugin.json"
        decky_file.write_text("decky")
        self.units.mkdir(parents=True)
        unit_paths = [self.units / "ay3-fancontrol.service", self.units / "ay3-fancontrol-sleep.service"]
        for path in unit_paths:
            path.write_text("unit")
        physical = self.root / "sys/devices/platform/ayaneo-ec/hwmon/hwmon77"
        physical.mkdir(parents=True)
        (physical / "name").write_text("ayaneo_ec")
        (physical / "pwm1_enable").write_text("2")
        hwmon = self.root / "sys/class/hwmon"
        hwmon.mkdir(parents=True)
        (hwmon / "hwmon77").symlink_to(physical, target_is_directory=True)
        files = {str(path): "digest" for path in [backend, self.native, decky_file, *unit_paths]}
        (self.state / "installation.json").write_text(json.dumps({
            "project": "ay3-fancontrol", "user_home": str(self.home), "files": files
        }))

        with patch("os.geteuid", return_value=0), \
             patch("pathlib.Path", side_effect=self.isolated_path), \
             patch("subprocess.run", side_effect=self.fake_run), contextlib.redirect_stdout(io.StringIO()):
            runpy.run_path(str(UNINSTALLER), run_name="__main__")

        self.assertFalse(backend.exists())
        self.assertFalse(self.native.exists())
        self.assertTrue(decky_file.is_file())
        self.assertEqual(decky_file.read_text(), "decky")
        self.assertTrue((self.state / "detached-decky-v0.5.0.json").is_file())


if __name__ == "__main__":
    unittest.main()
