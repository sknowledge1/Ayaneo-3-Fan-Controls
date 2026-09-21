extends SceneTree


func _initialize() -> void:
	_run.call_deferred()


func _run() -> void:
	var args: PackedStringArray = OS.get_cmdline_user_args()
	if args.size() != 2 or not ProjectSettings.load_resource_pack(args[0]):
		quit(1)
		return
	var script: Script = load("res://plugins/ayaneo-fan-control/core/fan_client.gd")
	var client: Node = script.new()
	var configs: Array[Dictionary] = [
		{"mode": "manual", "percent": 0.0, "curve": [0.0, 10.0, 60.0, 80.0, 100.0]},
		{"mode": "curve", "percent": 15.0, "curve": [10.0, 30.0, 40.0, 70.0, 100.0]},
		{"mode": "quiet", "percent": 15.0, "curve": [10.0, 30.0, 40.0, 70.0, 100.0]},
	]
	var failures: Array[String] = []
	var checks: int = 0
	for config: Dictionary in configs:
		checks += 1
		var payload: String = script.call("encode_configuration", config)
		var result: Dictionary = client.call("_run_command", PackedStringArray([args[1], "--configure-base64", payload])) as Dictionary
		if not bool(result.get("ok", false)) or result.get("hardware_access") != false:
			failures.append(str(result))
		elif result["config"] != config:
			failures.append("Configuration changed during transport")
	checks += 1
	var legacy: Dictionary = script.call("normalize_response", {"ok": true, "config": configs[0]}) as Dictionary
	if not bool(legacy.get("ok", false)) or int(legacy.get("api_version", 0)) != 1:
		failures.append("A compatible v0.4 response was not accepted as protocol 1")
	checks += 1
	var future: Dictionary = script.call("normalize_response", {"ok": true, "api_version": 2, "config": configs[0]}) as Dictionary
	if bool(future.get("ok", true)) or not str(future.get("error", "")).contains("Unsupported"):
		failures.append("An unknown protocol was not rejected")
	checks += 1
	var malformed: Dictionary = script.call("normalize_response", {"ok": true, "config": {}}) as Dictionary
	if bool(malformed.get("ok", true)):
		failures.append("A malformed legacy response was not rejected")
	client.free()
	print(JSON.stringify({"native_transport_checks": checks, "hardware_access": false, "failures": failures}))
	quit(0 if failures.is_empty() else 1)
