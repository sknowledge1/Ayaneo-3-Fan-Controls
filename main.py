import asyncio
import json
import socket


def exchange(operation, config=None):
    message = {"operation": operation}
    if config is not None:
        message["config"] = config
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
            client.settimeout(3)
            client.connect("/run/ay3-fancontrol/control.sock")
            client.sendall(json.dumps(message).encode() + b"\n")
            return json.loads(client.makefile("rb").readline(16384))
    except Exception as error:
        return {"ok": False, "error": "Fan service unavailable: " + str(error)}


class Plugin:
    async def _main(self):
        pass

    async def _unload(self):
        # The supervised service owns the loop; menu/plugin reloads do not interrupt it.
        pass

    async def get_status(self):
        return await asyncio.to_thread(exchange, "status")

    async def set_config(self, config: dict):
        return await asyncio.to_thread(exchange, "configure", config)
