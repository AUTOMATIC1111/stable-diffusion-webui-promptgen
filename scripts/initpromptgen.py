
from modules import scripts, script_callbacks, devices, ui
from scripts.promptgen import add_tab, on_ui_settings, on_unload


script_callbacks.on_ui_tabs(add_tab)
script_callbacks.on_ui_settings(on_ui_settings)
script_callbacks.on_script_unloaded(on_unload)
