"""Exercise installer file selection in a temporary root with all service calls mocked."""
import contextlib
import hashlib
import io
import json
from pathlib import Path
import runpy
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

INSTALLER = Path(__file__).resolve().parents[1] / "scripts/install-device.py"


class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="ay3-installer-")
        self.root = Path(self.temp.name)
        self.stage = self.root / "stage"
        self.home = self.root / "home/tester"
        self.state = self.root / "var/lib/ay3-fancontrol"
        self.native = self.home / ".local/share/opengamepadui/plugins/ayaneo-fan-control.zip"
        self.decky = self.home / "homebrew/plugins/ay3-fancontrol"
        self.home.mkdir(parents=True)
        self.state.parent.mkdir(parents=True)
        self.commands = []

    def tearDown(self):
        self.temp.cleanup()

    def stage_files(self, native=False, decky=False):
        files = {
            "src/ay3_fancontrol.py": "# Backend fixture; never executed\n",
            "systemd/ay3-fancontrol.service": "[Service]\nGroup=bazzite\n",
            "systemd/ay3-fancontrol-sleep.service": "[Service]\nType=oneshot\n",
        }
        if native:
            files["native/plugin.json"] = json.dumps({"plugin.version": "0.4.0"})
            files["dist/ayaneo-fan-control-0.4.0.zip"] = "Native ZIP fixture"
        if decky:
            files.update({name: "Decky fixture" for name in ["main.py", "dist/index.js", "LICENSE", "LICENSE.decky-api"]})
            files["plugin.json"] = json.dumps({"name": "Ayaneo3 Fans"})
            files["package.json"] = json.dumps({"name": "ayaneo3-fans", "version": "0.4.0"})
        manifest = {}
        for name, content in files.items():
            destination = self.stage / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(content)
            manifest[name] = hashlib.sha256(destination.read_bytes()).hexdigest()
        (self.stage / "deploy-manifest.json").write_text(json.dumps(manifest))

    def run_installer(self, *options):
        def isolated_path(value):
            original = type(self.root)(value)
            if str(original).startswith(("/var/lib/ay3-fancontrol", "/etc/systemd/system")):
                return self.root / original.relative_to("/")
            return original

        def run(command, **kwargs):
            self.commands.append(list(command))
            return subprocess.CompletedProcess(command, 0, stdout="{}", stderr="")

        account = SimpleNamespace(pw_dir=str(self.home), pw_uid=1000, pw_gid=1000)
        with patch("sys.argv", [str(INSTALLER), str(self.stage), "--user", "tester", *options]), \
             patch("os.geteuid", return_value=0), patch("os.chown"), \
             patch("pwd.getpwnam", return_value=account), \
             patch("pathlib.Path", side_effect=isolated_path), \
             patch("subprocess.run", side_effect=run), contextlib.redirect_stdout(io.StringIO()):
            runpy.run_path(str(INSTALLER), run_name="__main__")

    def test_backend_only_needs_no_native_or_decky_payload(self):
        self.stage_files()
        self.run_installer("--backend-only")
        record = json.loads((self.state / "installation.json").read_text())
        self.assertEqual(len(record["files"]), 3)
        self.assertFalse((self.home / ".local").exists())
        self.assertFalse((self.home / "homebrew").exists())
        self.assertEqual(json.loads((self.state / "config.json").read_text())["mode"], "auto")

    def test_default_installs_native_without_decky(self):
        self.stage_files(native=True)
        self.run_installer()
        self.assertTrue(self.native.is_file())
        self.assertFalse(self.decky.exists())

    def test_adding_decky_preserves_native_and_current_configuration(self):
        self.stage_files(native=True, decky=True)
        self.run_installer()
        saved = {"mode": "quiet", "percent": 15, "curve": [10, 30, 40, 70, 100]}
        (self.state / "config.json").write_text(json.dumps(saved))
        self.decky.parent.mkdir(parents=True)
        self.run_installer("--with-decky")
        self.assertTrue(self.native.is_file())
        self.assertEqual(json.loads((self.decky / "plugin.json").read_text())["name"], "Ayaneo3 Fans")
        self.assertEqual(json.loads((self.state / "config.json").read_text()), saved)
        self.assertIn(["systemctl", "restart", "plugin_loader.service"], self.commands)

    def test_backend_refresh_preserves_frontends_and_their_manifest_entries(self):
        self.stage_files(native=True, decky=True)
        self.decky.parent.mkdir(parents=True)
        self.run_installer("--with-decky")
        record = json.loads((self.state / "installation.json").read_text())
        self.commands.clear()
        self.stage_files()
        self.run_installer("--backend-only")
        updated = json.loads((self.state / "installation.json").read_text())
        self.assertEqual(updated["files"], record["files"])
        self.assertEqual(self.native.read_text(), "Native ZIP fixture")
        self.assertEqual(json.loads((self.decky / "plugin.json").read_text())["name"], "Ayaneo3 Fans")
        self.assertNotIn(["systemctl", "restart", "plugin_loader.service"], self.commands)

    def test_conflicting_frontend_options_are_rejected_before_writing(self):
        self.stage_files()
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as failure:
            self.run_installer("--backend-only", "--with-decky")
        self.assertEqual(failure.exception.code, 2)
        self.assertFalse(self.state.exists())


if __name__ == "__main__":
    unittest.main()
