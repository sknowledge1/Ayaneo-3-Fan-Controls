#!/usr/bin/env python3
"""AYANEO 3 fan control through the kernel hwmon interface; no raw EC access."""

import argparse
import base64
import copy
import fcntl
import json
import logging
import math
import os
from pathlib import Path
import signal
import socket
import socketserver
import sys
import time

VERSION = "0.3.0"
SOCKET = "/run/ay3-fancontrol/control.sock"
CONFIG = "/var/lib/ay3-fancontrol/config.json"
FULL_SPEED_C = 95
RECOVERY_C = 98
ANCHORS = [40, 55, 65, 75, FULL_SPEED_C]
QUIET_POINTS = [(45, 0), (55, 15), (65, 25), (75, 35), (85, 55), (90, 75), (FULL_SPEED_C, 100)]
STANDARD_FLOOR = [(45, 0), (55, 40), (65, 60), (75, 80), (FULL_SPEED_C, 100)]
MIN_DUTY = 0
MIN_RUNNING_DUTY = 10
DEFAULT = {"mode": "auto", "percent": 60, "curve": [40, 50, 70, 85, 100]}
LOG = logging.getLogger("ay3-fancontrol")


def read_int(path):
    return int(Path(path).read_text().strip())


def find_fan(root):
    root = Path(root)
    dmi = root / "sys/class/dmi/id"
    if (dmi / "board_vendor").read_text().strip() != "AYANEO" or (dmi / "board_name").read_text().strip() != "AYANEO 3":
        raise RuntimeError("This build is restricted to AYANEO 3")
    fan_root = (root / "sys/devices/platform/ayaneo-ec/hwmon").resolve()
    matches = []
    for directory in (root / "sys/class/hwmon").glob("hwmon*"):
        try:
            name = (directory / "name").read_text().strip()
        except OSError:
            continue
        if name == "ayaneo_ec" and directory.resolve().is_relative_to(fan_root):
            if all((directory / item).is_file() for item in ("pwm1", "pwm1_enable", "fan1_input")):
                matches.append(directory)
    if len(matches) != 1:
        raise RuntimeError("Expected exactly one AYANEO fan interface")
    return matches[0]


def validate_config(value):
    if not isinstance(value, dict) or set(value) != set(DEFAULT):
        raise ValueError("Expected mode, percent, and curve settings")
    if value["mode"] not in ("auto", "manual", "curve", "quiet"):
        raise ValueError("Unknown fan mode")
    numbers = [value["percent"]] + (value["curve"] if isinstance(value["curve"], list) else [])
    if len(numbers) != 6 or any(type(n) is not int or not MIN_DUTY <= n <= 100 for n in numbers):
        raise ValueError("Fan settings must be integer percentages from 0 to 100")
    curve = value["curve"]
    if curve != sorted(curve) or curve[-1] != 100:
        raise ValueError("The curve must rise with temperature and finish at 100%")
    return copy.deepcopy(value)


def decode_cli_config(encoded):
    if len(encoded) > 8192:
        raise ValueError("Configuration payload is too large")
    return validate_config(json.loads(base64.b64decode(encoded, validate=True).decode("utf8")))


def interpolate(points, temperature):
    if temperature <= points[0][0]:
        return float(points[0][1])
    for (t0, p0), (t1, p1) in zip(points, points[1:]):
        if temperature <= t1:
            return p0 + (p1 - p0) * (temperature - t0) / (t1 - t0)
    return float(points[-1][1])


def safety_floor(temperature, mode="manual"):
    # Quiet trades warmer operation for less noise. Both policies reach full duty
    # at 95 C, before recovery at 98 C and the 8840U's documented 100 C Tjmax.
    return interpolate(QUIET_POINTS if mode == "quiet" else STANDARD_FLOOR, temperature)


