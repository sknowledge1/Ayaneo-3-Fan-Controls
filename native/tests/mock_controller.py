"""Transport fixture: validates payloads without reading or writing hardware."""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from ay3_fancontrol import decode_cli_config

parser = argparse.ArgumentParser()
parser.add_argument("--configure-base64", required=True)
args = parser.parse_args()
try:
    print(json.dumps({"ok": True, "config": decode_cli_config(args.configure_base64), "hardware_access": False}))
except ValueError as error:
    print(json.dumps({"ok": False, "error": str(error), "hardware_access": False}))
