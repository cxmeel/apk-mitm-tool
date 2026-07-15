import json
import os

CONFIG_FILE = "config.json"

DEFAULT_CONFIG = {
    "show_system_apps": False,
    "custom_certificate_path": "",
    "maps_api_keys": {},  # Format: {"Display Name": "API_KEY_STRING"}
    "selected_maps_api_key_name": "",
    "wait_for_manual_changes": False
}

def load_config():
    if not os.path.exists(CONFIG_FILE):
        return DEFAULT_CONFIG.copy()
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # Merge with defaults to ensure all keys exist
            config = DEFAULT_CONFIG.copy()
            config.update(data)
            return config
    except Exception:
        return DEFAULT_CONFIG.copy()

def save_config(config):
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4)
    except Exception as e:
        print(f"Error saving config: {e}")
