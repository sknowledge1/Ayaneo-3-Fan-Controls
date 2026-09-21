import copy
import base64
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
import ay3_fancontrol as fan


class FakeHardware:
    def __init__(self):
        self.mode, self.pwm, self.rpm, self.temperature = 2, 102, 2800, 42
        self.read_error = None
        self.write_error = None
        self.auto_calls = 0

    def sample(self):
        if self.read_error:
            raise RuntimeError(self.read_error)
        return {"hardware_mode": self.mode, "pwm": self.pwm, "rpm": self.rpm, "cpu_c": self.temperature}

    def automatic(self):
        self.auto_calls += 1
        self.mode = 2

    def manual(self, percent):
        if self.write_error:
            raise RuntimeError(self.write_error)
        self.mode = 1
        self.pwm = round(percent * 255 / 100)
        return round(percent)


class ControllerTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory(prefix="ay3-test-")
        self.config = Path(self.folder.name) / "config.json"
        self.hardware = FakeHardware()
        self.now = 10
        self.controller = fan.Controller(self.hardware, self.config, lambda: self.now)
        self.controller.tick()

    def tearDown(self):
        self.folder.cleanup()

    def configure(self, mode="manual", **changes):
        value = {**copy.deepcopy(fan.DEFAULT), "mode": mode, **changes}
        return self.controller.configure(value)

    def test_manual_and_auto(self):
        self.assertTrue(self.configure(percent=60)["ok"])
        self.assertEqual(self.hardware.mode, 1)
        self.assertEqual(self.hardware.pwm, 153)
        self.assertTrue(self.configure("auto")["automatic_verified"])
        self.assertEqual(self.hardware.mode, 2)

    def test_saved_curve_is_loaded(self):
        self.configure("curve")
        new = fan.Controller(self.hardware, self.config, lambda: self.now)
        new.tick()
        self.assertEqual(new.config["mode"], "curve")
        self.assertEqual(self.hardware.mode, 1)

    def test_sensor_failure_releases_and_persists_auto(self):
        self.configure()
        self.hardware.read_error = "sensor missing"
        self.controller.tick()
        self.assertEqual(self.hardware.mode, 2)
        self.assertIn("sensor missing", self.controller.fault)
        self.assertEqual(json.loads(self.config.read_text())["mode"], "auto")
        self.assertIsNone(self.controller.status()["telemetry"])

    def test_write_failure_releases(self):
        self.hardware.write_error = "write refused"
        result = self.configure()
        self.assertFalse(result["ok"])
        self.assertEqual(self.hardware.mode, 2)

    def test_thermal_floor_overrides_low_manual_duty(self):
        self.hardware.temperature = 95
        result = self.configure(percent=40)
        self.assertEqual(result["effective_percent"], 100)

    def test_critical_temperature_releases(self):
        self.configure()
        self.hardware.temperature = 98
        self.controller.tick()
        self.assertEqual(self.hardware.mode, 2)
        self.assertEqual(self.controller.config["mode"], "auto")

    def test_refuses_hot_acquisition(self):
        self.hardware.temperature = 98
        with self.assertRaises(ValueError):
            self.configure()
        self.assertEqual(self.hardware.mode, 2)

    def test_stall_releases_after_grace(self):
        self.configure()
        self.hardware.rpm = 0
        for _ in range(8):
            self.now += 1
            self.controller.tick()
        self.assertEqual(self.hardware.mode, 2)
        self.assertIn("rotation", self.controller.fault)

    def test_changed_ownership_releases(self):
        self.configure()
        self.hardware.mode = 2
        self.now += 1
        self.controller.tick()
        self.assertEqual(self.controller.config["mode"], "auto")
        self.assertIn("ownership", self.controller.fault)

    def test_does_not_acquire_over_other_owner(self):
        self.hardware.mode = 1
        with self.assertRaises(RuntimeError):
            self.configure()
        self.assertEqual(self.controller.config["mode"], "auto")

    def test_inactive_controller_does_not_fight_another_owner(self):
        count = self.hardware.auto_calls
        self.hardware.mode = 1
        self.controller.tick()
        self.assertEqual(self.hardware.auto_calls, count)
        self.assertFalse(self.controller.status()["automatic_verified"])

    def test_long_gap_releases_then_can_be_reenabled(self):
        self.configure()
        self.now += 7
        self.controller.tick()
        self.assertEqual(self.hardware.mode, 2)
        self.now += 20
        self.assertTrue(self.configure()["ok"])

    def test_curve_interpolation_and_smooth_decrease(self):
        self.hardware.temperature = 70
        self.configure("curve")
        duty = self.controller.last_duty
        self.hardware.temperature = 45
        self.now += 1
        self.controller.tick()
        self.assertGreaterEqual(self.controller.last_duty, duty - 3)

    def test_stale_telemetry_is_hidden(self):
        self.now += 6
        self.assertIsNone(self.controller.status()["telemetry"])
        self.assertFalse(self.controller.status()["automatic_verified"])

    def test_close_returns_auto(self):
        self.configure()
        self.controller.close()
        self.assertEqual(self.hardware.mode, 2)

    def test_invalid_saved_config_uses_auto(self):
        self.config.write_text('{"mode": "manual"}')
        controller = fan.Controller(self.hardware, self.config)
        self.assertEqual(controller.config["mode"], "auto")
        self.assertIn("Invalid saved", controller.fault)

    def test_invalid_configs_never_write_hardware(self):
        cases = [{}, {**fan.DEFAULT, "percent": True}, {**fan.DEFAULT, "percent": -1},
                 {**fan.DEFAULT, "curve": [40, 70, 60, 85, 100]},
                 {**fan.DEFAULT, "curve": [40, 50, 70, 85, 90]},
                 {**fan.DEFAULT, "mode": "off"}, {**fan.DEFAULT, "path": "/etc/passwd"}]
        for value in cases:
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.controller.configure(value)
        self.assertEqual(self.hardware.mode, 2)

    def test_config_save_failure_preserves_state(self):
        with patch.object(fan, "save_config", side_effect=OSError("disk full")):
            with self.assertRaises(OSError):
                self.configure()
        self.assertEqual(self.controller.config["mode"], "auto")
        self.assertEqual(self.hardware.mode, 2)

    def test_intentional_zero_duty_does_not_trigger_stall_recovery(self):
        self.hardware.temperature = 40
        self.hardware.rpm = 0
        self.configure(percent=0)
        for _ in range(10):
            self.now += 1
            self.controller.tick()
        self.assertEqual(self.controller.last_duty, 0)
        self.assertEqual(self.hardware.mode, 1)
        self.assertIsNone(self.controller.fault)

    def test_nonzero_request_uses_validated_running_floor(self):
        self.hardware.temperature = 40
        self.assertEqual(self.configure(percent=1)["effective_percent"], 10)

    def test_warming_restarts_stopped_fan_with_spinup_grace(self):
        self.hardware.temperature = 40
        self.hardware.rpm = 0
        self.configure(percent=0)
        for _ in range(10):
            self.now += 1
            self.controller.tick()
        self.hardware.temperature = 46
        for _ in range(3):
            self.now += 1
            self.controller.tick()
        self.assertEqual(self.controller.last_duty, 10)
        self.assertIsNone(self.controller.fault)
        self.hardware.rpm = 710
        self.hardware.temperature = 44
        self.now += 1
        self.controller.tick()
        self.assertEqual(self.controller.last_duty, 10)
        self.hardware.temperature = 41
        self.now += 1
        self.controller.tick()
        self.assertEqual(self.controller.last_duty, 0)

    def test_zero_curve_is_allowed_but_hot_endpoint_stays_full(self):
        self.hardware.temperature = 40
        result = self.configure("curve", curve=[0, 0, 60, 80, 100])
        self.assertTrue(result["ok"])
        self.assertEqual(result["effective_percent"], 0)
        self.hardware.temperature = 95
        self.now += 1
        self.controller.tick()
        self.assertEqual(self.controller.last_duty, 100)

    def test_quiet_uses_gentler_policy_independent_of_saved_curve(self):
        # Explicit expected outputs catch the old, aggressive floor overriding Quiet.
        for temperature, duty in [(40, 0), (45, 0), (46, 10), (55, 15), (65, 25),
                                  (75, 35), (85, 55), (90, 75), (95, 100)]:
            with self.subTest(temperature=temperature):
                self.hardware.temperature = temperature
                result = self.configure("quiet", percent=100, curve=[100] * 5)
                self.assertTrue(result["ok"])
                self.assertEqual(result["effective_percent"], duty)
                self.assertEqual(self.hardware.mode, 1)

    def test_standard_policy_only_moves_the_last_temperature(self):
        self.assertEqual(fan.ANCHORS, [40, 55, 65, 75, 95])
        for temperature, duty in [(55, 40), (65, 60), (75, 80), (85, 90), (95, 100)]:
            with self.subTest(temperature=temperature):
                self.hardware.temperature = temperature
                self.assertEqual(self.configure(percent=0)["effective_percent"], duty)

    def test_all_software_modes_reach_full_before_recovery(self):
        for mode in ("manual", "curve", "quiet"):
            for temperature in (95, 97.999):
                with self.subTest(mode=mode, temperature=temperature):
                    self.hardware.temperature = temperature
                    result = self.configure(mode, percent=0, curve=[0, 0, 0, 0, 100])
                    self.assertTrue(result["ok"])
                    self.assertEqual(result["effective_percent"], 100)
                    self.assertEqual(self.hardware.mode, 1)
            self.hardware.temperature = 98
            self.now += 1
            self.controller.tick()
            self.assertEqual(self.hardware.mode, 2)
            self.assertEqual(json.loads(self.config.read_text())["mode"], "auto")
            with self.assertRaises(ValueError):
                self.configure(mode)

    def test_quiet_persists_without_overwriting_custom_settings(self):
        saved = {"mode": "quiet", "percent": 15, "curve": [10, 30, 40, 70, 100]}
        self.controller.configure(saved)
        new = fan.Controller(self.hardware, self.config, lambda: self.now)
        new.tick()
        self.assertEqual(new.config, saved)
        self.assertEqual(new.last_duty, 0)
        restored = {**saved, "mode": "curve"}
        self.assertEqual(new.configure(restored)["config"], restored)

    def test_quiet_cools_gradually_but_heats_without_rate_limit(self):
        self.hardware.temperature = 85
        self.configure("quiet")
        self.hardware.temperature = 65
        self.now += 1
        self.controller.tick()
        self.assertEqual(self.controller.last_duty, 52)
        self.hardware.temperature = 95
        self.now += 1
        self.controller.tick()
        self.assertEqual(self.controller.last_duty, 100)

    def test_quiet_stop_restart_hysteresis_and_failed_restart(self):
        self.hardware.temperature = 40
        self.hardware.rpm = 0
        self.configure("quiet")
        for _ in range(10):
            self.now += 1
            self.controller.tick()
        self.assertEqual(self.controller.last_duty, 0)
        self.assertIsNone(self.controller.fault)
        self.hardware.temperature = 46
        self.now += 1
        self.controller.tick()
        self.assertEqual(self.controller.last_duty, 10)
        self.assertIsNone(self.controller.fault)
        self.hardware.rpm = 710
        self.hardware.temperature = 44
        self.now += 1
        self.controller.tick()
        self.assertEqual(self.controller.last_duty, 10)
        self.hardware.temperature = 42
        self.now += 1
        self.controller.tick()
        self.assertEqual(self.controller.last_duty, 0)
        self.hardware.temperature = 46
        self.hardware.rpm = 0
        for _ in range(9):
            self.now += 1
            self.controller.tick()
        self.assertEqual(self.hardware.mode, 2)
        self.assertIn("rotation", self.controller.fault)

    def test_quiet_sensor_failure_still_recovers(self):
        self.configure("quiet")
        self.hardware.read_error = "sensor missing"
        self.controller.tick()
        self.assertEqual(self.hardware.mode, 2)
        self.assertEqual(json.loads(self.config.read_text())["mode"], "auto")

    def test_status_exposes_quiet_preview_and_temperature_limits(self):
        status = self.configure("quiet")
        self.assertEqual(status["api_version"], 1)
        self.assertEqual(status["full_speed_c"], 95)
        self.assertEqual(status["recovery_c"], 98)
        self.assertEqual(status["quiet_points"][0], (45, 0))
        self.assertEqual(status["quiet_points"][-1], (95, 100))

    def test_native_cli_roundtrip_preserves_json_quotes_and_zero(self):
        config = {"mode": "manual", "percent": 0, "curve": [0, 10, 60, 80, 100]}
        encoded = base64.b64encode(json.dumps(config).encode()).decode()
        self.assertEqual(fan.decode_cli_config(encoded), config)

    def test_native_cli_rejects_invalid_or_excessive_payload(self):
        for encoded in ["not base64!", "A" * 8193, base64.b64encode(b'{"mode":"manual"}').decode()]:
            with self.subTest(encoded=encoded[:20]), self.assertRaises(ValueError):
                fan.decode_cli_config(encoded)


class HardwareTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory(prefix="ay3-hwmon-")
        self.root = Path(self.folder.name)
        values = {"sys/class/dmi/id/board_vendor": "AYANEO", "sys/class/dmi/id/board_name": "AYANEO 3",
                  "proc/cpuinfo": "model name: AMD Ryzen 7 8840U",
                  "sys/devices/platform/ayaneo-ec/hwmon/hwmon77/name": "ayaneo_ec",
                  "sys/devices/platform/ayaneo-ec/hwmon/hwmon77/pwm1": "102",
                  "sys/devices/platform/ayaneo-ec/hwmon/hwmon77/pwm1_enable": "2",
                  "sys/devices/platform/ayaneo-ec/hwmon/hwmon77/fan1_input": "2800",
                  "sys/class/hwmon/hwmon3/name": "k10temp",
                  "sys/class/hwmon/hwmon3/temp1_label": "Tctl",
                  "sys/class/hwmon/hwmon3/temp1_input": "42000",
                  "sys/class/hwmon/hwmon1/name": "amdgpu"}
        for path, value in values.items():
            target = self.root / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(value)
        (self.root / "sys/class/hwmon/hwmon77").symlink_to(self.root / "sys/devices/platform/ayaneo-ec/hwmon/hwmon77")

    def tearDown(self):
        self.folder.cleanup()

    def test_name_and_path_discovery(self):
        hardware = fan.Hardware(self.root)
        self.assertEqual(hardware.sample()["rpm"], 2800)
        hardware.manual(60)
        self.assertEqual(hardware.sample()["pwm"], 153)
        hardware.automatic()
        self.assertEqual(hardware.sample()["hardware_mode"], 2)

    def test_wrong_model_rejected(self):
        (self.root / "sys/class/dmi/id/board_name").write_text("AYANEO 2")
        with self.assertRaises(RuntimeError):
            fan.Hardware(self.root)

    def test_hx370_ayaneo3_uses_the_same_hwmon_contract(self):
        (self.root / "proc/cpuinfo").write_text("AMD Ryzen AI 9 HX 370")
        hardware = fan.Hardware(self.root)
        self.assertEqual(hardware.sample()["cpu_c"], 42)
        hardware.manual(60)
        self.assertEqual(hardware.sample()["pwm"], 153)
        hardware.automatic()
        self.assertEqual(hardware.sample()["hardware_mode"], 2)

    def test_ayaneo3_product_identity_allows_board_name_variants(self):
        dmi = self.root / "sys/class/dmi/id"
        (dmi / "sys_vendor").write_text("AYANEO")
        (dmi / "product_name").write_text("AYANEO 3")
        (dmi / "board_name").write_text("Variant board")
        self.assertEqual(fan.Hardware(self.root).sample()["rpm"], 2800)

    def test_ayaneo3_is_not_gated_by_cpu_name_or_cpuinfo(self):
        (self.root / "proc/cpuinfo").write_text("Another AYANEO 3 CPU variant")
        self.assertEqual(fan.Hardware(self.root).sample()["rpm"], 2800)
        (self.root / "proc/cpuinfo").unlink()
        self.assertEqual(fan.Hardware(self.root).sample()["rpm"], 2800)

    def test_other_variants_still_require_valid_temperature_telemetry(self):
        (self.root / "proc/cpuinfo").write_text("AMD Ryzen AI 9 HX 370")
        (self.root / "sys/class/hwmon/hwmon3/temp1_label").write_text("Other sensor")
        with self.assertRaisesRegex(RuntimeError, "Tctl sensor"):
            fan.Hardware(self.root)

    def test_wrong_fan_path_rejected(self):
        (self.root / "sys/class/hwmon/hwmon77").unlink()
        path = self.root / "sys/class/hwmon/hwmon90"
        path.mkdir()
        (path / "name").write_text("ayaneo_ec")
        with self.assertRaises(RuntimeError):
            fan.Hardware(self.root)

    def test_auto_does_not_require_temperature(self):
        hardware = fan.Hardware(self.root)
        hardware.manual(60)
        hardware.cpu.unlink()
        with self.assertRaises(FileNotFoundError):
            hardware.sample()
        hardware.automatic()
        self.assertEqual(fan.read_int(hardware.fan / "pwm1_enable"), 2)

    def test_implausible_temperature_rejected(self):
        hardware = fan.Hardware(self.root)
        hardware.cpu.write_text("0")
        with self.assertRaises(RuntimeError):
            hardware.sample()

    def test_auto_does_not_read_firmware_duty_register(self):
        hardware = fan.Hardware(self.root)
        (hardware.fan / "pwm1").write_text("firmware-private-value")
        self.assertIsNone(hardware.sample()["pwm"])
        (hardware.fan / "pwm1_enable").write_text("1")
        with self.assertRaises(ValueError):
            hardware.sample()

    def test_recovery_rediscovers_renumbered_fan_without_touching_old_index(self):
        hardware = fan.Hardware(self.root)
        hardware.manual(60)
        old = hardware.fan
        physical = old.resolve()
        new_physical = physical.with_name("hwmon88")
        physical.rename(new_physical)
        old.unlink()
        old.mkdir()
        (old / "name").write_text("amdgpu")
        (old / "pwm1_enable").write_text("1")
        new = old.with_name("hwmon88")
        new.symlink_to(new_physical)
        hardware.cpu.unlink()
        hardware.automatic()
        self.assertEqual((new / "pwm1_enable").read_text(), "2")
        self.assertEqual((old / "pwm1_enable").read_text(), "1")


if __name__ == "__main__":
    unittest.main(verbosity=2)
