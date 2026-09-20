extends VBoxContainer

const FanClientScript := preload("res://plugins/ayaneo-fan-control/core/fan_client.gd")
const SLIDER_SCENE := preload("res://core/ui/components/slider.tscn")
const DROPDOWN_SCENE := preload("res://core/ui/components/dropdown.tscn")
const BUTTON_SCENE := preload("res://core/ui/components/button.tscn")
const MODES: Array[String] = ["auto", "manual", "curve", "quiet"]
const ANCHORS: Array[int] = [40, 55, 65, 75, 95]
const QUICK_BAR_FOCUS := preload("res://core/ui/card_ui/quick_bar/quick_bar_menu_focus.tres")

var client: FanClientScript
var _config: Dictionary = {"mode": "auto", "percent": 60, "curve": [40, 50, 70, 85, 100]}
var _dirty: bool = false
var _updating: bool = false
var _awaiting_apply: bool = false
var _connected: bool = false
var _busy: bool = false
var _telemetry: Label
var _mode_label: Label
var _message: Label
var _mode: Dropdown
var _manual: ValueSlider
var _curve_box: VBoxContainer
var _quiet: Label
var _curve_sliders: Array[ValueSlider] = []
var _focus_group: FocusGroup
var _curve_focus: FocusGroup
var _apply: Button
var _automatic: Button


func _init() -> void:
	name = "AyaneoFanMenu"
	size_flags_horizontal = Control.SIZE_EXPAND_FILL
	focus_mode = Control.FOCUS_ALL
	# The Quick Bar API reads this title before the menu enters the scene tree.
	var section: Label = Label.new()
	section.name = "SectionLabel"
	section.text = "Fan Controls"
	add_child(section)
	section.owner = self


func _ready() -> void:
	add_theme_constant_override("separation", 12)
	_telemetry = _label("Waiting for fan telemetry…")
	_mode_label = _label("AYANEO 3")
	_mode = DROPDOWN_SCENE.instantiate() as Dropdown
	_mode.title = "Fan mode"
	add_child(_mode)
	_mode.add_item("Automatic")
	_mode.add_item("Manual")
	_mode.add_item("Custom curve")
	_mode.add_item("Quiet")
	_mode.item_selected.connect(_on_mode_selected)
	_manual = _slider("Fan duty (%)", 60)
	_manual.value_changed.connect(_on_manual_changed)
	_curve_box = VBoxContainer.new()
	_curve_box.add_theme_constant_override("separation", 10)
	add_child(_curve_box)
	for index: int in range(ANCHORS.size()):
		var slider: ValueSlider = SLIDER_SCENE.instantiate() as ValueSlider
		slider.text = "%d °C — fan duty (%%)" % ANCHORS[index]
		slider.min_value = 0
		slider.max_value = 100
		slider.step = 1
		slider.value = float((_config["curve"] as Array)[index])
		slider.editable = index != ANCHORS.size() - 1
		_curve_box.add_child(slider)
		slider.value_changed.connect(_on_curve_changed.bind(index))
		_curve_sliders.append(slider)
	_curve_focus = FocusGroup.new()
	_curve_focus.focus_stack = QUICK_BAR_FOCUS
	_curve_box.add_child(_curve_focus)
	_curve_box.focus_mode = Control.FOCUS_ALL
	_curve_box.focus_entered.connect(_curve_focus.grab_focus)
	_quiet = _label("Quiet allows warmer operation with a gentler fan curve, reaching full speed at 95 °C. Your custom curve is kept separately.")
	_apply = BUTTON_SCENE.instantiate() as Button
	_apply.text = "Apply changes"
	_apply.pressed.connect(_apply_changes)
	add_child(_apply)
	_automatic = BUTTON_SCENE.instantiate() as Button
	_automatic.text = "Restore automatic control"
	_automatic.pressed.connect(_restore_automatic)
	add_child(_automatic)
	_message = _label("")
	_label("0% allows a stop when cool. Nonzero output uses a 10% running floor. Full cooling starts at 95 °C; firmware recovery starts at 98 °C. Control continues with the menu closed.")
	# Stock cards discover this group and enter it after their expansion animation.
	_focus_group = FocusGroup.new()
	_focus_group.focus_stack = QUICK_BAR_FOCUS
	_focus_group.current_focus = _mode
	add_child(_focus_group)
	move_child(_focus_group, 0)
	focus_entered.connect(_focus_group.grab_focus)
	if client != null:
		client.state_changed.connect(_on_state_changed)
		client.request_failed.connect(_on_request_failed)
		client.busy_changed.connect(_on_busy_changed)
		if not client.last_state.is_empty():
			_on_state_changed(client.last_state, "status")
	_sync_editor()


