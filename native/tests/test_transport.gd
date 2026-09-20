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
	for config: Dictionary in configs:
		var payload: String = script.call("encode_configuration", config)
		var result: Dictionary = client.call("_run_command", PackedStringArray([args[1], "--configure-base64", payload])) as Dictionary
		if not bool(result.get("ok", false)) or result.get("hardware_access") != false:
			failures.append(str(result))
		elif result["config"] != config:
			failures.append("Configuration changed during transport")
	client.free()
	print(JSON.stringify({"native_transport_checks": configs.size(), "hardware_access": false, "failures": failures}))
	quit(0 if failures.is_empty() else 1)
