extends SceneTree

var _failures: Array[String] = []
var _checks: int = 0


func _initialize() -> void:
	_run.call_deferred()


func _check(condition: bool, message: String) -> void:
	_checks += 1
	if not condition:
		_failures.append(message)
		push_error(message)


func _run() -> void:
	var args: PackedStringArray = OS.get_cmdline_user_args()
	if args.size() != 1:
		quit(1)
		return
	_check(OS.get_user_data_dir().contains("ogui-test-data"), "Tests use isolated OGUI user data")
	if not _failures.is_empty():
		quit(1)
		return
	var loader: PluginLoader = PluginLoader.new()
	var metadata: Dictionary = loader.call("_load_plugin_meta", args[0])
	var selected: Array[String] = loader.filter_by_tag({metadata["plugin.id"]: metadata}, "quick-bar")
	_check("ayaneo-fan-control" in selected, "The real Steam-overlay plugin filter includes Fan Controls")
	_check(ProjectSettings.load_resource_pack(args[0]), "The native resource pack loads")
	var menu_script: Script = load("res://plugins/ayaneo-fan-control/core/fan_menu.gd")
	var menu: Control = menu_script.new()
	# Use the actual stock card implementation without starting Steam or power tools.
	var quick_script: Script = load("res://core/ui/card_ui/quick_bar/quick_bar_menu.gd")
	var quick_bar: Control = quick_script.new()
	var viewport: VBoxContainer = VBoxContainer.new()
	viewport.custom_minimum_size = Vector2(540, 600)
	root.add_child(viewport)
	quick_bar.set("viewport", viewport)
	quick_bar.call("add_child_menu", menu, load("res://assets/ui/icons/performance_icon.svg"), menu)
	await process_frame
	var card: Control = viewport.get_child(0) as Control
	_check(card.is_visible_in_tree() and card.get("title") == "Fan Controls", "The stock card has a visible Fan Controls header")
	menu.call("_on_state_changed", {
		"config": {"mode": "quiet", "percent": 15, "curve": [10, 30, 40, 70, 100]},
		"telemetry": {"cpu_c": 55.0, "rpm": 1200, "hardware_mode": 1},
		"effective_percent": 15, "fault": null,
	}, "status")
	_check(card.get("focus_group") != null, "The stock card discovers a controller focus group")
	card.grab_focus()
	card.call("_on_button_up")
	await create_timer(0.6).timeout
	_check(menu.is_visible_in_tree(), "Expanding the stock card reveals the fan menu")
	var focused: Control = root.gui_get_focus_owner()
	_check(focused != null and menu.is_ancestor_of(focused), "Expanding the card focuses a fan control")
	menu.call("_on_mode_selected", 2)
	var curve_controls: Control = menu.get("_curve_box") as Control
	curve_controls.grab_focus()
	await process_frame
	await process_frame
	focused = root.gui_get_focus_owner()
	_check(focused != null and curve_controls.is_ancestor_of(focused), "Controller focus enters the custom curve sliders")
	viewport.queue_free()
	quick_bar.free()
	await process_frame
	print(JSON.stringify({"overlay_checks": _checks, "hardware_access": false, "failures": _failures}))
	quit(0 if _failures.is_empty() else 1)
