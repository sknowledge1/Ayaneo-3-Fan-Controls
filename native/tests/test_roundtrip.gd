extends SceneTree

var _done: bool = false
var _error: String = ""
var _reply: Dictionary = {}


func _initialize() -> void:
	_run.call_deferred()


func _run() -> void:
	# Reapply the current user-selected configuration exactly as read.
	# No test mode/duty is selected, no services are stopped, and no cleanup write is needed.
	var args: PackedStringArray = OS.get_cmdline_user_args()
	if args.size() != 1 or not ProjectSettings.load_resource_pack(args[0]):
		quit(1)
		return
	var script: Script = load("res://plugins/ayaneo-fan-control/core/fan_client.gd")
	var client: Node = script.new()
	client.connect("request_failed", func(message: String) -> void:
		_error = message
		_done = true
	)
	client.connect("state_changed", func(state: Dictionary, operation: String) -> void:
		if operation == "configure":
			_reply = state.duplicate(true)
			_done = true
	)
	root.add_child(client)
	var deadline: int = Time.get_ticks_msec() + 6000
	while (client.get("last_state") as Dictionary).is_empty() and not _done and Time.get_ticks_msec() < deadline:
		await create_timer(0.1).timeout
	var state: Dictionary = client.get("last_state") as Dictionary
	if state.is_empty():
		_error = "Could not read current settings: " + _error
	else:
		var original: Dictionary = (state["config"] as Dictionary).duplicate(true)
		client.call("apply_configuration", original)
		deadline = Time.get_ticks_msec() + 6000
		while not _done and Time.get_ticks_msec() < deadline:
			await create_timer(0.1).timeout
		if not _done:
			_error = "Current-setting roundtrip timed out"
		elif _reply.get("config") != original:
			_error = "The returned settings differ from the current selection"
	client.call("shutdown")
	client.queue_free()
	await process_frame
	print(JSON.stringify({"existing_configuration_roundtrip": _error.is_empty(), "error": _error, "reply": _reply}))
	quit(0 if _error.is_empty() else 1)
