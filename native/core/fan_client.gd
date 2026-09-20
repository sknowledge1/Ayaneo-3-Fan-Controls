extends Node

signal state_changed(state: Dictionary, operation: String)
signal request_failed(message: String)
signal busy_changed(busy: bool)

const CONTROLLER_PATH := "/var/lib/ay3-fancontrol/app/ay3_fancontrol.py"
const PACKAGED_CONTROLLER_PATH := "/usr/libexec/ay3-fancontrol"

var last_state: Dictionary = {}
var _thread: Thread = Thread.new()
var _operation: String = "status"
var _queued_config: Variant = null
var _poll_timer: Timer
var _stopping: bool = false


func _ready() -> void:
	_poll_timer = Timer.new()
	_poll_timer.wait_time = 2.0
	_poll_timer.timeout.connect(poll)
	add_child(_poll_timer)
	_poll_timer.start()
	poll()


func poll() -> void:
	if _stopping or _thread.is_started():
		return
	_start_request("status", PackedStringArray([controller_path(), "--status"]))


static func controller_path() -> String:
	# Distribution packages keep executable code in the immutable /usr tree.
	return PACKAGED_CONTROLLER_PATH if FileAccess.file_exists(PACKAGED_CONTROLLER_PATH) else CONTROLLER_PATH


func apply_configuration(config: Dictionary) -> void:
	if _stopping:
		return
	_queued_config = config.duplicate(true)
	if not _thread.is_started():
		_start_queued_config()


static func encode_configuration(config: Dictionary) -> String:
	# Godot parses JSON numbers as floats; preserve the backend's integer contract.
	var curve: Array[int] = []
	for value: Variant in config.get("curve", []):
		curve.append(int(value))
	var normalized: Dictionary = {"mode": str(config.get("mode", "auto")), "percent": int(config.get("percent", 60)), "curve": curve}
	return Marshalls.utf8_to_base64(JSON.stringify(normalized))


func _start_queued_config() -> void:
	if not _queued_config is Dictionary:
		return
	var config: Dictionary = _queued_config as Dictionary
	_queued_config = null
	# Godot's process API can consume embedded JSON quotes on this platform.
	var payload: String = encode_configuration(config)
	_start_request("configure", PackedStringArray([controller_path(), "--configure-base64", payload]))


func _start_request(operation: String, arguments: PackedStringArray) -> void:
	_operation = operation
	busy_changed.emit(operation == "configure")
	var error: Error = _thread.start(_run_command.bind(arguments))
	if error != OK:
		busy_changed.emit(false)
		request_failed.emit("Could not start the fan-service request.")


func _run_command(arguments: PackedStringArray) -> Dictionary:
	# The existing Python client has a bounded Unix-socket timeout. Run it off the UI thread.
	var output: Array = []
	var exit_code: int = OS.execute("/usr/bin/python3", arguments, output, true, false)
	if exit_code != 0 or output.is_empty():
		printerr("AY3 fan client command failed: ", exit_code, " ", output)
		return {"ok": false, "error": "Fan service unavailable. Install or start the Ayaneo fan backend."}
	var decoded: Variant = JSON.parse_string(str(output[0]))
	if not decoded is Dictionary:
		return {"ok": false, "error": "The fan service returned an invalid response."}
	return decoded as Dictionary


func _process(_delta: float) -> void:
	if not _thread.is_started() or _thread.is_alive():
		return
	var result: Dictionary = _thread.wait_to_finish() as Dictionary
	busy_changed.emit(false)
	if bool(result.get("ok", false)):
		last_state = result.duplicate(true)
		state_changed.emit(last_state, _operation)
	else:
		request_failed.emit(str(result.get("error", result.get("fault", "The fan command failed."))))
	if _queued_config is Dictionary and not _stopping:
		_start_queued_config()


func shutdown() -> void:
	_stopping = true
	_queued_config = null
	if is_instance_valid(_poll_timer):
		_poll_timer.stop()
	if _thread.is_started():
		_thread.wait_to_finish()


func _exit_tree() -> void:
	shutdown()
