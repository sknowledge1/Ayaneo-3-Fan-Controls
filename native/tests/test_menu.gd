extends SceneTree

var _failures: Array[String] = []
var _checks: int = 0

class QuickBarFixture:
	extends VBoxContainer
	var menu_count: int = 0

	func add_child_menu(menu: Control, _icon: Texture2D, _focus: Control = null) -> void:
		menu_count += 1
		add_child(menu)


func _initialize() -> void:
	_run.call_deferred()


func _check(condition: bool, message: String) -> void:
	_checks += 1
	if not condition:
		_failures.append(message)
		push_error(message)


func _run() -> void:
	var arguments: PackedStringArray = OS.get_cmdline_user_args()
	_check(arguments.size() == 1, "Pass the native plugin ZIP")
	if arguments.is_empty():
		quit(1)
		return
	_check(ProjectSettings.load_resource_pack(arguments[0]), "ZIP loads as a Godot resource pack")
	var client_script: Script = load("res://plugins/ayaneo-fan-control/core/fan_client.gd")
	var menu_script: Script = load("res://plugins/ayaneo-fan-control/core/fan_menu.gd")
	_check(client_script != null and menu_script != null, "Native scripts compile")
	if client_script == null or menu_script == null:
		quit(1)
		return
	var client: Node = client_script.new()
	var menu: VBoxContainer = menu_script.new()
	_check(menu.find_child("SectionLabel") != null, "The stock Quick Bar can discover the owned section title")
	menu.set("client", client)
	root.add_child(menu)
	await process_frame
	var state: Dictionary = {
		"ok": true,
		"config": {"mode": "auto", "percent": 60, "curve": [40, 50, 70, 85, 100]},
		"telemetry": {"cpu_c": 42.5, "hardware_mode": 2, "rpm": 2100},
		"effective_percent": null,
		"fault": null,
		"quiet_points": [[45, 0], [55, 15], [65, 25], [75, 35], [85, 55], [90, 75], [95, 100]],
	}
	client.emit_signal("state_changed", state, "status")
	_check((menu.get("_telemetry") as Label).text.contains("2100 RPM"), "RPM is displayed")
	_check((menu.get("_mode_label") as Label).text.contains("automatic"), "Automatic mode is displayed")
	menu.call("_on_mode_selected", 1)
	menu.call("_on_manual_changed", 67.0)
	_check((menu.get("_config") as Dictionary)["percent"] == 67, "Manual slider updates the draft")
	_check((menu.get("_manual") as ValueSlider).min_value == 0, "The native manual slider permits zero")
	menu.call("_on_manual_changed", 0.0)
	_check((menu.get("_config") as Dictionary)["percent"] == 0, "A zero-percent draft is retained")
	client.emit_signal("state_changed", state, "status")
	_check((menu.get("_config") as Dictionary)["mode"] == "manual", "Polling preserves unapplied edits")
	menu.call("_on_mode_selected", 2)
	menu.call("_on_curve_changed", 80.0, 1)
	var curve: Array = (menu.get("_config") as Dictionary)["curve"]
	_check(curve == [40, 80, 80, 85, 100], "Curve edits remain monotonic with a full-speed endpoint")
	_check((menu.get("_curve_sliders") as Array).size() == 5, "Five native curve controls are present")
	_check(not ((menu.get("_curve_sliders") as Array)[4] as ValueSlider).editable, "High-temperature endpoint is fixed")
	_check(((menu.get("_curve_sliders") as Array)[4] as ValueSlider).text.begins_with("95 °C"), "The full-speed endpoint is 95 C")
	menu.call("_on_mode_selected", 3)
	_check((menu.get("_config") as Dictionary)["mode"] == "quiet", "Quiet can be selected")
	_check((menu.get("_config") as Dictionary)["curve"] == curve, "Quiet preserves the custom curve")
	_check((menu.get("_quiet") as Label).visible and not (menu.get("_curve_box") as VBoxContainer).visible, "Quiet shows its preview instead of custom sliders")
	_check((menu.get("_quiet") as Label).text.contains("85 °C: 55%"), "Quiet displays the backend-owned curve")
	client.emit_signal("state_changed", state, "status")
	_check((menu.get("_config") as Dictionary)["mode"] == "quiet", "Polling preserves a pending Quiet selection")
	var quiet_state: Dictionary = state.duplicate(true)
	quiet_state["config"]["mode"] = "quiet"
	quiet_state["telemetry"]["hardware_mode"] = 1
	quiet_state["effective_percent"] = 15
	menu.set("_awaiting_apply", true)
	client.emit_signal("state_changed", quiet_state, "configure")
	_check((menu.get("_mode_label") as Label).text == "Quiet — 15% duty", "The active Quiet profile is identified")
	_check(not bool(menu.get("_dirty")), "Applying Quiet clears the pending state")
	menu.set("_awaiting_apply", true)
	client.emit_signal("state_changed", state, "configure")
	_check(not bool(menu.get("_dirty")), "An applied response clears the pending state")
	client.emit_signal("request_failed", "Service unavailable")
	_check((menu.get("_apply") as Button).disabled, "Missing service disables applying")
	_check((menu.get("_message") as Label).text == "Service unavailable", "Missing service is explained")
	client.emit_signal("state_changed", state, "status")
	_check(not (menu.get("_automatic") as Button).disabled, "Automatic control becomes available after reconnection")
	menu.queue_free()
	await process_frame
	client.free()
	var stock_quick_script: Script = load("res://core/ui/card_ui/quick_bar/quick_bar_menu.gd")
	var stock_quick: Control = stock_quick_script.new()
	var stock_viewport: VBoxContainer = VBoxContainer.new()
	root.add_child(stock_viewport)
	stock_quick.set("viewport", stock_viewport)
	var stock_menu: VBoxContainer = menu_script.new()
	stock_quick.call("add_child_menu", stock_menu, load("res://assets/ui/icons/performance_icon.svg"), null)
	_check(stock_viewport.get_child_count() == 1, "The real stock Quick Bar implementation creates a card")
	if stock_viewport.get_child_count() == 1:
		_check(stock_viewport.get_child(0).get("title") == "Fan Controls", "The native card has the correct title")
	stock_viewport.queue_free()
	stock_quick.free()
	await process_frame
	var plugin_script: Script = load("res://plugins/ayaneo-fan-control/plugin.gd")
	_check(plugin_script != null, "The Plugin API entrypoint compiles")
	if plugin_script != null:
		var quick_bar: QuickBarFixture = QuickBarFixture.new()
		quick_bar.add_to_group("quick-bar")
		root.add_child(quick_bar)
		var plugin: Node = plugin_script.new()
		root.add_child(plugin)
		await process_frame
		await process_frame
		_check(quick_bar.menu_count == 1, "The plugin registers exactly one Quick Bar menu")
		var settings_menu: Control = plugin.call("get_settings_menu") as Control
		_check(settings_menu != null, "A stock plugin-settings menu is provided")
		settings_menu.free()
		plugin.call("unload")
		plugin.queue_free()
		quick_bar.queue_free()
		await process_frame
	print(JSON.stringify({"native_menu_checks": _checks, "failures": _failures}))
	quit(0 if _failures.is_empty() else 1)