func _label(text: String) -> Label:
	var label: Label = Label.new()
	label.text = text
	label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	label.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	add_child(label)
	return label


func _slider(text: String, value: int) -> ValueSlider:
	var slider: ValueSlider = SLIDER_SCENE.instantiate() as ValueSlider
	slider.text = text
	slider.min_value = 0
	slider.max_value = 100
	slider.step = 1
	slider.value = value
	add_child(slider)
	return slider


func _sync_editor() -> void:
	_updating = true
	_mode.select(maxi(0, MODES.find(str(_config["mode"]))))
	_manual.value = float(_config["percent"])
	for index: int in range(_curve_sliders.size()):
		_curve_sliders[index].value = float((_config["curve"] as Array)[index])
	_manual.visible = _config["mode"] == "manual"
	_curve_box.visible = _config["mode"] == "curve"
	_quiet.visible = _config["mode"] == "quiet"
	_mode.disabled = not _connected or _busy
	_apply.disabled = not _connected or not _dirty or _busy
	_automatic.disabled = not _connected or _busy
	_updating = false


func _on_mode_selected(index: int) -> void:
	if _updating or index < 0 or index >= MODES.size():
		return
	_config["mode"] = MODES[index]
	_mark_dirty()


func _on_manual_changed(value: float) -> void:
	if _updating:
		return
	_config["percent"] = roundi(value)
	_mark_dirty()


func _on_curve_changed(value: float, index: int) -> void:
	if _updating:
		return
	var curve: Array = (_config["curve"] as Array).duplicate()
	curve[index] = roundi(value)
	for lower: int in range(index):
		curve[lower] = mini(int(curve[lower]), int(curve[index]))
	for higher: int in range(index + 1, curve.size()):
		curve[higher] = maxi(int(curve[higher]), int(curve[index]))
	curve[curve.size() - 1] = 100
	_config["curve"] = curve
	_mark_dirty()


func _mark_dirty() -> void:
	_dirty = true
	_message.text = "Changes are waiting to be applied."
	_sync_editor()


func _apply_changes() -> void:
	if client == null or not _connected:
		return
	_awaiting_apply = true
	client.apply_configuration(_config)


func _restore_automatic() -> void:
	_config["mode"] = "auto"
	_dirty = true
	_apply_changes()


func _on_state_changed(state: Dictionary, operation: String) -> void:
	_connected = true
	var quiet_points: Variant = state.get("quiet_points")
	if quiet_points is Array:
		var points: PackedStringArray = []
		for point: Variant in quiet_points:
			if point is Array and point.size() == 2:
				points.append("%d °C: %d%%" % [int(point[0]), int(point[1])])
		_quiet.text = "Quiet allows warmer operation with less fan noise. Your custom curve is kept separately.\n" + " · ".join(points)
	var telemetry: Variant = state.get("telemetry")
	if telemetry is Dictionary:
		var sample: Dictionary = telemetry as Dictionary
		_telemetry.text = "Fan: %d RPM    CPU: %.1f °C" % [int(sample.get("rpm", 0)), float(sample.get("cpu_c", 0.0))]
		if int(sample.get("hardware_mode", 2)) == 2:
			_mode_label.text = "Firmware automatic control"
		else:
			var effective: Variant = state.get("effective_percent")
			var active_mode: String = str((state.get("config", {}) as Dictionary).get("mode", "manual"))
			var mode_name: String = {"quiet": "Quiet", "curve": "Custom curve"}.get(active_mode, "Manual control")
			_mode_label.text = "%s — %d%% duty" % [mode_name, int(effective)] if effective != null else "Another controller is using manual mode"
	else:
		_telemetry.text = "Fan telemetry unavailable"
		_mode_label.text = "Automatic recovery requested"
	if not _dirty or (operation == "configure" and _awaiting_apply):
		var config: Variant = state.get("config")
		if config is Dictionary:
			_config = (config as Dictionary).duplicate(true)
		_dirty = false
		_awaiting_apply = false
		_message.text = str(state.get("fault", "")) if state.get("fault") != null else ""
	_sync_editor()


func _on_request_failed(message: String) -> void:
	_connected = false
	_awaiting_apply = false
	_message.text = message
	_sync_editor()


func _on_busy_changed(busy: bool) -> void:
	_busy = busy
	_sync_editor()
