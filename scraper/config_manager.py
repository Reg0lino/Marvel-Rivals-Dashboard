# File: config_manager.py
import json
import os
import datetime
from tkinter import messagebox # For error popups if save_config_json is called directly

# --- Directories needed by this module ---
# Assuming this script is in the same directory as updater_v3.py
# If not, these paths would need to be passed in or configured more robustly.
SCRIPT_DIR_CM = os.path.dirname(os.path.abspath(__file__)) # CM for ConfigManager
BASE_DIR_CM = os.path.abspath(os.path.join(SCRIPT_DIR_CM, os.pardir))
CONFIG_DIR_CM = os.path.join(BASE_DIR_CM, "config")

# --- Files (relative to SCRIPT_DIR_CM or CONFIG_DIR_CM as appropriate) ---
URL_DATA_FILE_CM = os.path.join(SCRIPT_DIR_CM, 'saved_character_urls.json')
SETTINGS_FILE_CM = os.path.join(SCRIPT_DIR_CM, 'updater_settings.json')
# CHAR_IMG_CONFIG and CHAR_ICON_CONFIG are just filenames, directory is CONFIG_DIR_CM

# --- Character URL Persistence ---
def load_character_urls():
    """Loads character URLs from the dedicated JSON file."""
    character_urls_local = {}
    try:
        if os.path.exists(URL_DATA_FILE_CM):
            with open(URL_DATA_FILE_CM, 'r', encoding='utf-8') as f:
                loaded_data = json.load(f)
                if isinstance(loaded_data, dict):
                    character_urls_local = loaded_data
                    print(f"CM: Loaded URLs for {len(character_urls_local)} characters from {os.path.basename(URL_DATA_FILE_CM)}")
                else:
                    print(f"CM ERROR: Invalid format in {os.path.basename(URL_DATA_FILE_CM)}. Expected dict.")
        else:
            print(f"CM: {os.path.basename(URL_DATA_FILE_CM)} not found. Starting with empty URL list.")
    except json.JSONDecodeError as e:
        print(f"CM Error loading {os.path.basename(URL_DATA_FILE_CM)}: Invalid JSON - {e}")
    except Exception as e:
        print(f"CM Error loading {os.path.basename(URL_DATA_FILE_CM)}: {e}.")
    return character_urls_local

def save_character_urls(urls_to_save):
    """Saves character URLs to the dedicated JSON file."""
    if not isinstance(urls_to_save, dict):
        print("CM ERROR: URLs data to save must be a dictionary.")
        return False
    try:
        with open(URL_DATA_FILE_CM, 'w', encoding='utf-8') as f:
            json.dump(urls_to_save, f, indent=4, ensure_ascii=False)
        print(f"CM: Saved URLs to {os.path.basename(URL_DATA_FILE_CM)}")
        return True
    except Exception as e:
        print(f"CM Error saving URLs: {e}")
        # messagebox.showerror("Save Error", f"Could not save URLs.\n{e}") # Avoid direct Tkinter in non-GUI module if possible
        return False

# --- UI Settings Persistence ---
def load_ui_settings():
    """Loads UI settings (like selected models) from the settings file."""
    # DEFAULT_MODEL and AVAILABLE_MODELS would ideally be passed or accessed from a central config
    # For now, we'll assume they might be needed contextually by the caller.
    # This function will just return the raw loaded settings.
    settings_data = {}
    try:
        if os.path.exists(SETTINGS_FILE_CM):
            with open(SETTINGS_FILE_CM, 'r', encoding='utf-8') as f:
                settings_data = json.load(f)
            print(f"CM: Loaded UI settings from {os.path.basename(SETTINGS_FILE_CM)}")
    except Exception as e:
        print(f"CM Error loading UI settings from {os.path.basename(SETTINGS_FILE_CM)}: {e}.")
    return settings_data # Return dict, could be empty

