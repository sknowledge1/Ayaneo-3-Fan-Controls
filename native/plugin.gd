extends Plugin

const FanClientScript := preload("res://plugins/ayaneo-fan-control/core/fan_client.gd")
const FanMenuScript := preload("res://plugins/ayaneo-fan-control/core/fan_menu.gd")
const FAN_ICON := preload("res://assets/ui/icons/performance_icon.svg")

var _client: FanClientScript
var _quick_menu: FanMenuScript
var _settings_menus: Array[WeakRef] = []
var _quick_card: Node


func _ready() -> void:
	_client = FanClientScript.new()
	_client.name = "FanClient"
	add_child(_client)
	_install_menu.call_deferred()


func _install_menu() -> void:
	if not is_inside_tree():
		return
	var quick_bar: Node = get_tree().get_first_node_in_group("quick-bar")
	if quick_bar == null:
		logger.warn("The stock quick-access bar is unavailable; fan settings remain accessible in plugin settings.")
		return
	_quick_menu = _new_menu()
	add_to_quick_bar(_quick_menu, FAN_ICON, _quick_menu)
	# The supported API wraps the menu in a card. Retain only our card for cleanup.
	var ancestor: Node = _quick_menu.get_parent()
	while ancestor != null and ancestor != quick_bar:
		if ancestor.get_parent() == quick_bar.get_node_or_null("%Viewport"):
			_quick_card = ancestor
			break
		ancestor = ancestor.get_parent()
	logger.info("Ayaneo 3 Fan Controls registered in the stock quick-access bar")


func _new_menu() -> FanMenuScript:
	var menu: FanMenuScript = FanMenuScript.new()
	menu.client = _client
	return menu


func get_settings_menu() -> Control:
	if _client == null:
		return null
	var menu: FanMenuScript = _new_menu()
	_settings_menus.append(weakref(menu))
	return menu


func unload() -> void:
	for menu_ref: WeakRef in _settings_menus:
		var menu: Node = menu_ref.get_ref() as Node
		if is_instance_valid(menu):
			menu.queue_free()
	_settings_menus.clear()
	if is_instance_valid(_quick_card):
		_quick_card.queue_free()
	elif is_instance_valid(_quick_menu):
		_quick_menu.queue_free()
	if is_instance_valid(_client):
		_client.shutdown()
		_client.queue_free()