def save_config(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    with temporary.open("w") as stream:
        json.dump(value, stream, indent=2)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.chmod(temporary, 0o600)
    os.replace(temporary, path)


class Hardware:
    def __init__(self, root="/"):
        self.root = Path(root)
        self.fan = None
        self.cpu = None
        self.discover()

    def discover(self):
        self.fan = find_fan(self.root)
        if "AMD Ryzen 7 8840U" not in (self.root / "proc/cpuinfo").read_text():
            raise RuntimeError("The fan policy has only been validated on the 8840U model")
        cpus = []
        for directory in sorted((self.root / "sys/class/hwmon").glob("hwmon*")):
            name = (directory / "name").read_text().strip()
            if name == "k10temp" and (directory / "temp1_label").read_text().strip() == "Tctl":
                cpus.append(directory / "temp1_input")
        if len(cpus) != 1:
            raise RuntimeError("Expected exactly one CPU Tctl sensor")
        self.cpu = cpus[0]

    def sample(self):
        # Discovery on each tick also handles changed hwmon indices after resume.
        self.discover()
        temperature = read_int(self.cpu) / 1000
        if not math.isfinite(temperature) or not 5 <= temperature <= 110:
            raise RuntimeError("CPU temperature is unavailable or implausible")
        mode = read_int(self.fan / "pwm1_enable")
        # Firmware auto can leave a non-PWM value in this EC register (EIO on read).
        # Duty is only meaningful when the software owns manual mode.
        pwm = read_int(self.fan / "pwm1") if mode == 1 else None
        rpm = read_int(self.fan / "fan1_input")
        if mode not in (1, 2) or (pwm is not None and not 0 <= pwm <= 255) or not 0 <= rpm < 20000:
            raise RuntimeError("Fan telemetry is invalid")
        return {"cpu_c": temperature, "hardware_mode": mode, "pwm": pwm, "rpm": rpm}

    def automatic(self):
        # No temperature dependency: recovery must work when the CPU sensor fails.
        # Revalidate the path even when an old hwmon index still exists.
        self.fan = find_fan(self.root)
        (self.fan / "pwm1_enable").write_text("2")
        if read_int(self.fan / "pwm1_enable") != 2:
            raise RuntimeError("Firmware automatic mode could not be verified")

    def manual(self, percent):
        percent = max(MIN_DUTY, min(100, int(round(percent))))
        pwm = int(round(percent * 255 / 100))
        # This AYANEO driver accepts duty before manual mode; avoid a stale low duty.
        (self.fan / "pwm1").write_text(str(pwm))
        (self.fan / "pwm1_enable").write_text("1")
        if read_int(self.fan / "pwm1_enable") != 1 or abs(read_int(self.fan / "pwm1") - pwm) > 3:
            raise RuntimeError("Fan command readback did not match")
        return percent


class Controller:
    def __init__(self, hardware, config_path=CONFIG, clock=time.monotonic):
        self.hardware = hardware
        self.config_path = Path(config_path)
        self.clock = clock
        self.config = copy.deepcopy(DEFAULT)
        self.fault = None
        self.telemetry = None
        self.sampled_at = None
        self.last_duty = None
        self.last_tick = None
        self.manual_since = None
        self.stall_ticks = 0
        self.released = False
        self.hardware.automatic()
        self.released = True
        try:
            self.config = validate_config(json.loads(self.config_path.read_text()))
        except FileNotFoundError:
            pass
        except Exception as error:
            self.fault = "Invalid saved settings; using automatic control: " + str(error)

    def fail(self, reason):
        self.fault = str(reason)
        LOG.error("Fan control released: %s", reason)
        self.config["mode"] = "auto"
        self.last_duty = None
        self.manual_since = None
        self.stall_ticks = 0
        try:
            self.hardware.automatic()
            self.released = True
        except Exception as error:
            self.released = False
            self.fault += "; automatic recovery failed: " + str(error)
        save_config(self.config_path, self.config)

    def configure(self, value):
        value = validate_config(value)
        # A request cannot acquire manual control without valid current telemetry.
        if value["mode"] != "auto":
            sample = self.hardware.sample()
            if sample["cpu_c"] >= RECOVERY_C:
                raise ValueError("Device is too hot to acquire manual fan control")
            if sample["hardware_mode"] == 1 and self.config["mode"] == "auto":
                raise RuntimeError("Another fan controller appears to own the fan")
        previous = self.config
        self.config = value
        try:
            save_config(self.config_path, self.config)
        except Exception:
            self.config = previous
            raise
        self.fault = None
        self.last_duty = None
        self.last_tick = self.clock()
        self.manual_since = None
        self.stall_ticks = 0
        if value["mode"] == "auto":
            self.hardware.automatic()
            self.released = True
            self.manual_since = None
        self.tick()
        result = self.status()
        result["ok"] = self.fault is None
        return result

    def tick(self):
        now = self.clock()
        try:
            sample = self.hardware.sample()
            self.telemetry, self.sampled_at = sample, now
            if self.config["mode"] == "auto":
                # Do not repeatedly fight a separate controller while inactive.
                if not self.released:
                    self.hardware.automatic()
                    self.released = True
                self.last_tick = now
                return
            if self.last_tick is not None and now - self.last_tick > 5:
                raise RuntimeError("Controller sampling was interrupted")
            if sample["cpu_c"] >= RECOVERY_C:
                raise RuntimeError("CPU reached the automatic-recovery temperature")
            if self.manual_since is not None and sample["hardware_mode"] != 1:
                raise RuntimeError("Fan ownership changed; automatic control restored")
            if self.manual_since is not None and now - self.manual_since > 5 and self.last_duty is not None and self.last_duty > 0:
                self.stall_ticks = self.stall_ticks + 1 if sample["rpm"] < 300 else 0
                if self.stall_ticks >= 2:
                    raise RuntimeError("Fan rotation could not be confirmed")
            else:
                self.stall_ticks = 0
            mode = self.config["mode"]
            floor = safety_floor(sample["cpu_c"], mode)
            if mode == "quiet":
                requested = floor
            elif mode == "manual":
                requested = self.config["percent"]
            else:
                requested = interpolate(list(zip(ANCHORS, self.config["curve"])), sample["cpu_c"])
            target = max(requested, floor)
            stop_requested = target == 0
            # A stopped fan restarts above 45 C. Keep it running until <=42 C
            # to avoid cycling around that boundary.
            if stop_requested and self.last_duty is not None and self.last_duty > 0 and sample["cpu_c"] > 42:
                target = MIN_RUNNING_DUTY
            if self.last_duty is not None and mode in ("curve", "quiet"):
                target = max(target, self.last_duty - 3)
            if 0 < target < MIN_RUNNING_DUTY:
                target = 0 if stop_requested and sample["cpu_c"] <= 42 else MIN_RUNNING_DUTY
            restarting = self.last_duty == 0 and target > 0
            if self.last_duty is None or abs(target - self.last_duty) >= 1 or floor > self.last_duty:
                self.last_duty = self.hardware.manual(target)
            if self.manual_since is None or restarting:
                self.manual_since = now
                self.stall_ticks = 0
            self.released = False
            self.last_tick = now
            self.telemetry = self.hardware.sample()
        except Exception as error:
            self.telemetry = None
            self.sampled_at = None
            self.fail(error)

    def status(self):
        age = None if self.sampled_at is None else self.clock() - self.sampled_at
        return {"ok": True, "version": VERSION, "config": copy.deepcopy(self.config),
                "anchors": ANCHORS, "quiet_points": copy.deepcopy(QUIET_POINTS),
                "full_speed_c": FULL_SPEED_C, "recovery_c": RECOVERY_C,
                "minimum_percent": MIN_DUTY,
                "minimum_running_percent": MIN_RUNNING_DUTY, "fault": self.fault,
                "telemetry": self.telemetry if age is not None and age < 5 else None,
                "sample_age_s": age, "effective_percent": self.last_duty,
                "automatic_verified": bool(age is not None and age < 5 and self.released and self.telemetry and self.telemetry["hardware_mode"] == 2)}

    def close(self):
        self.hardware.automatic()


def notify(message):
    address = os.environ.get("NOTIFY_SOCKET")
    if address:
        if address.startswith("@"):
            address = "\0" + address[1:]
        with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as sock:
            sock.connect(address)
            sock.sendall(message.encode())


def request(value, socket_path=SOCKET):
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
        sock.settimeout(3)
        sock.connect(socket_path)
        sock.sendall(json.dumps(value).encode() + b"\n")
        response = sock.makefile("rb").readline(16384)
    return json.loads(response)


class Handler(socketserver.StreamRequestHandler):
    def handle(self):
        self.connection.settimeout(1)
        try:
            line = self.rfile.readline(4097)
            if len(line) > 4096 or not line.endswith(b"\n"):
                raise ValueError("Invalid request size")
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError("Expected an object")
            if value == {"operation": "status"}:
                response = self.server.controller.status()
            elif set(value) == {"operation", "config"} and value["operation"] == "configure":
                response = self.server.controller.configure(value["config"])
            else:
                raise ValueError("Unknown operation")
        except Exception as error:
            response = {"ok": False, "error": str(error)}
        try:
            self.wfile.write(json.dumps(response).encode() + b"\n")
        except (OSError, TimeoutError):
            pass


def serve():
    os.umask(0o077)
    Path(SOCKET).parent.mkdir(parents=True, exist_ok=True)
    with open(str(Path(SOCKET).parent / "owner.lock"), "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        hardware = Hardware()
        if read_int(hardware.fan / "pwm1_enable") != 2:
            raise RuntimeError("Fan is already in manual mode; refusing a second owner")
        (Path(SOCKET).parent / "owned").write_text("AY3 Fan Control\n")
        controller = Controller(hardware)
        Path(SOCKET).unlink(missing_ok=True)
        stopping = False

        def stop(_signal, _frame):
            nonlocal stopping
            stopping = True

        signal.signal(signal.SIGTERM, stop)
        signal.signal(signal.SIGINT, stop)
        try:
            with socketserver.UnixStreamServer(SOCKET, Handler) as server:
                server.controller = controller
                server.timeout = 0.25
                os.chmod(SOCKET, 0o660)
                controller.tick()
                notify("READY=1")
                next_tick = time.monotonic() + 1
                while not stopping:
                    server.handle_request()
                    if time.monotonic() >= next_tick:
                        controller.tick()
                        notify("WATCHDOG=1")
                        next_tick = time.monotonic() + 1
        finally:
            controller.close()
            Path(SOCKET).unlink(missing_ok=True)


def restore_after_stop():
    # Discover only the verified fan identity; this path cannot depend on a sensor.
    owned = Path(SOCKET).parent / "owned"
    if not owned.exists():
        return
    fan = find_fan("/")
    (fan / "pwm1_enable").write_text("2")
    if read_int(fan / "pwm1_enable") != 2:
        raise RuntimeError("Automatic recovery failed")
    if os.environ.get("SERVICE_RESULT", "success") != "success":
        try:
            config = validate_config(json.loads(Path(CONFIG).read_text()))
        except Exception:
            config = copy.deepcopy(DEFAULT)
        config["mode"] = "auto"
        save_config(CONFIG, config)
    owned.unlink(missing_ok=True)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    parser = argparse.ArgumentParser()
    parser.add_argument("--restore-auto", action="store_true")
    parser.add_argument("--status", action="store_true")
    parser.add_argument("--configure", help="Complete fan settings as JSON")
    parser.add_argument("--configure-base64", help="Base64 JSON for clients whose process API consumes quotes")
    args = parser.parse_args()
    if args.restore_auto:
        restore_after_stop()
    elif args.status:
        print(json.dumps(request({"operation": "status"}), indent=2))
    elif args.configure:
        print(json.dumps(request({"operation": "configure", "config": json.loads(args.configure)}), indent=2))
    elif args.configure_base64:
        print(json.dumps(request({"operation": "configure", "config": decode_cli_config(args.configure_base64)}), indent=2))
    else:
        serve()