def save_ui_settings(settings_data_to_save):
    """Saves UI settings to the settings file."""
    if not isinstance(settings_data_to_save, dict):
        print("CM ERROR: UI settings data to save must be a dictionary.")
        return False
    try:
        with open(SETTINGS_FILE_CM, 'w', encoding='utf-8') as f:
            json.dump(settings_data_to_save, f, indent=4)
        print(f"CM: Saved UI settings to {os.path.basename(SETTINGS_FILE_CM)}")
        return True
    except Exception as e:
        print(f"CM Error saving UI settings to {os.path.basename(SETTINGS_FILE_CM)}: {e}")
        # messagebox.showerror("Settings Save Error", f"Could not save settings.\n{e}")
        return False

# --- Generic Config File Helpers (for character_images.json, character_icons.json) ---
def load_generic_config(filename):
    """Loads a generic JSON config file from the standard config directory."""
    filepath = os.path.join(CONFIG_DIR_CM, filename)
    data = {}
    try:
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read().strip()
            if not content:
                print(f"CM WARN: Config empty: {filepath}.")
                return {}
            if not content.startswith('{'): # Basic JSON check
                print(f"CM ERROR: Config not JSON: {filepath}.")
                return {}
            data = json.loads(content)
        else:
            print(f"CM WARN: Config not found: {filepath}.")
    except json.JSONDecodeError as e:
        print(f"CM ERROR: Invalid JSON in config: {filepath} - {e}.")
    except Exception as e:
        print(f"CM ERROR: Failed load config {filepath}: {e}.")
    return data

def save_generic_config(data_to_save, filename):
    """Saves data to a generic JSON config file in the standard config directory."""
    if not isinstance(data_to_save, dict):
        print(f"CM ERROR: Data for {filename} must be a dictionary.")
        return False
    filepath = os.path.join(CONFIG_DIR_CM, filename)
    try:
        os.makedirs(CONFIG_DIR_CM, exist_ok=True) # Ensure config dir exists
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data_to_save, f, indent=4, ensure_ascii=False)
        print(f"CM: Saved config file: {filepath}")
        return True
    except Exception as e:
        print(f"CM ERROR: Failed save config {filepath}: {e}")
        # messagebox.showerror("Config Save Error", f"Could not save:\n{filename}\n{e}") # Avoid Tkinter
        return False

# --- Helper to Update Last Update Info ---
def update_last_update_file(update_key, value):
    """Reads last_update.json from config, updates a key, and saves it back."""
    filepath = os.path.join(CONFIG_DIR_CM, 'last_update.json')
    data = {}
    try:
        os.makedirs(CONFIG_DIR_CM, exist_ok=True)
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                try:
                    data = json.load(f)
                    if not isinstance(data, dict):
                        print(f"CM Warning: Invalid content in {os.path.basename(filepath)}. Resetting.")
                        data = {}
                except json.JSONDecodeError:
                    print(f"CM Warning: Corrupt JSON in {os.path.basename(filepath)}. Resetting.")
                    data = {}
        data[update_key] = value
        print(f"CM: Updating '{update_key}' in {os.path.basename(filepath)} to '{value}'")
        with open(filepath, 'w', encoding='utf-8') as f_out:
            json.dump(data, f_out, indent=2)
    except Exception as e:
        print(f"CM ERROR: Failed to update {os.path.basename(filepath)}: {e}")

if __name__ == '__main__':
    # Simple test cases if you run this file directly
    print("Testing config_manager.py...")
    test_urls = {"CharacterA": ["http://example.com/a"], "CharacterB": ["http://example.com/b"]}
    save_character_urls(test_urls)
    loaded_urls = load_character_urls()
    print(f"Loaded URLs: {loaded_urls}")

    test_settings = {"selected_model": "gemini-pro", "tune_model": "gemini-flash"}
    save_ui_settings(test_settings)
    loaded_settings = load_ui_settings()
    print(f"Loaded Settings: {loaded_settings}")

    test_img_config = {"CharacterA": "img_a.png"}
    save_generic_config(test_img_config, "character_images.json_test") # Use test extension
    loaded_img_config = load_generic_config("character_images.json_test")
    print(f"Loaded Image Config: {loaded_img_config}")

    update_last_update_file("test_update", datetime.datetime.now().isoformat())
    print("Testing complete.")