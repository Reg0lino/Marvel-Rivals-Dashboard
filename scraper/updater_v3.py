# -*- coding: utf-8 -*-
# Marvel Rivals Updater v3.1 - Modular Refactor

# ==============================================================================
# == IMPORTS ==
# ==============================================================================
from tkinter import ttk, messagebox, Listbox, Scrollbar, END, SINGLE, Text, Toplevel, Label, Entry, Frame, Button
import tkinter as tk
import os
import re # Keep for some minor GUI related regex if any, or schema string
import threading
import json # Keep for schema string or direct json ops if any remain
import time # Keep for main script delays if any
import sys
import io
import datetime
import subprocess # For opening files/dirs
# import shutil # Moved to config_manager or json_manager where file moves happen
# import functools # Moved to scraper_utils
# import urllib.parse # Moved to json_manager where it's used for reddit links

# --- Modular Imports ---
import config_manager
import scraper_utils
import ai_processor
import json_manager # This will contain the core processing logic

# --- Google AI Library (Check for main GUI, AI Processor handles actual use) ---
try:
    # import google.generativeai as genai # Not directly used in GUI layer
    # from google.api_core import exceptions as google_exceptions
    GOOGLE_AI_LIB_PRESENT = ai_processor.AI_GOOGLE_AI_AVAILABLE # Check via ai_processor
except AttributeError: # If ai_processor itself failed to import AI_GOOGLE_AI_AVAILABLE
    print("CRITICAL: ai_processor module not loaded correctly, cannot determine GOOGLE_AI_LIB_PRESENT.")
    GOOGLE_AI_LIB_PRESENT = False


# --- DotEnv (Check for main GUI, Config Manager handles actual use) ---
try:
    from dotenv import load_dotenv # Still useful for main script's environment
    DOTENV_PRESENT = True
except ImportError:
    print("WARNING: python-dotenv library not found. .env loading may be affected if used directly by updater_v3.")
    DOTENV_PRESENT = False
    def load_dotenv(): pass # Dummy

# --- Tab-Specific Instructions (Remains in GUI) ---
TAB_INSTRUCTIONS = {
    0: """Tab 1: Manage & Scrape
    1. Select Character: Choose a hero from the dropdown.
    2. Manage URLs: Add/Remove web page URLs used for scraping data for selected character.
    3. Scrape Raw Text: Click buttons to fetch raw text from saved URLs.
    4. Update Meta/Info/Teamups: Use dedicated buttons for these global updates.""",
    1: """Tab 2: Add Character
    1. Fill Form: Enter required (*) and optional details.
    2. Image/Icon Files: Provide FILENAMES. Place actual files in 'images' folder.
    3. Create Files: Generates base JSON, adds to configs.""",
    2: """Tab 3: Generate/Update JSON
    1. Select Character: Choose character for AI processing.
    2. Select AI Model: Choose AI model for generation.
    3. API Key: Ensure GOOGLE_API_KEY is in .env in 'scraper' folder.
    4. Generate: Creates/updates character JSON using AI, patches, and preserves sections.
    5. Cancel: Button appears during 'Generate ALL JSON'.""",
    3: """Tab 4: Fine-Tune JSON
    1. Select Character & Load JSON.
    2. Enter Instruction: Describe the AI change.
    3. Select Model & Preview: AI generates proposed update.
    4. Save/Discard: Apply or discard changes."""
}
DEFAULT_INSTRUCTION = "Select a tab to see instructions."

# --- Prompt template file helpers ---
def edit_api_prompt():
    prompt_file = ai_processor.AIP_API_PROMPT_TEMPLATE_FILE
    if os.path.exists(prompt_file):
        try:
            if os.name == "nt":
                subprocess.Popen(["notepad", prompt_file])
            else:
                subprocess.Popen(["open", prompt_file])
        except Exception as e:
            messagebox.showerror("Error", f"Could not open prompt file:\n{e}")
    else:
        messagebox.showerror("Error", f"Prompt template not found:\n{prompt_file}")

def open_prompt_directory():
    folder = ai_processor.AIP_SCRIPT_DIR
    if os.path.isdir(folder):
        try:
            if sys.platform.startswith("win"):
                os.startfile(folder)
            else:
                subprocess.Popen(["open", folder])
        except Exception as e:
            messagebox.showerror("Error", f"Could not open folder:\n{e}")
    else:
        messagebox.showerror("Error", f"Script directory not found:\n{folder}")

# ==============================================================================
# == CONFIGURATION & GLOBAL CONSTANTS (Main Script Specific) ==
# ==============================================================================
if DOTENV_PRESENT:
    load_dotenv() # Load .env for API_KEY for the whole application session

# --- Define the Schema in Python (Needed by ai_processor, passed via json_manager.init) ---
FINAL_JSON_SCHEMA_STRING_MAIN = """
{
  "name": "string",
  "role": "string | null",
  "stats": {
    "health": "number | string | null",
    "speed": "string | null",
    "difficulty": "string | null",
    "color_theme": "string | null",
    "color_theme_secondary": "string | null"
  },
  "abilities": [
    {
      "name": "string",
      "keybind": "string | null",
      "type": "string | null",
      "description": "string | null",
      "casting": "string | null",
      "damage": "string | null",
      "damage_falloff": "string | null",
      "fire_rate_interval": "string | null",
      "ammo": "string | number | null",
      "critical_hit": "boolean | null",
      "cooldown": "string | null",
      "range": "string | null",
      "projectile_speed": "string | null",
      "charges": "number | null",
      "duration": "string | null",
      "movement_boost": "string | null",
      "energy_cost_details": "string | null",
      "details": "string | null"
    }
  ],
  "ultimate": {
    "name": "string | null",
    "keybind": "string | null",
    "type": "string | null",
    "description": "string | null",
    "casting": "string | null",
    "damage": "string | null",
    "range": "string | null",
    "effect": "string | null",
    "duration": "string | null",
    "health_upon_revival": "string | null",
    "slow_rate": "string | null",
    "projectile_speed": "string | null",
    "movement_boost": "string | null",
    "bonus_health_details": "string | null",
    "energy_cost": "string | number | null",
    "details": "string | null"
  } | null,
  "passives": [
    {
      "name": "string",
      "keybind": "string | null",
      "type": "string | null",
      "description": "string | null",
      "cooldown": "string | null",
      "damage": "string | null",
      "range": "string | null",
      "trigger_condition": "string | null",
      "effect_boost": "string | null",
      "speed_details": "string | null",
      "details": "string | null"
    }
  ],
  "teamups": [
    {
      "name": "string | null",
      "keybind": "string | null",
      "partner": "list[string] | string | null",
      "effect": "string | null",
      "teamup_bonus": "string | null",
      "duration": "string | null",
      "cooldown": "string | null",
      "range_target": "string | null",
      "special_notes": "string | null",
      "details": "string | null"
    }
  ],
  "gameplay": {
    "strategy_overview": "string | null",
    "weaknesses": ["string"],
    "achievements": [
      {
        "icon": "string | null",
        "name": "string",
        "description": "string",
        "points": "string | number | null"
      }
    ]
  },
  "lore_details": {
    "ingame_bio_quote": "string | null",
    "ingame_bio_text": "string | null",
    "ingame_story_intro": "string | null",
    "hero_stories": [
      {
        "title": "string",
        "content": "string | null",
        "status": "string | null"
      }
    ],
    "balance_changes": [
      {
        "date_version": "string",
        "changes": ["string"]
      }
    ],
    "official_quote": "string | null",
    "official_description": "string | null"
  },
  "background": {
    "real_name": "string | null",
    "aliases": ["string"],
    "birthplace": "string | null",
    "birthdate": "string | null",
    "gender": "string | null",
    "eye_color": "string | null",
    "hair_color": "string | null",
    "relatives": ["string"],
    "affiliation": ["string"],
    "first_appearance_comic": "string | null",
    "recommended_comics": ["string"],
    "lore_powers_skills": ["string"]
  },
  "misc": {
    "voice_actor": "string | null",
    "quotes_link": "string | null",
    "community_buzz": "string | null",
    "helpful_links": [
      { "title": "string", "url": "string" }
    ]
  },
  "meta_stats": {
    "tier": "string | null",
    "win_rate": "string | null",
    "wr_change": "string | null",
    "pick_rate": "string | null",
    "pr_change": "string | null",
    "ban_rate": "string | null",
    "matches": "string | null"
  },
  "data_sources": {
    "wiki": ["string"],
    "tracker": ["string"],
    "comic_wiki": ["string"]
  }
}
"""
# Simplified schema structure, also passed to json_manager.init
SIMPLE_SCHEMA_STRUCTURE_MAIN = {
    "name": "string", "role": "string", "stats": "object", "abilities": "array",
    "ultimate": "object", "passives": "array", "teamups": "array", "gameplay": "object",
    "lore_details": "object", "background": "object", "misc": "object",
    "meta_stats": "object", "data_sources": "object"
}
# Top-level properties, derived from your schema, passed to json_manager.init
# (This should be the same as your TOP_LEVEL_SCHEMA_PROPERTIES from before)
TOP_LEVEL_SCHEMA_PROPERTIES_MAIN = {
    "name": {"type": "string"}, "role": {"type": "string"},
    "stats": {"type": "object", "properties": { "health": {"type": "any"}, "speed": {"type": "string"}, "difficulty": {"type": "string"}, "color_theme": {"type": "string"}, "color_theme_secondary": {"type": "string"}}},
    "abilities": {"type": "array", "items": {"type": "object", "properties": { "name": {"type": "string"}, "keybind": {"type": "string"}, "type": {"type": "string"}, "description": {"type": "string"}, "casting": {"type": "string"}, "damage": {"type": "string"}, "damage_falloff": {"type": "string"}, "fire_rate_interval": {"type": "string"}, "ammo": {"type": "any"}, "critical_hit": {"type": "boolean"}, "cooldown": {"type": "string"}, "range": {"type": "string"}, "projectile_speed": {"type": "string"}, "charges": {"type": "number"}, "duration": {"type": "string"}, "movement_boost": {"type": "string"}, "energy_cost_details": {"type": "string"}, "details": {"type": "string"}}}},
    "ultimate": {"type": "object", "properties": { "name": {"type": "string"}, "keybind": {"type": "string"}, "type": {"type": "string"}, "description": {"type": "string"}, "casting": {"type": "string"}, "damage": {"type": "string"}, "range": {"type": "string"}, "effect": {"type": "string"}, "duration": {"type": "string"}, "health_upon_revival": {"type": "string"}, "slow_rate": {"type": "string"}, "projectile_speed": {"type": "string"}, "movement_boost": {"type": "string"}, "bonus_health_details": {"type": "string"}, "energy_cost": {"type": "any"}, "details": {"type": "string"}}},
    "passives": {"type": "array", "items": {"type": "object", "properties": { "name": {"type": "string"}, "keybind": {"type": "string"}, "type": {"type": "string"}, "description": {"type": "string"}, "cooldown": {"type": "string"}, "damage": {"type": "string"}, "range": {"type": "string"}, "trigger_condition": {"type": "string"}, "effect_boost": {"type": "string"}, "speed_details": {"type": "string"}, "details": {"type": "string"}}}},
    "teamups": {"type": "array", "items": {"type": "object", "properties": { "name": {"type": "string"}, "keybind": {"type": "string"}, "partner": {"type": "any"}, "effect": {"type": "string"}, "teamup_bonus": {"type": "string"}, "duration": {"type": "string"}, "cooldown": {"type": "string"}, "range_target": {"type": "string"}, "special_notes": {"type": "string"}, "details": {"type": "string"}}}},
    "gameplay": {"type": "object", "properties": { "strategy_overview": {"type": "string"}, "weaknesses": {"type": "array"}, "achievements": {"type": "array", "items": {"type": "object", "properties": { "icon": {"type": "string"}, "name": {"type": "string"}, "description": {"type": "string"}, "points": {"type": "any"}}}}}},
    "lore_details": {"type": "object", "properties": { "ingame_bio_quote": {"type": "string"}, "ingame_bio_text": {"type": "string"}, "ingame_story_intro": {"type": "string"}, "hero_stories": {"type": "array", "items": {"type": "object", "properties": { "title": {"type": "string"}, "content": {"type": "string"}, "status": {"type": "string"}}}}, "balance_changes": {"type": "array", "items": {"type": "object", "properties": { "date_version": {"type": "string"}, "changes": {"type": "array"}}}}, "official_quote": {"type": "string"}, "official_description": {"type": "string"}}},
    "background": {"type": "object", "properties": { "real_name": {"type": "string"}, "aliases": {"type": "array"}, "birthplace": {"type": "string"}, "birthdate": {"type": "string"}, "gender": {"type": "string"}, "eye_color": {"type": "string"}, "hair_color": {"type": "string"}, "relatives": {"type": "array"}, "affiliation": {"type": "array"}, "first_appearance_comic": {"type": "string"}, "recommended_comics": {"type": "array"}, "lore_powers_skills": {"type": "array"}}},
    "misc": {"type": "object", "properties": { "voice_actor": {"type": "string"}, "quotes_link": {"type": "string"}, "community_buzz": {"type": "string"}, "helpful_links": {"type": "array", "items": {"type": "object", "properties": { "title": {"type": "string"}, "url": {"type": "string"}}}}}},
    "meta_stats": {"type": "object", "properties": { "tier": {"type": "string"}, "win_rate": {"type": "string"}, "wr_change": {"type": "string"}, "pick_rate": {"type": "string"}, "pr_change": {"type": "string"}, "ban_rate": {"type": "string"}, "matches": {"type": "string"}}},
    "data_sources": {"type": "object", "properties": { "wiki": {"type": "array"}, "tracker": {"type": "array"}, "comic_wiki": {"type": "array"}}}
}


# --- Directories (Main Script Perspective) ---
APP_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
APP_BASE_DIR = os.path.abspath(os.path.join(APP_SCRIPT_DIR, os.pardir))
APP_RAW_TEXT_DIR = os.path.join(APP_SCRIPT_DIR, "scraped_character_data")
APP_CHARACTER_JSON_OUTPUT_DIR = os.path.join(APP_BASE_DIR, "characters")
APP_CONFIG_DIR = os.path.join(APP_BASE_DIR, "config")
APP_IMAGE_DIR_CHECK = os.path.join(APP_BASE_DIR, "images")
APP_INFO_OUTPUT_DIR = os.path.join(APP_BASE_DIR, "info")
APP_COLOR_POOLS_FILE = os.path.join(APP_SCRIPT_DIR, 'character_color_pools.json') # For json_manager init


# --- Constants for json_manager.init (Main Script Perspective) ---
# Keys primarily populated by the Wiki AI + Patch AI process
CORE_GENERATED_KEYS_MAIN = [
    "name", "role", "stats", "abilities", "ultimate", "passives", "gameplay", "lore_details"
]
PRESERVED_SECTIONS_DURING_CORE_GEN_MAIN = [
    "teamups", "background", "misc", "meta_stats", "data_sources"
]
PRESERVED_NESTED_FIELDS_MAIN = [
    "gameplay.strategy_overview", "gameplay.weaknesses",
    "misc.community_buzz", "misc.helpful_links", "misc.quotes_link",
]
CHARACTER_BASE_SPEEDS_MAIN = { # Copied from original global scope
    "Adam Warlock": "6 m/s", "Black Panther": "7 m/s", "Black Widow": "6 m/s",
    "Captain America": "6 m/s", "Cloak and Dagger": "6 m/s", "Doctor Strange": "6 m/s",
    "Groot": "6 m/s", "Hawkeye": "6 m/s", "Hela": "6 m/s", "Hulk": "6 m/s",
    "Human Torch": "6 m/s", "Invisible Woman": "6 m/s", "Iron Fist": "6 m/s",
    "Iron Man": "6 m/s", "Jeff the Land Shark": "6 m/s", "Loki": "6 m/s",
    "Luna Snow": "6 m/s", "Magik": "6 m/s", "Magneto": "6 m/s", "Mantis": "6 m/s",
    "Mister Fantastic": "6 m/s", "Moon Knight": "6 m/s", "Namor": "6 m/s",
    "Peni Parker": "6 m/s", "Psylocke": "6 m/s", "Punisher": "6 m/s",
    "Rocket Raccoon": "6 m/s", "Scarlet Witch": "6 m/s", "Spider-Man": "6 m/s",
    "Squirrel Girl": "6 m/s", "Star-Lord": "6 m/s", "Storm": "6 m/s",
    "The Thing": "6 m/s", "Thor": "6 m/s", "Venom": "6 m/s",
    "Winter Soldier": "6 m/s", "Wolverine": "7 m/s"
}
# Other Settings (Main Script Perspective)
APP_API_CALL_DELAY_SECONDS = 1.5 # Example, if needed by json_manager
APP_SCRAPE_DELAY_SECONDS = 1 # For scraping module if it doesn't define its own

# --- Google API Key (Main Script Global) ---
# This key will be passed to ai_processor functions
google_api_key_main = os.environ.get("GOOGLE_API_KEY")

# --- Constants for Info File Scraping (Main Script Perspective) ---
INFO_CATEGORIES_MAIN = {
    "Announcements": ("announcements.txt", "https://www.marvelrivals.com/announcements/"),
    "Balance Post": ("balance_post.txt", "https://www.marvelrivals.com/balancepost/"),
    "Dev Diaries": ("dev_diaries.txt", "https://www.marvelrivals.com/devdiaries/"),
    "Game Update": ("game_update.txt", "https://www.marvelrivals.com/gameupdate/"),
    "News": ("news.txt", "https://www.marvelrivals.com/news/"),
}
MAX_ARTICLES_PER_CATEGORY_MAIN = 5

# --- Global Variables (Main Script GUI State) ---
ACTIVE_CHARACTER_LIST = [] # Populated by load_character_list_from_files
character_urls_main = {}   # Populated by config_manager.load_character_urls
log_buffer = io.StringIO() # For GUI log

# Thread control flags
stop_scrape_all_flag = threading.Event()
stop_generate_all_json_flag = threading.Event()

# AI Model Info (Populated by ai_processor.list_available_models_from_ai via initial_api_checks)
AVAILABLE_MODELS_MAIN = []
DEFAULT_MODEL_MAIN = ""

# Thread handles
scrape_all_thread = None
json_gen_all_thread = None
json_gen_single_thread = None
json_tune_thread = None
update_teamups_thread_handle = None
update_info_files_thread_handle = None
update_meta_stats_thread_handle = None

# GUI Variables (initialized to None, assigned in setup_gui)
root = None; notebook = None; status_var = None; log_text = None; copy_log_button = None;
scraper_character_var = None; scraper_character_dropdown = None; scraper_url_entry = None; scraper_url_listbox = None;
add_url_button = None; remove_url_button = None; scrape_button = None; scrape_all_button = None;
action_frame_tab_manage = None; progress_var = None; progress_bar = None; time_remaining_var = None;
time_remaining_label = None; stop_button = None; status_label = None; instruction_label = None;
add_char_name_entry = None; add_char_img_entry = None; add_char_icon_entry = None; add_char_wiki_entry = None;
add_char_tracker_entry = None; add_char_comic_entry = None; create_char_button = None;
json_character_var = None; json_character_dropdown = None; model_selection_var = None; model_combobox = None;
json_output_file_label = None; edit_prompt_button = None; open_prompt_dir_button = None;
generate_json_button = None; generate_all_json_button = None; cancel_generate_all_button = None; json_action_frame = None;
tune_character_var = None; tune_character_dropdown = None; tune_load_button = None; current_json_display = None;
tuning_instruction_input = None; tune_model_var = None; tune_model_combobox = None; tune_preview_button = None;
proposed_json_display = None; tune_save_button = None; tune_discard_button = None; tune_status_var = None;
original_loaded_json_str = None # For tuning tab state
proposed_tuned_json_data = None # For tuning tab state
refresh_ui_button = None # For top bar
# Buttons for Tab 1 advanced actions
update_teamups_button = None
update_meta_button = None
update_info_button = None


# ==============================================================================
# == GUI HELPER CLASSES & FUNCTIONS (Main Script Specific) ==
# ==============================================================================
class TextRedirector(io.StringIO):
    def __init__(self, widget_ref): # widget_ref to avoid global log_text here
        super().__init__()
        self.widget_ref = widget_ref
    def write(self, str_):
        log_buffer.write(str_) # Still write to main buffer
        if self.widget_ref and self.widget_ref.winfo_exists():
            try:
                self.widget_ref.after(0, self._write_to_widget_ref, str_)
            except tk.TclError: pass
    def _write_to_widget_ref(self, str_):
        if self.widget_ref and self.widget_ref.winfo_exists():
            try:
                current_state = self.widget_ref.cget("state")
                self.widget_ref.config(state=tk.NORMAL)
                self.widget_ref.insert(tk.END, str_)
                self.widget_ref.see(tk.END)
                self.widget_ref.config(state=current_state)
            except tk.TclError: pass
    def flush(self): pass


def update_all_character_dropdowns_gui(initial_setup=False):
    global ACTIVE_CHARACTER_LIST # This list is managed by this main script
    # GUI vars are global to this script
    dropdowns_vars_widgets = []
    if scraper_character_var and scraper_character_dropdown:
        dropdowns_vars_widgets.append((scraper_character_var, scraper_character_dropdown))
    if json_character_var and json_character_dropdown:
        dropdowns_vars_widgets.append((json_character_var, json_character_dropdown))
    if tune_character_var and tune_character_dropdown:
        dropdowns_vars_widgets.append((tune_character_var, tune_character_dropdown))

    options = ACTIVE_CHARACTER_LIST if ACTIVE_CHARACTER_LIST else ["(No Characters Found)"]
    previously_selected_value = None
    if not initial_setup and dropdowns_vars_widgets and dropdowns_vars_widgets[0][0]:
        try:
            previously_selected_value = dropdowns_vars_widgets[0][0].get()
            if previously_selected_value not in ACTIVE_CHARACTER_LIST: previously_selected_value = None
        except tk.TclError: previously_selected_value = None
    if not previously_selected_value and options and options[0] != "(No Characters Found)":
        previously_selected_value = options[0]

    for var, dd_widget in dropdowns_vars_widgets:
        if dd_widget and dd_widget.winfo_exists():
            try:
                current_val = var.get() # Store to see if it changes
                dd_widget['values'] = options
                new_selection = ""
                if previously_selected_value and previously_selected_value in options:
                    new_selection = previously_selected_value
                elif options and options[0] != "(No Characters Found)":
                    new_selection = options[0]
                
                if var.get() != new_selection: # Set only if different or to trigger trace
                    var.set(new_selection)
                # If var.get() was already new_selection, the trace won't fire.
                # We still need to ensure the combobox display text is correct.
                dd_widget.set(new_selection) # Explicitly set combobox text

                # Callbacks are triggered by var.set() if the value *changes*.
                # If the value didn't change but we still need to refresh dependent UI
                # (e.g., during initial_setup or if the underlying list of options changed
                # but the selection happened to remain the same valid item),
                # we might need to call these manually.

                # The trace_add on the StringVar should handle most updates when the *variable's value* changes.
                # The issue arises if the variable's value *doesn't* change but the context (like available files) does.
                # For initial_setup, we definitely want these to run.
                # If current_val == new_selection, the trace might not have fired if the value didn't actually change.
                
                # Corrected calls with _gui suffix
                if dd_widget == scraper_character_dropdown:
                    if initial_setup or current_val == new_selection: # Ensure update if value didn't change but context might have
                        if callable(update_scraper_url_listbox_gui): update_scraper_url_listbox_gui()
                elif dd_widget == json_character_dropdown:
                    if initial_setup or current_val == new_selection:
                        if callable(update_json_paths_gui): update_json_paths_gui()
                elif dd_widget == tune_character_dropdown:
                    if initial_setup or current_val == new_selection:
                         if callable(load_current_json_for_tuning_gui): load_current_json_for_tuning_gui()

            except tk.TclError as e: print(f"GUI Error updating dropdown: {e}")
            except Exception as e: print(f"GUI Unexpected error updating dropdown {dd_widget}: {e}")


def load_character_list_from_files_gui():
    """Scans output dir for .json files, updates ACTIVE_CHARACTER_LIST."""
    global ACTIVE_CHARACTER_LIST, APP_CHARACTER_JSON_OUTPUT_DIR
    print(f"GUI: Scanning for character JSONs in: {APP_CHARACTER_JSON_OUTPUT_DIR}")
    failed_dir = os.path.join(APP_CHARACTER_JSON_OUTPUT_DIR, "failed")
    try:
        os.makedirs(APP_CHARACTER_JSON_OUTPUT_DIR, exist_ok=True)
        os.makedirs(failed_dir, exist_ok=True)
    except OSError as e:
        print(f"GUI ERROR: Could not create directories: {e}"); ACTIVE_CHARACTER_LIST = []; return

    temp_list = []; found_chars = set(); moved_error_files = 0
    try:
        for filename in os.listdir(APP_CHARACTER_JSON_OUTPUT_DIR):
            filepath = os.path.join(APP_CHARACTER_JSON_OUTPUT_DIR, filename)
            if os.path.isfile(filepath) and filename.lower().endswith(".json.api_error.txt"):
                try:
                    # shutil.move is better but for now, keeping it simple.
                    # If shutil is needed, import it at the top.
                    os.rename(filepath, os.path.join(failed_dir, filename)) # Simple rename
                    moved_error_files += 1
                except Exception as move_e: print(f"GUI WARN: Could not move error file {filename}: {move_e}")
                continue
            if filename.lower().endswith(".json") and os.path.isfile(filepath):
                char_name = os.path.splitext(filename)[0] # Base name is character name
                # Add to list (duplicate handling can be simpler if filenames are canonical)
                if char_name.lower() not in found_chars:
                    temp_list.append(char_name)
                    found_chars.add(char_name.lower())
                # else: print(f"GUI INFO: Skipping duplicate/variation from dir scan: {char_name}") # Less verbose
    except OSError as e: print(f"GUI ERROR: Reading char dir {APP_CHARACTER_JSON_OUTPUT_DIR}: {e}"); ACTIVE_CHARACTER_LIST = []; return
    ACTIVE_CHARACTER_LIST = sorted(temp_list)
    print(f"GUI: Found {len(ACTIVE_CHARACTER_LIST)} valid characters.")
    if moved_error_files > 0: print(f"GUI: Moved {moved_error_files} error file(s) to 'failed'.")


# --- GUI Progress Update Callback (Generic) ---
def gui_progress_updater(current_step, total_steps, message_prefix, is_final=False, errors=0, stopped=False):
    """ Generic callback for worker threads to update GUI progress and status. """
    global root, status_var, progress_var, time_remaining_var # Uses GUI globals
    
    if not root or not root.winfo_exists(): return

    def update_ui():
        if progress_var:
            progress_percent = int(((current_step +1) / total_steps) * 100) if total_steps > 0 else 0
            if is_final and not stopped : progress_percent = 100 # Ensure 100% on non-stopped completion
            elif is_final and stopped: pass # Keep progress where it stopped
            progress_var.set(progress_percent)

        if status_var:
            status_msg = f"Status: {message_prefix}"
            if not is_final:
                status_msg += f" ({current_step+1}/{total_steps}) {progress_percent}%"
            elif errors > 0 :
                 status_msg += f" - Completed with {errors} error(s)."
            elif stopped:
                 status_msg += f" - Operation CANCELLED."
            else:
                 status_msg += f" - Operation COMPLETE."
            status_var.set(status_msg)
        
        # Time remaining can be complex to estimate accurately from a generic callback
        # For now, clear it on final, or specific threads can manage it more directly.
        if is_final and time_remaining_var:
            time_remaining_var.set("")

        if is_final: # Re-enable buttons when the entire operation is final
            enable_buttons_gui() # Use the GUI specific enable function

    root.after(0, update_ui)


# (Button state management functions: disable_buttons_gui, enable_buttons_gui will be very similar to original)
# (Callbacks for Tab 1, Tab 2, Tab 3, Tab 4 buttons will be defined here)
# (setup_gui and if __name__ == "__main__" will be at the end of this file)
# ==============================================================================
# == GUI BUTTON STATE MANAGEMENT ==
# ==============================================================================

def disable_buttons_gui(): # Renamed
    global stop_button, cancel_generate_all_button, refresh_ui_button, action_frame_tab_manage, json_action_frame
    # GUI vars are global to this script
    try:
        widgets_to_disable = [
            scrape_button, scrape_all_button, add_url_button, remove_url_button,
            update_teamups_button, update_meta_button, update_info_button,
            generate_json_button, generate_all_json_button, edit_prompt_button,
            open_prompt_dir_button, model_combobox, create_char_button,
            tune_load_button, tune_preview_button, tune_save_button,
            tune_discard_button, tune_model_combobox,
            refresh_ui_button
        ]
        for w in widgets_to_disable:
             if w and isinstance(w, (tk.Widget, ttk.Widget)) and w.winfo_exists():
                 try:
                     if isinstance(w, ttk.Combobox): w.config(state=tk.DISABLED)
                     else: w.config(state=tk.DISABLED)
                 except tk.TclError: pass

        is_scraping_all = scrape_all_thread and scrape_all_thread.is_alive()
        if stop_button and stop_button.winfo_exists():
            if is_scraping_all and action_frame_tab_manage and action_frame_tab_manage.winfo_exists():
                try:
                    if stop_button.master != action_frame_tab_manage: stop_button.pack(in_=action_frame_tab_manage, side=tk.LEFT, padx=(10,0))
                    else: stop_button.pack(side=tk.LEFT, padx=(10,0)) # Repack to ensure visibility
                    stop_button.config(text="Stop Scrape All", state=tk.NORMAL)
                except tk.TclError: pass
            else:
                try: stop_button.pack_forget()
                except tk.TclError: pass
        
        is_generating_all_json = json_gen_all_thread and json_gen_all_thread.is_alive()
        if cancel_generate_all_button and cancel_generate_all_button.winfo_exists():
            if is_generating_all_json and json_action_frame and json_action_frame.winfo_exists():
                try:
                    if cancel_generate_all_button.master != json_action_frame: cancel_generate_all_button.pack(in_=json_action_frame, side=tk.LEFT, padx=(10,0))
                    else: cancel_generate_all_button.pack(side=tk.LEFT, padx=(10,0)) # Repack
                    cancel_generate_all_button.config(text="Cancel Generate All", state=tk.NORMAL)
                except tk.TclError: pass
            else:
                 try: cancel_generate_all_button.pack_forget() # Hide if not generating all
                 except tk.TclError: pass
    except (tk.TclError, NameError, AttributeError): pass

def enable_buttons_gui(): # Renamed
    # GUI vars are global to this script
    try:
        scrape_active = scrape_all_thread and scrape_all_thread.is_alive()
        json_gen_single_active = json_gen_single_thread and json_gen_single_thread.is_alive()
        json_gen_all_active = json_gen_all_thread and json_gen_all_thread.is_alive()
        tune_active = json_tune_thread and json_tune_thread.is_alive()
        teamup_update_active = update_teamups_thread_handle and update_teamups_thread_handle.is_alive()
        info_update_active = update_info_files_thread_handle and update_info_files_thread_handle.is_alive()
        meta_update_active = update_meta_stats_thread_handle and update_meta_stats_thread_handle.is_alive()

        any_major_process_active = scrape_active or json_gen_single_active or json_gen_all_active or \
                                   tune_active or teamup_update_active or info_update_active or meta_update_active

        def set_state(widget, target_state):
            if widget and isinstance(widget, (tk.Widget, ttk.Widget)) and widget.winfo_exists():
                try:
                    if isinstance(widget, ttk.Combobox) and target_state == tk.NORMAL: widget.config(state="readonly")
                    else: widget.config(state=target_state)
                except tk.TclError: pass

        set_state(refresh_ui_button, tk.DISABLED if any_major_process_active else tk.NORMAL)
        set_state(scrape_button, tk.DISABLED if any_major_process_active else tk.NORMAL)
        set_state(scrape_all_button, tk.DISABLED if any_major_process_active else tk.NORMAL)
        set_state(add_url_button, tk.DISABLED if any_major_process_active else tk.NORMAL)
        set_state(update_teamups_button, tk.DISABLED if any_major_process_active else tk.NORMAL)
        set_state(update_meta_button, tk.DISABLED if any_major_process_active else tk.NORMAL)
        set_state(update_info_button, tk.DISABLED if any_major_process_active else tk.NORMAL)
        if scraper_url_listbox and scraper_url_listbox.winfo_exists() and callable(on_listbox_select_gui): on_listbox_select_gui(None)
        else: set_state(remove_url_button, tk.DISABLED)
        set_state(create_char_button, tk.DISABLED if any_major_process_active else tk.NORMAL)
        set_state(generate_all_json_button, tk.DISABLED if any_major_process_active else tk.NORMAL)
        set_state(edit_prompt_button, tk.DISABLED if any_major_process_active else tk.NORMAL)
        set_state(open_prompt_dir_button, tk.DISABLED if any_major_process_active else tk.NORMAL)
        set_state(model_combobox, tk.DISABLED if any_major_process_active else tk.NORMAL) # Becomes readonly
        if callable(update_json_paths_gui): update_json_paths_gui()
        set_state(tune_load_button, tk.DISABLED if any_major_process_active else tk.NORMAL)
        set_state(tune_model_combobox, tk.DISABLED if any_major_process_active else tk.NORMAL) # Becomes readonly
        can_preview = original_loaded_json_str is not None and not any_major_process_active
        set_state(tune_preview_button, tk.NORMAL if can_preview else tk.DISABLED)
        can_save_discard = proposed_tuned_json_data is not None and not any_major_process_active
        set_state(tune_save_button, tk.NORMAL if can_save_discard else tk.DISABLED)
        set_state(tune_discard_button, tk.NORMAL if can_save_discard else tk.DISABLED)

        if stop_button and stop_button.winfo_exists() and not scrape_active: stop_button.pack_forget()
        if cancel_generate_all_button and cancel_generate_all_button.winfo_exists() and not json_gen_all_active: cancel_generate_all_button.pack_forget()
        
        if not any_major_process_active: # Reset progress only if ALL relevant processes are idle
             if progress_var and isinstance(progress_var, tk.DoubleVar):
                 try: progress_var.set(0)
                 except tk.TclError: pass
             if time_remaining_var and isinstance(time_remaining_var, tk.StringVar):
                 try: time_remaining_var.set("")
                 except tk.TclError: pass
    except (tk.TclError, NameError, AttributeError): pass


# ==============================================================================
# == GUI CALLBACKS & ACTION STARTERS ==
# ==============================================================================

# --- Config Related Callbacks (using config_manager) ---
def load_settings_gui(): # Renamed
    global model_selection_var, tune_model_var, model_combobox, tune_model_combobox
    global DEFAULT_MODEL_MAIN, AVAILABLE_MODELS_MAIN # Use main script's model info
    
    settings_data = config_manager.load_ui_settings()
    selected_gen_model = settings_data.get("selected_model", DEFAULT_MODEL_MAIN)
    selected_tune_model = settings_data.get("tune_model", DEFAULT_MODEL_MAIN)

    if not (selected_gen_model in AVAILABLE_MODELS_MAIN) and AVAILABLE_MODELS_MAIN:
        print(f"GUI WARN: Loaded gen model '{selected_gen_model}' not in available. Defaulting.")
        selected_gen_model = DEFAULT_MODEL_MAIN if DEFAULT_MODEL_MAIN in AVAILABLE_MODELS_MAIN else AVAILABLE_MODELS_MAIN[0]
    elif not AVAILABLE_MODELS_MAIN:
        selected_gen_model = DEFAULT_MODEL_MAIN # Fallback if no models loaded yet

    if not (selected_tune_model in AVAILABLE_MODELS_MAIN) and AVAILABLE_MODELS_MAIN:
        print(f"GUI WARN: Loaded tune model '{selected_tune_model}' not in available. Defaulting.")
        selected_tune_model = DEFAULT_MODEL_MAIN if DEFAULT_MODEL_MAIN in AVAILABLE_MODELS_MAIN else AVAILABLE_MODELS_MAIN[0]
    elif not AVAILABLE_MODELS_MAIN:
        selected_tune_model = DEFAULT_MODEL_MAIN

    options = AVAILABLE_MODELS_MAIN if AVAILABLE_MODELS_MAIN else [DEFAULT_MODEL_MAIN] # Ensure options has at least default

    if model_selection_var and model_combobox and model_combobox.winfo_exists():
        model_combobox['values'] = options
        model_selection_var.set(selected_gen_model)
        model_combobox.set(selected_gen_model)
    if tune_model_var and tune_model_combobox and tune_model_combobox.winfo_exists():
        tune_model_combobox['values'] = options
        tune_model_var.set(selected_tune_model)
        tune_model_combobox.set(selected_tune_model)
    print(f"GUI: Settings loaded. Gen: {selected_gen_model}, Tune: {selected_tune_model}")

def save_settings_gui(event=None): # Renamed
    settings_to_save = {}
    if model_selection_var: settings_to_save["selected_model"] = model_selection_var.get()
    if tune_model_var: settings_to_save["tune_model"] = tune_model_var.get()
    if settings_to_save:
        config_manager.save_ui_settings(settings_to_save)
        print(f"GUI: UI settings saved via config_manager.")

# --- Tab 1: Manage & Scrape Callbacks ---
def update_scraper_url_listbox_gui(*args): # Renamed
    global character_urls_main # Use main script's URL data
    try:
        if not root or not root.winfo_exists() or not scraper_url_listbox or not scraper_url_listbox.winfo_exists() or not scraper_character_var: return
        selected_character = scraper_character_var.get()
        scraper_url_listbox.delete(0, END)
        if selected_character and selected_character in ACTIVE_CHARACTER_LIST:
            urls = character_urls_main.get(selected_character, [])
            if urls: [scraper_url_listbox.insert(END, url) for url in urls]
            else: scraper_url_listbox.insert(END, "(No URLs saved)"); scraper_url_listbox.itemconfig(0, {'fg':'grey'})
        else: scraper_url_listbox.insert(END, "(Select character)"); scraper_url_listbox.itemconfig(0, {'fg':'grey'})
        if callable(on_listbox_select_gui): on_listbox_select_gui(None)
    except (tk.TclError, NameError, AttributeError): pass

def add_scraper_url_gui(): # Renamed
    global character_urls_main # Use main script's URL data
    if not scraper_character_var or not scraper_url_entry: return
    selected_character = scraper_character_var.get(); new_url = scraper_url_entry.get().strip()
    if not selected_character or selected_character not in ACTIVE_CHARACTER_LIST: messagebox.showerror("Error", "Select character."); return
    if not new_url or not (new_url.startswith("http://") or new_url.startswith("https://")): messagebox.showerror("Error", "Invalid URL."); return
    
    current_urls = character_urls_main.get(selected_character, [])
    if new_url in current_urls: messagebox.showwarning("Duplicate", "URL already saved."); return
    current_urls.append(new_url); character_urls_main[selected_character] = current_urls
    if config_manager.save_character_urls(character_urls_main):
        update_scraper_url_listbox_gui(); scraper_url_entry.delete(0, END)
        if status_var: status_var.set(f"Status: Added URL for {selected_character}")
    else: messagebox.showerror("Save Error", "Failed to save URL list.")

def remove_scraper_url_gui(): # Renamed
    global character_urls_main # Use main script's URL data
    if not scraper_character_var or not scraper_url_listbox: return
    selected_character = scraper_character_var.get(); selection_indices = scraper_url_listbox.curselection()
    if not selected_character or selected_character not in ACTIVE_CHARACTER_LIST: messagebox.showerror("Error", "Select character."); return
    if not selection_indices: messagebox.showerror("Error", "Select URL to remove."); return
    selected_url = scraper_url_listbox.get(selection_indices[0])
    if selected_url.startswith("("): return # Placeholder
    
    current_urls = character_urls_main.get(selected_character, [])
    if selected_url in current_urls:
        current_urls.remove(selected_url); character_urls_main[selected_character] = current_urls
        if config_manager.save_character_urls(character_urls_main):
            update_scraper_url_listbox_gui()
            if status_var: status_var.set(f"Status: Removed URL for {selected_character}")
        else: messagebox.showerror("Save Error", "Failed to save URL list after removal.")
    else: messagebox.showerror("Sync Error", "URL not found in data."); update_scraper_url_listbox_gui()

def on_listbox_select_gui(event): # Renamed
    try:
        if not remove_url_button or not remove_url_button.winfo_exists() or not scraper_url_listbox or not scraper_url_listbox.winfo_exists(): return
        any_proc = any(t and t.is_alive() for t in [scrape_all_thread, json_gen_single_thread, json_gen_all_thread, json_tune_thread])
        if any_proc: remove_url_button.config(state=tk.DISABLED); return
        selected_text = scraper_url_listbox.get(scraper_url_listbox.curselection()) if scraper_url_listbox.curselection() else ""
        remove_url_button.config(state=tk.NORMAL if selected_text and not selected_text.startswith("(") else tk.DISABLED)
    except tk.TclError: pass

# --- Action Starter Callbacks for Tab 1 (Scraping & Updates) ---
def start_scrape_single_character_gui(): # Renamed
    global scrape_single_character_thread_handle # Use a unique handle if needed, or rely on json_manager
    if not scraper_character_var: return
    character = scraper_character_var.get()
    if not character or character not in ACTIVE_CHARACTER_LIST: messagebox.showerror("Error", "Select character."); return
    urls = character_urls_main.get(character, [])
    if not urls: messagebox.showinfo("No URLs", f"No URLs for '{character}'."); return
    
    disable_buttons_gui()
    if status_var: status_var.set(f"Status: Scraping Raw Text for {character}...")
    
    # The thread target will be a function in scraper_utils or json_manager
    # For now, assuming scraper_utils has a function that takes these and a file path
    def scrape_single_thread_target(char_name, urls_list, raw_text_dir_path, stop_event):
        # This is the actual work done in the thread
        start_t = time.time()
        success_count_total = 0
        sanitized_char_name_part = scraper_utils.sanitize_filename(char_name, extension="") # Pass empty string for extension
    # Now construct the full desired filename
        raw_filename_correct = f"{sanitized_char_name_part}_raw.txt"
        raw_filepath = os.path.join(raw_text_dir_path, raw_filename_correct)

        # Clear existing file for single scrape
        if os.path.exists(raw_filepath):
            try: os.remove(raw_filepath)
            except OSError as e_del: print(f"GUI WARN: Failed to remove old raw file {raw_filepath}: {e_del}")
        
        first_write = True
        for url_item in urls_list:
            if stop_event.is_set(): break
            if scraper_utils.scrape_single_wiki_page_to_file(url_item, raw_filepath, append_mode=not first_write, source_url_for_header=url_item):
                success_count_total +=1
                first_write = False # Subsequent scrapes for this char append
            time.sleep(APP_SCRAPE_DELAY_SECONDS / 2) # Use APP_ constant

        duration_t = str(datetime.timedelta(seconds=int(time.time() - start_t)))
        result_msg_t = f"Status: Finished scraping for {char_name} ({success_count_total}/{len(urls_list)}) in {duration_t}."
        
        if root and root.winfo_exists(): # Safely update GUI
            root.after(0, lambda: (status_var.set(result_msg_t) if status_var else None, enable_buttons_gui()))

    # Create and start the thread
    # stop_scrape_all_flag can be reused if only one "scrape" type op runs at a time
    stop_scrape_all_flag.clear() # Clear before starting a new single scrape
    scrape_single_thread_handle = threading.Thread(
        target=scrape_single_thread_target,
        args=(character, urls, APP_RAW_TEXT_DIR, stop_scrape_all_flag), # Pass APP_RAW_TEXT_DIR
        daemon=True
    )
    scrape_single_thread_handle.start()


def start_scrape_all_characters_gui(): # Renamed
    global scrape_all_thread # Uses the global scrape_all_thread handle
    chars_with_urls = {name: urls for name, urls in character_urls_main.items() if urls}
    if not chars_with_urls: messagebox.showinfo("No URLs", "No URLs saved for any character."); return
    if not messagebox.askyesno("Confirm Scrape All", f"Scrape raw text for {len(chars_with_urls)} characters?"): return

    disable_buttons_gui()
    if progress_var: progress_var.set(0)
    if time_remaining_var: time_remaining_var.set("Starting...")
    stop_scrape_all_flag.clear()

    def scrape_all_thread_target_wrapper(): # Wrapper to manage GUI updates from main script
        start_time_all = time.time()
        total_chars = len(chars_with_urls)
        processed_all = 0
        total_urls_scraped_all = 0

        sorted_chars = sorted(chars_with_urls.keys())

        for idx, char_name_all in enumerate(sorted_chars):
            if stop_scrape_all_flag.is_set(): print("GUI: Scrape All cancelled."); break
            
            # GUI progress update from this main thread context
            if root and root.winfo_exists():
                elapsed = time.time() - start_time_all
                avg_time = elapsed / (idx + 1) if idx >=0 else APP_SCRAPE_DELAY_SECONDS # Use APP_ const
                remaining_t = (total_chars - (idx + 1)) * avg_time
                time_left_s = str(datetime.timedelta(seconds=int(remaining_t))) if remaining_t > 0 else "..."
                prog_perc = int(((idx + 1) / total_chars) * 100) if total_chars > 0 else 0
                
                def update_scrape_all_progress_ui(p, tl, msg): # Closure for safety
                    if progress_var: progress_var.set(p)
                    if time_remaining_var: time_remaining_var.set(f"Est. Time Left: {tl}")
                    if status_var: status_var.set(msg)
                
                status_message_scrape_all = f"Status: Scraping All... ({idx+1}/{total_chars}) - {char_name_all}"
                root.after(0, update_scrape_all_progress_ui, prog_perc, time_left_s, status_message_scrape_all)

            # Actual scraping for one character (this logic is now more self-contained)
            # This reuses the single character scraping logic but without its own threading.
            char_urls = chars_with_urls[char_name_all]
            success_count_single_char = 0
            sanitized_char_name_part_all = scraper_utils.sanitize_filename(char_name_all, extension="")
            raw_filename_correct_all = f"{sanitized_char_name_part_all}_raw.txt"
            raw_filepath_all = os.path.join(APP_RAW_TEXT_DIR, raw_filename_correct_all)
            if os.path.exists(raw_filepath_all):
                try: os.remove(raw_filepath_all)
                except OSError: pass # Ignore if can't delete
            
            first_write_all = True
            for url_item_all in char_urls:
                if stop_scrape_all_flag.is_set(): break
                if scraper_utils.scrape_single_wiki_page_to_file(url_item_all, raw_filepath_all, append_mode=not first_write_all, source_url_for_header=url_item_all):
                    success_count_single_char +=1
                    first_write_all = False
                time.sleep(APP_SCRAPE_DELAY_SECONDS / 4) # Shorter delay between URLs of same char
            
            total_urls_scraped_all += success_count_single_char
            processed_all += 1
            
            if not stop_scrape_all_flag.is_set() and idx < total_chars - 1:
                time.sleep(APP_SCRAPE_DELAY_SECONDS) # Delay between characters

        # Final UI update after loop
        final_duration_all = str(datetime.timedelta(seconds=int(time.time() - start_time_all)))
        final_msg_all = f"Status: Scrape All {'STOPPED' if stop_scrape_all_flag.is_set() else 'COMPLETE'}. {processed_all}/{total_chars} chars. {total_urls_scraped_all} URLs. In {final_duration_all}."
        
        if root and root.winfo_exists():
            root.after(0, lambda: (
                status_var.set(final_msg_all) if status_var else None,
                progress_var.set(100) if progress_var and not stop_scrape_all_flag.is_set() else None,
                time_remaining_var.set("") if time_remaining_var else None,
                enable_buttons_gui()
            ))
        global scrape_all_thread # To clear the handle
        scrape_all_thread = None

    scrape_all_thread = threading.Thread(target=scrape_all_thread_target_wrapper, daemon=True)
    scrape_all_thread.start()


def stop_scrape_all_gui(): # Renamed
    if scrape_all_thread and scrape_all_thread.is_alive():
        print("\nGUI: >>> Sending Stop Signal to Scrape All Raw Text... <<<")
        stop_scrape_all_flag.set()
        if stop_button and stop_button.winfo_exists():
            try: stop_button.config(text="Stopping...", state=tk.DISABLED)
            except tk.TclError: pass
    else: print("GUI: No active 'Scrape All' process to stop.")

def start_update_info_files_gui(): # Renamed
    global update_info_files_thread_handle, APP_INFO_OUTPUT_DIR, status_var
    global INFO_CATEGORIES_MAIN, MAX_ARTICLES_PER_CATEGORY_MAIN

    if update_info_files_thread_handle and update_info_files_thread_handle.is_alive():
        messagebox.showinfo("Busy", "Info File update is already running."); return
    if not messagebox.askyesno("Confirm", "Update all info files from official site?"): return
    
    disable_buttons_gui()
    if status_var: status_var.set("Status: Starting Info File update...")

    def info_thread_target(): # Wrapper
        total_cat, success_cat, error_cat = scraper_utils.update_all_info_files_su(
             APP_INFO_OUTPUT_DIR,
             INFO_CATEGORIES_MAIN,
             MAX_ARTICLES_PER_CATEGORY_MAIN,
             gui_progress_updater
        )
        
        final_msg_info = f"Status: Info Update COMPLETE. Categories: {total_cat}, Success: {success_cat}, Errors: {error_cat}."
        if success_cat > 0:
            print(f"GUI: Updating last_update.json for Info Files completion...")
            config_manager.update_last_update_file("last_info_update", datetime.datetime.now().isoformat())
            latest_patch_version = "Unknown"
            try:
                patch_file_path = os.path.join(APP_INFO_OUTPUT_DIR, "balance_post.txt")
                if patch_file_path and os.path.exists(patch_file_path):
                    with open(patch_file_path, 'r', encoding='utf-8') as f_patch:
                        first_lines = [f_patch.readline() for _ in range(10)]
                    version_pattern = re.compile(r"Version\s+(\d{8})\s+Balance\s+Post", re.IGNORECASE)
                    for line in first_lines:
                        match = version_pattern.search(line)
                        if match:
                            latest_patch_version = match.group(1)
                            print(f"GUI: Extracted Patch Version from info file: {latest_patch_version}")
                            break
                config_manager.update_last_update_file("last_game_patch_parsed", latest_patch_version)
            except Exception as e_patch_extract:
                print(f"GUI WARN: Could not extract patch version from info file: {e_patch_extract}")

        if root and root.winfo_exists():
            root.after(0, lambda: (
                status_var.set(final_msg_info) if status_var else None,
                messagebox.showinfo("Info Update", f"Checked: {total_cat}\nSuccess: {success_cat}\nErrors: {error_cat}"),
                enable_buttons_gui()
            ))
        global update_info_files_thread_handle # To clear handle
        update_info_files_thread_handle = None

    update_info_files_thread_handle = threading.Thread(target=info_thread_target, daemon=True)
    update_info_files_thread_handle.start()


def start_update_all_teamups_gui(): # Renamed
    global update_teamups_thread_handle, ACTIVE_CHARACTER_LIST
    if update_teamups_thread_handle and update_teamups_thread_handle.is_alive():
        messagebox.showinfo("Busy", "Team-Up update is already running."); return
    if not messagebox.askyesno("Confirm", "Update all character JSONs with Team-Up data from wiki?"): return

    disable_buttons_gui()
    if status_var: status_var.set("Status: Starting Team-Up data update...")

    def teamup_thread_target(): # Wrapper
        processed_tu, updated_tu, errors_tu = 0, 0, 1
        final_msg_tu = "Status: Team-Up Update FAILED (Initial error)."

        try:
            print("GUI: Fetching team-up wiki page via scraper_utils...")
            teamup_html = scraper_utils.fetch_teamup_wiki_page_su()
            if not teamup_html:
                print("GUI ERROR: Failed to fetch team-up wiki page.")
                final_msg_tu = "Status: Team-Up Update FAILED - Could not fetch wiki page."
            else:
                print("GUI: Parsing team-up data via scraper_utils...")
                normalized_active_set = {scraper_utils.normalize_for_comparison(name) for name in ACTIVE_CHARACTER_LIST}
                normalized_to_original_map = {scraper_utils.normalize_for_comparison(name): name for name in ACTIVE_CHARACTER_LIST}
                active_char_norm_tuple = (normalized_active_set, normalized_to_original_map)
                parsed_wiki_teamups_data = scraper_utils.parse_active_teamups_from_html_su(teamup_html, active_char_norm_tuple)
                if not parsed_wiki_teamups_data:
                    print("GUI ERROR: Failed to parse any active team-ups from wiki.")
                    final_msg_tu = "Status: Team-Up Update FAILED - Could not parse team-ups."
                else:
                    print("GUI: Updating character JSONs with team-up data via json_manager...")
                    processed_tu, updated_tu, errors_tu = json_manager.update_all_characters_with_teamups(
                        parsed_wiki_teamups_data,
                        ACTIVE_CHARACTER_LIST,
                        gui_progress_updater
                    )
                    final_msg_tu = f"Status: Team-Up Update COMPLETE. Processed: {processed_tu}, Updated: {updated_tu}, Errors: {errors_tu}."
        except Exception as e_thread:
            print(f"GUI ERROR in teamup_thread_target: {e_thread}")
            import traceback
            traceback.print_exc(file=sys.stderr)
            final_msg_tu = f"Status: Team-Up Update FAILED - Exception: {e_thread}"
            if processed_tu == 0 and updated_tu == 0 and errors_tu == 1:
                try:
                    num_json_files = len([f for f in os.listdir(APP_CHARACTER_JSON_OUTPUT_DIR) if f.lower().endswith('.json')])
                    errors_tu = num_json_files
                except:
                    pass

        if root and root.winfo_exists():
            root.after(0, lambda: (
                status_var.set(final_msg_tu) if status_var else None,
                messagebox.showwarning("Team-Up Update", final_msg_tu) if errors_tu > 0 else messagebox.showinfo("Team-Up Update", final_msg_tu.replace("Status: ", "")),
                enable_buttons_gui()
            ))
        global update_teamups_thread_handle
        update_teamups_thread_handle = None

    update_teamups_thread_handle = threading.Thread(target=teamup_thread_target, daemon=True)
    update_teamups_thread_handle.start()


def start_update_all_meta_stats_gui(): # Renamed
    global update_meta_stats_thread_handle
    if update_meta_stats_thread_handle and update_meta_stats_thread_handle.is_alive():
        messagebox.showinfo("Busy", "Meta Stats update is running."); return
    if not messagebox.askyesno("Confirm", "Update all Meta Stats from tracker site?"): return

    disable_buttons_gui()
    if status_var: status_var.set("Status: Starting Meta Stats update...")

    def meta_stats_thread_target(): # Wrapper
        # First, we need to get the scraped_tracker_data using scraper_utils
        scraped_data_for_meta = None
        print("GUI: Fetching all tracker data via scraper_utils...")
        if callable(scraper_utils.scrape_all_rivalstracker_heroes):
            scraped_data_for_meta = scraper_utils.scrape_all_rivalstracker_heroes()
        else:
            print("GUI CRITICAL ERROR: scraper_utils.scrape_all_rivalstracker_heroes not found!")
            # Handle this critical error appropriately, maybe update GUI and return

        if scraped_data_for_meta:
            print("GUI: Updating character JSONs with meta stats via json_manager...")
            processed_ms, updated_ms, errors_ms = json_manager.update_all_character_meta_stats(
                scraped_data_for_meta,  # Pass the scraped data as the first argument
                gui_progress_updater    # Pass the GUI callback as the second argument
            )
        else:
            print("GUI ERROR: Failed to scrape tracker data, cannot update meta stats.")
            processed_ms, updated_ms, errors_ms = 0, 0, 1 # Indicate failure
            # You might want to get a count of total JSON files to set errors_ms more accurately
            try:
                num_json_files_meta = len([f for f in os.listdir(APP_CHARACTER_JSON_OUTPUT_DIR) if f.lower().endswith('.json')])
                errors_ms = num_json_files_meta
            except:
                pass # Keep errors_ms as 1 if dir listing fails

        final_msg_ms = f"Status: Meta Stats Update COMPLETE. Processed: {processed_ms}, Updated: {updated_ms}, Errors: {errors_ms}."
        if root and root.winfo_exists():
            root.after(0, lambda: (
                status_var.set(final_msg_ms) if status_var else None,
                messagebox.showinfo("Meta Stats Update", f"Files Checked: {processed_ms}\nUpdated: {updated_ms}\nErrors: {errors_ms}"),
                enable_buttons_gui()
            ))
        global update_meta_stats_thread_handle # To clear handle
        update_meta_stats_thread_handle = None

    update_meta_stats_thread_handle = threading.Thread(target=meta_stats_thread_target, daemon=True)
    update_meta_stats_thread_handle.start()


# --- Tab 2: Add Character Callback ---
def create_new_character_gui(): # Renamed
    global ACTIVE_CHARACTER_LIST, character_urls_main # Operates on main script's data
    # ... (Get values from GUI entries: add_char_name_entry, etc.) ...
    new_name = add_char_name_entry.get().strip()
    img_file = add_char_img_entry.get().strip()
    icon_file = add_char_icon_entry.get().strip()
    wiki_url = add_char_wiki_entry.get().strip()
    tracker_url = add_char_tracker_entry.get().strip()
    comic_url = add_char_comic_entry.get().strip()

    # ... (Input validation as before) ...
    if not new_name or not img_file or not icon_file:
        messagebox.showerror("Input Error", "Name, Image, and Icon filenames are required."); return
    if new_name.lower() in [name.lower() for name in ACTIVE_CHARACTER_LIST]:
        messagebox.showerror("Duplicate Error", f"Character '{new_name}' already exists."); return

    disable_buttons_gui()
    if status_var: status_var.set(f"Status: Creating character '{new_name}'...")

    # Call a function in json_manager to handle file creation
    # This function in json_manager will use config_manager for config files
    success_create, message_create = json_manager.create_character_files_jm(
        new_name, img_file, icon_file, wiki_url, tracker_url, comic_url,
        character_urls_main # Pass the current dict of URLs
    )

    if success_create:
        # Update character_urls_main with the potentially modified one from json_manager
        # (if create_character_files_jm returns the updated dict)
        # Or, json_manager.create_character_files_jm could directly call config_manager.save_character_urls
        # For now, assume json_manager handles saving URLs if they are modified.
        # We just need to reload the character list.
        load_character_list_from_files_gui()
        update_all_character_dropdowns_gui()
        # Select new character in dropdowns
        if scraper_character_var: scraper_character_var.set(new_name)
        if json_character_var: json_character_var.set(new_name)
        if tune_character_var: tune_character_var.set(new_name)
        # Clear entry fields
        add_char_name_entry.delete(0, END); add_char_img_entry.delete(0, END); add_char_icon_entry.delete(0, END)
        add_char_wiki_entry.delete(0, END); add_char_tracker_entry.delete(0, END); add_char_comic_entry.delete(0, END)
        messagebox.showinfo("Success", message_create)
        if status_var: status_var.set(f"Status: Successfully added '{new_name}'.")
    else:
        messagebox.showerror("Creation Error", message_create)
        if status_var: status_var.set(f"Status: Failed to add '{new_name}'.")
    
    enable_buttons_gui()

# --- Tab 3: Generate JSON Callbacks ---
def update_json_paths_gui(*args): # Renamed
    # ... (Logic mostly same as before, using APP_RAW_TEXT_DIR and APP_CHARACTER_JSON_OUTPUT_DIR) ...
    # ... and scraper_utils.sanitize_filename ...
    global json_character_var, json_output_file_label, generate_json_button, ACTIVE_CHARACTER_LIST
    global json_gen_single_thread, json_gen_all_thread, json_tune_thread
    try:
        if not root or not root.winfo_exists() or not json_output_file_label or not generate_json_button: return
        selected_character = json_character_var.get() if json_character_var else ""
        any_process_active = any(t and t.is_alive() for t in [json_gen_single_thread, json_gen_all_thread, json_tune_thread])

        if selected_character and selected_character != "(No Characters Found)" and selected_character in ACTIVE_CHARACTER_LIST:
            raw_fn_base = scraper_utils.sanitize_filename(selected_character, extension="")
            if not raw_fn_base: # Handle sanitize error
                json_output_file_label.config(text="Output JSON: (Error sanitizing name)", foreground="red")
                generate_json_button.config(state=tk.DISABLED)
                return
            raw_filepath = os.path.join(APP_RAW_TEXT_DIR, f"{raw_fn_base}_raw.txt")
            
            json_fn = scraper_utils.sanitize_filename(selected_character, extension=".json")
            if not json_fn: # Handle sanitize error
                json_output_file_label.config(text="Output JSON: (Error sanitizing name)", foreground="red")
                generate_json_button.config(state=tk.DISABLED)
                return
            json_filepath_disp = os.path.join(APP_CHARACTER_JSON_OUTPUT_DIR, json_fn)

            json_output_file_label.config(text=f"Output JSON: {json_filepath_disp}", foreground="black")
            can_gen = os.path.exists(raw_filepath) and not any_process_active
            generate_json_button.config(state=tk.NORMAL if can_gen else tk.DISABLED)
            if not os.path.exists(raw_filepath): generate_json_button.config(state=tk.DISABLED) # Explicitly disable
        else:
            json_output_file_label.config(text="Output JSON: (Select Character)", foreground="grey")
            generate_json_button.config(state=tk.DISABLED)
    except (tk.TclError, NameError, AttributeError): pass


def start_generate_single_json_gui(): # Renamed
    global json_gen_single_thread
    if not (json_character_var and model_selection_var): return
    selected_character = json_character_var.get(); selected_model = model_selection_var.get()
    if not (selected_character and selected_character in ACTIVE_CHARACTER_LIST): messagebox.showerror("Error", "Select character."); return
    if not (selected_model and selected_model in AVAILABLE_MODELS_MAIN): messagebox.showerror("Error", "Select AI model."); return
    if not GOOGLE_AI_LIB_PRESENT: messagebox.showerror("Error", "Google AI library missing."); return
    if not google_api_key_main: messagebox.showerror("API Key Error", "Google API Key missing."); return

    raw_filename_base = scraper_utils.sanitize_filename(selected_character, extension="")
    raw_filepath = os.path.join(APP_RAW_TEXT_DIR, f"{raw_filename_base}_raw.txt")
    if not os.path.exists(raw_filepath): messagebox.showerror("Error", f"Raw text file not found:\n{raw_filepath}"); return
    if json_gen_single_thread and json_gen_single_thread.is_alive(): messagebox.showinfo("Busy", "Single JSON gen already running."); return

    disable_buttons_gui()
    if status_var: status_var.set(f"Status: Starting JSON generation for {selected_character}...")

    def single_json_thread_target(): # Wrapper
        success_sj, message_sj, final_name_sj, out_fpath_sj = json_manager.process_single_character_json(
            google_api_key_main, selected_character, raw_filepath, selected_model
        )
        if root and root.winfo_exists():
            root.after(0, lambda: (
                status_var.set(f"Status: {message_sj}") if status_var else None,
                messagebox.showinfo("Single JSON Result", message_sj) if success_sj else messagebox.showerror("Single JSON Error", message_sj),
                load_current_json_for_tuning_gui() if success_sj and tune_character_var and tune_character_var.get() == final_name_sj and callable(load_current_json_for_tuning_gui) else None,
                enable_buttons_gui()
            ))
        global json_gen_single_thread # To clear handle
        json_gen_single_thread = None

    json_gen_single_thread = threading.Thread(target=single_json_thread_target, daemon=True)
    json_gen_single_thread.start()


def start_generate_all_json_gui(): # Renamed
    global json_gen_all_thread, cancel_generate_all_button, json_action_frame
    if not model_selection_var: return
    selected_model = model_selection_var.get()
    if not (selected_model and selected_model in AVAILABLE_MODELS_MAIN): messagebox.showerror("Error", "Select AI model."); return
    if not GOOGLE_AI_LIB_PRESENT: messagebox.showerror("Error", "Google AI library missing."); return
    if not google_api_key_main: messagebox.showerror("API Key Error", "Google API Key missing."); return
    
    chars_to_process_all = [
        os.path.splitext(f)[0].replace("_raw", "")
        for f in os.listdir(APP_RAW_TEXT_DIR)
        if os.path.isfile(os.path.join(APP_RAW_TEXT_DIR, f)) and f.lower().endswith("_raw.txt")
    ]
    if not chars_to_process_all: messagebox.showinfo("No Files", "No raw text files found."); return
    if not messagebox.askyesno("Confirm", f"Generate/Update JSON for {len(chars_to_process_all)} characters?"): return
    if json_gen_all_thread and json_gen_all_thread.is_alive(): messagebox.showinfo("Busy", "'Generate All' is running."); return

    disable_buttons_gui()
    if status_var: status_var.set(f"Status: Starting Generate All JSON ({len(chars_to_process_all)} files)...")
    if cancel_generate_all_button and json_action_frame: # Show cancel button
        if cancel_generate_all_button.master != json_action_frame: cancel_generate_all_button.pack(in_=json_action_frame, side=tk.LEFT, padx=(10,0))
        else: cancel_generate_all_button.pack(side=tk.LEFT, padx=(10,0))
        cancel_generate_all_button.config(text="Cancel Generate All", state=tk.NORMAL)

    def all_json_thread_target(): # Wrapper
        processed_all_j, success_all_j, errors_all_j, stopped_all_j = json_manager.process_all_characters_json_generation(
            google_api_key_main, chars_to_process_all, selected_model,
            stop_generate_all_json_flag, # Pass the stop event
            gui_progress_updater # Pass the GUI progress callback
        )
        final_msg_all_j = f"Status: Generate All {'STOPPED' if stopped_all_j else 'COMPLETE'}. Processed: {processed_all_j}, Success: {success_all_j}, Errors: {errors_all_j}."
        if root and root.winfo_exists():
            root.after(0, lambda: (
                status_var.set(final_msg_all_j) if status_var else None,
                messagebox.showwarning("Generate All", final_msg_all_j) if errors_all_j > 0 or stopped_all_j else messagebox.showinfo("Generate All", final_msg_all_j),
                enable_buttons_gui(),
                load_character_list_from_files_gui(), # Refresh list in case new files were made (though less likely here)
                update_all_character_dropdowns_gui()
            ))
        global json_gen_all_thread # To clear handle
        json_gen_all_thread = None
    
    stop_generate_all_json_flag.clear() # Clear before starting
    json_gen_all_thread = threading.Thread(target=all_json_thread_target, daemon=True)
    json_gen_all_thread.start()


def stop_generate_all_json_gui(): # Renamed
    if json_gen_all_thread and json_gen_all_thread.is_alive():
        print("GUI: >>> Sending Stop Signal to Generate All JSON... <<<")
        stop_generate_all_json_flag.set()
        if cancel_generate_all_button and cancel_generate_all_button.winfo_exists():
            try: cancel_generate_all_button.config(text="Stopping...", state=tk.DISABLED)
            except tk.TclError: pass
    else: print("GUI: No active 'Generate All JSON' process to stop.")


# --- Tab 4: Fine-Tune JSON Callbacks ---
def load_current_json_for_tuning_gui(): # Renamed
    global original_loaded_json_str, proposed_tuned_json_data # Manage state
    # ... (Logic mostly same, using APP_CHARACTER_JSON_OUTPUT_DIR and scraper_utils.sanitize_filename) ...
    if not (tune_character_var and current_json_display and tuning_instruction_input and proposed_json_display and tune_status_var and tune_preview_button): return
    selected_char = tune_character_var.get()
    # Clear previous state
    current_json_display.config(state=tk.NORMAL); current_json_display.delete('1.0', END); current_json_display.config(state=tk.DISABLED)
    tuning_instruction_input.delete('1.0', END)
    proposed_json_display.config(state=tk.NORMAL); proposed_json_display.delete('1.0', END); proposed_json_display.config(state=tk.DISABLED)
    original_loaded_json_str = None; proposed_tuned_json_data = None
    disable_tuning_buttons_gui()

    if not selected_char or selected_char == "(No Characters Found)":
        current_json_display.config(state=tk.NORMAL); current_json_display.insert('1.0', "(Select valid character)"); current_json_display.config(state=tk.DISABLED)
        tune_status_var.set("Select character."); return
    
    json_fn_load = scraper_utils.sanitize_filename(selected_char, ".json")
    if not json_fn_load: messagebox.showerror("Error", f"Invalid filename for '{selected_char}'."); tune_status_var.set("Error."); return
    filepath_load = os.path.join(APP_CHARACTER_JSON_OUTPUT_DIR, json_fn_load)

    if not os.path.exists(filepath_load):
        current_json_display.config(state=tk.NORMAL); current_json_display.delete('1.0', END)
        current_json_display.insert('1.0', f"JSON file not found for '{selected_char}'.\nExpected:\n{filepath_load}"); current_json_display.config(state=tk.DISABLED)
        tune_status_var.set(f"Error: JSON file not found."); return
    try:
        with open(filepath_load, 'r', encoding='utf-8') as f: original_loaded_json_str = f.read()
        json_data = json.loads(original_loaded_json_str)
        pretty_json = json.dumps(json_data, indent=2, ensure_ascii=False)
        current_json_display.config(state=tk.NORMAL); current_json_display.insert('1.0', pretty_json); current_json_display.config(state=tk.DISABLED)
        tune_status_var.set(f"Loaded JSON for {selected_char}.")
        any_proc_active = any(t and t.is_alive() for t in [scrape_all_thread, json_gen_single_thread, json_gen_all_thread, json_tune_thread])
        if not any_proc_active and tune_preview_button and tune_preview_button.winfo_exists():
             tune_preview_button.config(state=tk.NORMAL)
    except Exception as e:
        messagebox.showerror("Load Error", f"Failed to load/parse JSON:\n{e}")
        current_json_display.config(state=tk.NORMAL); current_json_display.delete('1.0', END); current_json_display.insert('1.0', f"Error loading:\n{e}"); current_json_display.config(state=tk.DISABLED)
        tune_status_var.set(f"Error loading JSON."); original_loaded_json_str = None; disable_tuning_buttons_gui()


def preview_ai_tuning_gui():
    global json_tune_thread
    # ... (Validation as before) ...
    if not (tune_character_var and tuning_instruction_input and tune_model_var): return
    selected_char = tune_character_var.get(); instruction = tuning_instruction_input.get("1.0", END).strip(); tune_model = tune_model_var.get()
    if not (selected_char and selected_char != "(No Characters Found)" and instruction and tune_model and tune_model in AVAILABLE_MODELS_MAIN and original_loaded_json_str):
        messagebox.showerror("Error", "Ensure character, JSON, instruction, and model are set."); return
    if not GOOGLE_AI_LIB_PRESENT or not google_api_key_main: messagebox.showerror("API Error", "Google AI/Key not ready."); return
    if json_tune_thread and json_tune_thread.is_alive(): messagebox.showinfo("Busy", "Tuning process already running."); return

    raw_filepath_tune = os.path.join(APP_RAW_TEXT_DIR, f"{scraper_utils.sanitize_filename(selected_char, '')}_raw.txt")
    raw_content_tune = "Source raw text not available."
    if os.path.exists(raw_filepath_tune):
        try:
            with open(raw_filepath_tune, 'r', encoding='utf-8') as f: raw_content_tune = f.read()
        except Exception: messagebox.showwarning("Warning", "Could not read raw text file for tuning context.")
    else: messagebox.showwarning("Warning", "Raw text file not found for tuning context.")

    disable_buttons_gui(); disable_tuning_buttons_gui(keep_load=False)
    if tune_status_var: tune_status_var.set("Status: Sending tuning request to AI...")

    def tune_thread_target(): # Wrapper
        global proposed_tuned_json_data, json_tune_thread # To set global and clear handle
        # Call ai_processor function
        ai_result = ai_processor.tune_json_with_ai(
            google_api_key_main, original_loaded_json_str, raw_content_tune,
            instruction, tune_model, FINAL_JSON_SCHEMA_STRING_MAIN
        )
        final_error_msg_tune = None
        local_proposed_data_tune = None
        context_string_on_error_tune = ai_result.get("raw_response", "Raw AI output unavailable (tuning).") if isinstance(ai_result, dict) else str(ai_result)

        if isinstance(ai_result, dict) and 'error' not in ai_result:
            # Successful parse from AI, now ensure schema using updater_v3.py's schema definition
            print("GUI: AI tuning returned data, ensuring schema...")
            if callable(scraper_utils.ensure_schema_keys) and TOP_LEVEL_SCHEMA_PROPERTIES_MAIN:
                local_proposed_data_tune = scraper_utils.ensure_schema_keys(ai_result, TOP_LEVEL_SCHEMA_PROPERTIES_MAIN)
                print("GUI: Schema enforcement on tuned data complete.")
            else:
                local_proposed_data_tune = ai_result # Use as is if schema tool or properties missing
                print("GUI WARN: Schema enforcement tool or TOP_LEVEL_SCHEMA_PROPERTIES_MAIN missing for tuning result.")
        elif isinstance(ai_result, dict): # Error dict from AI
            final_error_msg_tune = ai_result.get('error', 'Unknown AI tuning error') + f" Details: {ai_result.get('details', '')}"
            print(f"GUI: AI Tuning Error: {final_error_msg_tune}")
        else: # Unexpected return
            final_error_msg_tune = "Unexpected data type from AI tuning."
            print(f"GUI: AI Tuning Error - Unexpected data: {ai_result}")

        proposed_tuned_json_data = local_proposed_data_tune # Set global

        # --- Update GUI after tuning attempt ---
        if root and root.winfo_exists():
            root.after(0, lambda: update_tuning_preview_ui(local_proposed_data_tune, final_error_msg_tune, context_string_on_error_tune))
        json_tune_thread = None # Clear handle

    json_tune_thread = threading.Thread(target=tune_thread_target, daemon=True)
    json_tune_thread.start()


def update_tuning_preview_ui(final_data, final_error_msg, context_string_on_error):
    """Helper to update tuning tab UI after AI call - CALLED VIA root.after"""
    enable_buttons_gui() # Enable general buttons first
    if final_data and final_error_msg is None: # Success
        try:
            pretty_json = json.dumps(final_data, indent=2, ensure_ascii=False)
            if proposed_json_display and proposed_json_display.winfo_exists():
                proposed_json_display.config(state=tk.NORMAL); proposed_json_display.delete('1.0', END)
                proposed_json_display.insert('1.0', pretty_json); proposed_json_display.config(state=tk.DISABLED)
            if tune_save_button and tune_save_button.winfo_exists(): tune_save_button.config(state=tk.NORMAL)
            if tune_discard_button and tune_discard_button.winfo_exists(): tune_discard_button.config(state=tk.NORMAL)
            if tune_status_var: tune_status_var.set("Status: Review proposal and Save or Discard.")
        except Exception as display_e:
            if tune_status_var: tune_status_var.set(f"Status: Error displaying proposal: {display_e}")
            disable_tuning_buttons_gui(keep_load=True) # Keep load enabled
    else: # Failure
        if not final_error_msg: final_error_msg = "Unknown tuning error."
        if tune_status_var: tune_status_var.set(f"Status: AI tuning failed. {final_error_msg}")
        if proposed_json_display and proposed_json_display.winfo_exists():
            proposed_json_display.config(state=tk.NORMAL); proposed_json_display.delete('1.0', END)
            error_display_text = f"Tuning Error:\n{final_error_msg}"
            snippet = (context_string_on_error or "")[:500]
            if snippet and snippet != "Raw AI output unavailable (tuning).":
                 error_display_text += f"\n\n--- Faulty/Raw AI Snippet ---\n{snippet}..."
            proposed_json_display.insert('1.0', error_display_text); proposed_json_display.config(state=tk.DISABLED)
        messagebox.showerror("AI Tuning Error", f"AI tuning failed:\n{final_error_msg}", parent=root)
        disable_tuning_buttons_gui(keep_load=True)


def save_tuned_json_gui(): # Renamed
    if not (tune_character_var and isinstance(proposed_tuned_json_data, dict)):
        messagebox.showerror("Error", "No valid character or tuned data to save."); return
    selected_char = tune_character_var.get()
    json_fn_save = scraper_utils.sanitize_filename(selected_char, ".json") # Use util
    if not json_fn_save: messagebox.showerror("Error", "Invalid filename."); return
    filepath_save = os.path.join(APP_CHARACTER_JSON_OUTPUT_DIR, json_fn_save)

    disable_buttons_gui(); disable_tuning_buttons_gui()
    try:
        with open(filepath_save, 'w', encoding='utf-8') as f:
            json.dump(proposed_tuned_json_data, f, indent=2, ensure_ascii=False)
        if callable(load_current_json_for_tuning_gui): load_current_json_for_tuning_gui() # Reload
        if tune_status_var: tune_status_var.set(f"Status: Saved tuned JSON for {selected_char}.")
        messagebox.showinfo("Save Successful", f"Tuned JSON saved for {selected_char}.")
    except Exception as e:
        messagebox.showerror("Save Error", f"Failed to save tuned JSON:\n{e}")
        if tune_status_var: tune_status_var.set(f"Status: Error saving.")
    finally: # Ensure buttons are re-enabled even on error during save file op
        enable_buttons_gui()


def discard_tuned_changes_gui(): # Renamed
    global proposed_tuned_json_data # This is state for the GUI
    if not (tuning_instruction_input and proposed_json_display and tune_save_button and tune_discard_button and tune_preview_button): return
    tuning_instruction_input.delete('1.0', END)
    proposed_json_display.config(state=tk.NORMAL); proposed_json_display.delete('1.0', END); proposed_json_display.config(state=tk.DISABLED)
    tune_save_button.config(state=tk.DISABLED); tune_discard_button.config(state=tk.DISABLED)
    tune_preview_button.config(state=tk.NORMAL if original_loaded_json_str else tk.DISABLED)
    if tune_status_var: tune_status_var.set("Status: Discarded proposed changes.")
    proposed_tuned_json_data = None

def disable_tuning_buttons_gui(keep_load=False): # Renamed
    # GUI vars global to this script
    widgets_to_act = [tune_preview_button, tune_save_button, tune_discard_button, tune_model_combobox]
    load_btn_state = tk.DISABLED if not keep_load else tk.NORMAL
    try:
        def set_state_tune_gui(widget, state): # Renamed
            if widget and widget.winfo_exists():
                try:
                    if isinstance(widget, ttk.Combobox) and state == tk.NORMAL: widget.config(state="readonly")
                    else: widget.config(state=state)
                except tk.TclError: pass
        if tune_load_button: set_state_tune_gui(tune_load_button, load_btn_state)
        for w_tune in widgets_to_act: set_state_tune_gui(w_tune, tk.DISABLED)
    except (tk.TclError, NameError, AttributeError): pass


def update_instructions_gui(event=None): # Renamed
    if notebook is None or instruction_label is None: return
    try:
        current_tab_index = notebook.index(notebook.select())
        instruction_text = TAB_INSTRUCTIONS.get(current_tab_index, DEFAULT_INSTRUCTION)
        if instruction_label.winfo_exists(): instruction_label.config(text=instruction_text)
    except (tk.TclError, Exception): pass # Graceful fail

def refresh_application_ui_state_gui(): # Renamed, this is the top-level refresh
    print("\nGUI: --- Refreshing Application UI State ---")
    global google_api_key_main, AVAILABLE_MODELS_MAIN, DEFAULT_MODEL_MAIN # Use main script's model info

    if not root or not root.winfo_exists(): print("GUI Refresh: Root window not available."); return
    
    enable_buttons_gui() # First, try to enable everything that might be stuck
    load_character_list_from_files_gui() # Reload character list from disk
    update_all_character_dropdowns_gui() # Update all dropdowns with new list

    # Re-fetch available AI Models and reload settings
    # This relies on GOOGLE_AI_LIB_PRESENT being accurate
    if GOOGLE_AI_LIB_PRESENT and google_api_key_main:
        print("GUI:   Re-fetching available AI models...")
        # ai_processor.list_available_models_from_ai returns a list
        AVAILABLE_MODELS_MAIN = ai_processor.list_available_models_from_ai(google_api_key_main)
        if AVAILABLE_MODELS_MAIN: # Update default if list is not empty
             if "gemini-1.5-pro-latest" in AVAILABLE_MODELS_MAIN: DEFAULT_MODEL_MAIN = "gemini-1.5-pro-latest"
             elif "gemini-1.5-flash-latest" in AVAILABLE_MODELS_MAIN: DEFAULT_MODEL_MAIN = "gemini-1.5-flash-latest"
             else: DEFAULT_MODEL_MAIN = AVAILABLE_MODELS_MAIN[0]
        else: # Fallback if API returns no models
            print("GUI WARN: AI Provider returned no models. Using fallbacks.")
            AVAILABLE_MODELS_MAIN = ["gemini-1.5-pro-latest", "gemini-1.5-flash-latest"] # Hardcoded fallback
            DEFAULT_MODEL_MAIN = AVAILABLE_MODELS_MAIN[0]
        print(f"GUI:   Available models set ({len(AVAILABLE_MODELS_MAIN)}). Default: {DEFAULT_MODEL_MAIN}")
        load_settings_gui() # This will update comboboxes
    else: # Fallback if AI lib missing or no key
        print("GUI:   AI not available or key missing; setting model dropdowns to hardcoded fallback.")
        AVAILABLE_MODELS_MAIN = ["gemini-1.5-pro-latest", "gemini-1.5-flash-latest"]
        DEFAULT_MODEL_MAIN = AVAILABLE_MODELS_MAIN[0]
        load_settings_gui() # Attempt to set comboboxes with these fallbacks

    # Trigger UI updates that depend on character/model selections
    if callable(update_json_paths_gui): update_json_paths_gui()
    if callable(update_scraper_url_listbox_gui): update_scraper_url_listbox_gui()
    if callable(load_current_json_for_tuning_gui): load_current_json_for_tuning_gui()
    if status_var: status_var.set("Status: UI Refreshed.")
    if tune_status_var: tune_status_var.set("Load character JSON or enter instruction.")
    print("GUI: --- UI State Refresh Complete ---")


def copy_logs_to_clipboard():
    global root, log_buffer, status_var
    try:
        if root and root.winfo_exists():
            log_content = log_buffer.getvalue()
            if log_content:
                root.clipboard_clear()
                root.clipboard_append(log_content)
                print("Log content copied to clipboard.")
                if status_var:
                    status_var.set("Status: Logs copied to clipboard.")
            else:
                print("Log buffer is empty. Nothing to copy.")
                if status_var:
                    status_var.set("Status: Log buffer is empty.")
    except Exception as e:
        print(f"Error copying logs to clipboard: {e}")
        if status_var:
            status_var.set("Status: Error copying logs.")


# ==============================================================================
# == GUI SETUP FUNCTION (Main Script) ==
# ==============================================================================
def setup_gui_main(): # Renamed
    # All GUI widget variables are global to this main script
    global root, notebook, status_var, status_label, instruction_label, log_text, copy_log_button, stop_button, \
           scraper_character_var, scraper_character_dropdown, scraper_url_entry, scraper_url_listbox, \
           add_url_button, remove_url_button, scrape_button, scrape_all_button, action_frame_tab_manage, \
           progress_var, progress_bar, time_remaining_var, time_remaining_label, \
           add_char_name_entry, add_char_img_entry, add_char_icon_entry, add_char_wiki_entry, \
           add_char_tracker_entry, add_char_comic_entry, create_char_button, \
           json_character_var, json_character_dropdown, model_selection_var, model_combobox, \
           json_output_file_label, edit_prompt_button, open_prompt_dir_button, \
           generate_json_button, generate_all_json_button, \
           cancel_generate_all_button, json_action_frame, \
           tune_character_var, tune_character_dropdown, tune_load_button, current_json_display, \
           tuning_instruction_input, tune_model_var, tune_model_combobox, tune_preview_button, \
           proposed_json_display, tune_save_button, tune_discard_button, tune_status_var, \
           update_teamups_button, update_meta_button, update_info_button, \
           refresh_ui_button, ACTIVE_CHARACTER_LIST, AVAILABLE_MODELS_MAIN # Use main script's model list

    root = tk.Tk(); root.title("Marvel Rivals Updater v3.1 (Modular)"); root.geometry("950x800")
    style = ttk.Style(); style.configure("Grey.TLabel", foreground="grey"); style.configure("Stop.TButton", foreground="red", font=('TkDefaultFont', 10, 'bold'))

    top_bar_frame = ttk.Frame(root)
    top_bar_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=(5,0))
    refresh_ui_button = ttk.Button(top_bar_frame, text="Refresh UI State", command=refresh_application_ui_state_gui)
    refresh_ui_button.pack(side=tk.LEFT, padx=5)

    notebook = ttk.Notebook(root)
    notebook.pack(pady=(0,10), padx=10, fill=tk.BOTH, expand=True)
    notebook.bind("<<NotebookTabChanged>>", update_instructions_gui) # Use _gui suffixed
    root.after(100, update_instructions_gui) # Use _gui suffixed

    # --- Tab 1: Manage & Scrape ---
    manage_frame = ttk.Frame(notebook, padding="10"); notebook.add(manage_frame, text='1. Manage & Scrape'); manage_frame.columnconfigure(1, weight=1)
    ttk.Label(manage_frame, text="Character:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
    scraper_character_var = tk.StringVar(root)
    scraper_character_dropdown = ttk.Combobox(manage_frame, textvariable=scraper_character_var, values=ACTIVE_CHARACTER_LIST if ACTIVE_CHARACTER_LIST else ["(None)"], state="readonly", width=40)
    scraper_character_dropdown.grid(row=0, column=1, padx=5, pady=5, sticky="ew"); scraper_character_var.trace_add("write", update_scraper_url_listbox_gui)
    scraper_url_frame = ttk.LabelFrame(manage_frame, text="Manage Source URLs", padding="10")
    scraper_url_frame.grid(row=1, column=0, columnspan=2, padx=5, pady=(5,10), sticky="nsew"); scraper_url_frame.columnconfigure(1, weight=1)
    ttk.Label(scraper_url_frame, text="New URL:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
    scraper_url_entry = ttk.Entry(scraper_url_frame, width=50); scraper_url_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
    add_url_button = ttk.Button(scraper_url_frame, text="Add URL", command=add_scraper_url_gui); add_url_button.grid(row=0, column=2, padx=5, pady=5)
    ttk.Label(scraper_url_frame, text="Saved URLs:").grid(row=1, column=0, padx=5, pady=5, sticky="nw")
    scraper_listbox_frame = ttk.Frame(scraper_url_frame); scraper_listbox_frame.grid(row=1, column=1, columnspan=2, padx=5, pady=5, sticky="nsew")
    scraper_listbox_frame.rowconfigure(0, weight=1); scraper_listbox_frame.columnconfigure(0, weight=1)
    scraper_url_scrollbar = Scrollbar(scraper_listbox_frame, orient=tk.VERTICAL)
    scraper_url_listbox = Listbox(scraper_listbox_frame, height=5, width=60, yscrollcommand=scraper_url_scrollbar.set, exportselection=False, selectmode=SINGLE)
    scraper_url_scrollbar.config(command=scraper_url_listbox.yview); scraper_url_scrollbar.grid(row=0, column=1, sticky="ns"); scraper_url_listbox.grid(row=0, column=0, sticky="nsew")
    scraper_url_listbox.bind('<<ListboxSelect>>', on_listbox_select_gui)
    remove_url_button = ttk.Button(scraper_url_frame, text="Remove Selected URL", command=remove_scraper_url_gui, state=tk.DISABLED)
    remove_url_button.grid(row=2, column=1, columnspan=2, padx=5, pady=(0,5), sticky="e")
    action_frame_tab_manage = ttk.Frame(manage_frame); action_frame_tab_manage.grid(row=2, column=0, columnspan=2, pady=(10, 5), sticky="ew")
    btn_w = 20 # Adjusted button width
    scrape_button = ttk.Button(action_frame_tab_manage, text="Scrape Raw (Sel)", command=start_scrape_single_character_gui, width=btn_w); scrape_button.pack(side=tk.LEFT, padx=2, pady=2)
    scrape_all_button = ttk.Button(action_frame_tab_manage, text="Scrape Raw (ALL)", command=start_scrape_all_characters_gui, width=btn_w); scrape_all_button.pack(side=tk.LEFT, padx=2, pady=2)
    update_teamups_button = ttk.Button(action_frame_tab_manage, text="Upd Team-Ups (Wiki)", command=start_update_all_teamups_gui, width=btn_w); update_teamups_button.pack(side=tk.LEFT, padx=2, pady=2)
    update_meta_button = ttk.Button(action_frame_tab_manage, text="Upd Meta Stats (Site)", command=start_update_all_meta_stats_gui, width=btn_w); update_meta_button.pack(side=tk.LEFT, padx=2, pady=2)
    update_info_button = ttk.Button(action_frame_tab_manage, text="Upd Info Files (Site)", command=start_update_info_files_gui, width=btn_w); update_info_button.pack(side=tk.LEFT, padx=2, pady=2)
    stop_button = ttk.Button(action_frame_tab_manage, text="Stop Scrape All", command=stop_scrape_all_gui, style="Stop.TButton", width=btn_w)
    progress_frame = ttk.Frame(manage_frame); progress_frame.grid(row=3, column=0, columnspan=2, pady=5, sticky="ew")
    progress_var = tk.DoubleVar(); progress_bar = ttk.Progressbar(progress_frame, variable=progress_var, maximum=100); progress_bar.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
    time_remaining_var = tk.StringVar(); time_remaining_label = ttk.Label(progress_frame, textvariable=time_remaining_var, width=25, anchor="e"); time_remaining_label.pack(side=tk.RIGHT, padx=5)
    manage_frame.rowconfigure(4, weight=1)

    # --- Tab 2: Add Character ---
    add_char_frame = ttk.Frame(notebook, padding="10"); notebook.add(add_char_frame, text='2. Add Character'); add_char_frame.columnconfigure(1, weight=1)
    # ... (Tab 2 widgets as before, but command=create_new_character_gui)
    ttk.Label(add_char_frame, text="Enter details. Required fields *.").grid(row=0, column=0, columnspan=2, padx=5, pady=(5,10), sticky="w")
    ttk.Label(add_char_frame, text="Character Name*:").grid(row=1, column=0, padx=5, pady=3, sticky="w"); add_char_name_entry = ttk.Entry(add_char_frame, width=50); add_char_name_entry.grid(row=1, column=1, padx=5, pady=3, sticky="ew")
    ttk.Label(add_char_frame, text="Main Image Filename*:").grid(row=2, column=0, padx=5, pady=3, sticky="w"); add_char_img_entry = ttk.Entry(add_char_frame, width=50); add_char_img_entry.grid(row=2, column=1, padx=5, pady=3, sticky="ew")
    ttk.Label(add_char_frame, text="Icon Filename*:").grid(row=3, column=0, padx=5, pady=3, sticky="w"); add_char_icon_entry = ttk.Entry(add_char_frame, width=50); add_char_icon_entry.grid(row=3, column=1, padx=5, pady=3, sticky="ew")
    ttk.Label(add_char_frame, text="Wiki URL:").grid(row=4, column=0, padx=5, pady=3, sticky="w"); add_char_wiki_entry = ttk.Entry(add_char_frame, width=50); add_char_wiki_entry.grid(row=4, column=1, padx=5, pady=3, sticky="ew")
    ttk.Label(add_char_frame, text="Tracker URL:").grid(row=5, column=0, padx=5, pady=3, sticky="w"); add_char_tracker_entry = ttk.Entry(add_char_frame, width=50); add_char_tracker_entry.grid(row=5, column=1, padx=5, pady=3, sticky="ew")
    ttk.Label(add_char_frame, text="Comic Wiki URL:").grid(row=6, column=0, padx=5, pady=3, sticky="w"); add_char_comic_entry = ttk.Entry(add_char_frame, width=50); add_char_comic_entry.grid(row=6, column=1, padx=5, pady=3, sticky="ew")
    ttk.Label(add_char_frame, text=f"(Place files in: '{APP_IMAGE_DIR_CHECK}')", style="Grey.TLabel").grid(row=7, column=1, padx=5, pady=(0,10), sticky="w")
    create_char_button = ttk.Button(add_char_frame, text="Create New Character Files", command=create_new_character_gui, width=30); create_char_button.grid(row=8, column=1, padx=5, pady=10, sticky="e")
    add_char_frame.rowconfigure(9, weight=1)

    # --- Tab 3: Generate/Update JSON ---
    json_gen_frame = ttk.Frame(notebook, padding="10"); notebook.add(json_gen_frame, text='3. Generate/Update JSON'); json_gen_frame.columnconfigure(1, weight=1)
    # ... (Tab 3 widgets as before, commands point to _gui suffixed functions)
    ttk.Label(json_gen_frame, text="1. Character:").grid(row=0, column=0, padx=5, pady=(10,5), sticky="w")
    json_character_var = tk.StringVar(root); json_character_dropdown = ttk.Combobox(json_gen_frame, textvariable=json_character_var, values=ACTIVE_CHARACTER_LIST if ACTIVE_CHARACTER_LIST else ["(None)"], state="readonly", width=40)
    json_character_dropdown.grid(row=0, column=1, columnspan=2, padx=5, pady=(10,5), sticky="ew"); json_character_var.trace_add("write", update_json_paths_gui)
    ttk.Label(json_gen_frame, text="2. Select AI Model:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
    model_selection_var = tk.StringVar(root); model_combobox = ttk.Combobox(json_gen_frame, textvariable=model_selection_var, values=AVAILABLE_MODELS_MAIN, state="readonly", width=40) # Use MAIN models
    model_combobox.grid(row=1, column=1, columnspan=2, padx=5, pady=5, sticky="ew"); model_combobox.bind('<<ComboboxSelected>>', save_settings_gui)
    json_output_file_label = ttk.Label(json_gen_frame, text="Output JSON: (Select Character)", style="Grey.TLabel", relief=tk.SUNKEN, anchor="w", wraplength=700)
    json_output_file_label.grid(row=3, column=0, columnspan=3, padx=5, pady=2, sticky="ew")
    prompt_edit_frame = ttk.Frame(json_gen_frame); prompt_edit_frame.grid(row=4, column=0, columnspan=3, pady=(10,5), sticky="ew")
    edit_prompt_button = ttk.Button(prompt_edit_frame, text="Edit API Prompt Template", command=edit_api_prompt, width=28); edit_prompt_button.pack(side=tk.LEFT, padx=5)
    open_prompt_dir_button = ttk.Button(prompt_edit_frame, text="Open Script Folder", command=open_prompt_directory, width=28); open_prompt_dir_button.pack(side=tk.LEFT, padx=5)
    json_action_frame = ttk.Frame(json_gen_frame); json_action_frame.grid(row=5, column=0, columnspan=3, pady=(5, 20), sticky="ew")
    generate_json_button = ttk.Button(json_action_frame, text="Generate JSON (Sel)", command=start_generate_single_json_gui, state=tk.DISABLED, width=22); generate_json_button.pack(side=tk.LEFT, padx=(0,5))
    generate_all_json_button = ttk.Button(json_action_frame, text="Generate ALL JSON", command=start_generate_all_json_gui, width=22); generate_all_json_button.pack(side=tk.LEFT, padx=5)
    cancel_generate_all_button = ttk.Button(json_action_frame, text="Cancel Gen All", command=stop_generate_all_json_gui, style="Stop.TButton", width=22) # Not packed initially
    json_gen_frame.rowconfigure(6, weight=1)

    # --- Tab 4: Fine-Tune JSON ---
    tune_frame = ttk.Frame(notebook, padding="10"); notebook.add(tune_frame, text='4. Fine-Tune JSON'); # ... (Tab 4 setup as before, commands to _gui functions)
    tune_frame.columnconfigure(0, weight=1); tune_frame.columnconfigure(1, weight=1); tune_frame.rowconfigure(2, weight=1); tune_frame.rowconfigure(4, weight=1)
    tune_top_frame = ttk.Frame(tune_frame); tune_top_frame.grid(row=0, column=0, columnspan=2, padx=5, pady=5, sticky="ew"); tune_top_frame.columnconfigure(1, weight=1)
    ttk.Label(tune_top_frame, text="Character:").pack(side=tk.LEFT, padx=(0,5))
    tune_character_var = tk.StringVar(root); tune_character_dropdown = ttk.Combobox(tune_top_frame, textvariable=tune_character_var, values=ACTIVE_CHARACTER_LIST if ACTIVE_CHARACTER_LIST else ["(None)"], state="readonly", width=30)
    tune_character_dropdown.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True); tune_character_var.trace_add("write", lambda name, index, mode: load_current_json_for_tuning_gui())
    tune_load_button = ttk.Button(tune_top_frame, text="Load Current JSON", command=load_current_json_for_tuning_gui, width=20); tune_load_button.pack(side=tk.LEFT, padx=(10, 5))
    ttk.Label(tune_frame, text="Current JSON:").grid(row=1, column=0, padx=5, pady=(10,0), sticky="nw")
    current_json_frame = ttk.Frame(tune_frame); current_json_frame.grid(row=2, column=0, padx=5, pady=2, sticky="nsew"); current_json_frame.rowconfigure(0, weight=1); current_json_frame.columnconfigure(0, weight=1)
    current_json_scroll = Scrollbar(current_json_frame); current_json_scroll.pack(side=tk.RIGHT, fill=tk.Y)
    current_json_display = Text(current_json_frame, wrap=tk.WORD, height=10, width=50, yscrollcommand=current_json_scroll.set, state=tk.DISABLED, font=("Courier New", 9)); current_json_scroll.config(command=current_json_display.yview); current_json_display.pack(fill=tk.BOTH, expand=True)
    ttk.Label(tune_frame, text="Proposed JSON (AI Generated):").grid(row=1, column=1, padx=5, pady=(10,0), sticky="nw")
    proposed_json_frame = ttk.Frame(tune_frame); proposed_json_frame.grid(row=2, column=1, padx=5, pady=2, sticky="nsew"); proposed_json_frame.rowconfigure(0, weight=1); proposed_json_frame.columnconfigure(0, weight=1)
    proposed_json_scroll = Scrollbar(proposed_json_frame); proposed_json_scroll.pack(side=tk.RIGHT, fill=tk.Y)
    proposed_json_display = Text(proposed_json_frame, wrap=tk.WORD, height=10, width=50, yscrollcommand=proposed_json_scroll.set, state=tk.DISABLED, font=("Courier New", 9)); proposed_json_scroll.config(command=proposed_json_display.yview); proposed_json_display.pack(fill=tk.BOTH, expand=True)
    ttk.Label(tune_frame, text="Tuning Instruction:").grid(row=3, column=0, columnspan=2, padx=5, pady=(10,0), sticky="sw")
    instruction_frame = ttk.Frame(tune_frame); instruction_frame.grid(row=4, column=0, columnspan=2, padx=5, pady=2, sticky="nsew"); instruction_frame.rowconfigure(0, weight=1); instruction_frame.columnconfigure(0, weight=1)
    instruction_scroll = Scrollbar(instruction_frame); instruction_scroll.pack(side=tk.RIGHT, fill=tk.Y)
    tuning_instruction_input = Text(instruction_frame, wrap=tk.WORD, height=4, width=100, yscrollcommand=instruction_scroll.set); instruction_scroll.config(command=tuning_instruction_input.yview); tuning_instruction_input.pack(fill=tk.BOTH, expand=True)
    tune_controls_frame = ttk.Frame(tune_frame); tune_controls_frame.grid(row=5, column=0, columnspan=2, padx=5, pady=5, sticky="ew"); tune_controls_frame.columnconfigure(2, weight=1)
    ttk.Label(tune_controls_frame, text="AI Model (Tuning):").pack(side=tk.LEFT, padx=(0,5)); tune_model_var = tk.StringVar(root)
    tune_model_combobox = ttk.Combobox(tune_controls_frame, textvariable=tune_model_var, values=AVAILABLE_MODELS_MAIN, state="readonly", width=30); tune_model_combobox.pack(side=tk.LEFT, padx=5); tune_model_combobox.bind('<<ComboboxSelected>>', save_settings_gui)
    tune_preview_button = ttk.Button(tune_controls_frame, text="Preview AI Tuning", command=preview_ai_tuning_gui, width=20, state=tk.DISABLED); tune_preview_button.pack(side=tk.LEFT, padx=5)
    tune_action_buttons_frame = ttk.Frame(tune_controls_frame); tune_action_buttons_frame.pack(side=tk.RIGHT)
    tune_save_button = ttk.Button(tune_action_buttons_frame, text="Save Tuned JSON", command=save_tuned_json_gui, width=20, state=tk.DISABLED); tune_save_button.pack(side=tk.LEFT, padx=5)
    tune_discard_button = ttk.Button(tune_action_buttons_frame, text="Discard Changes", command=discard_tuned_changes_gui, width=20, state=tk.DISABLED); tune_discard_button.pack(side=tk.LEFT, padx=5)
    tune_status_var = tk.StringVar(value="Load character JSON to begin tuning.")
    tune_status_label = ttk.Label(tune_frame, textvariable=tune_status_var, relief=tk.SUNKEN, anchor="w", wraplength=880); tune_status_label.grid(row=6, column=0, columnspan=2, padx=5, pady=(10,0), sticky="sew")

    # --- Shared Bottom Section (Log, Status, Instructions) ---
    bottom_frame = ttk.Frame(root, padding=(10,0,10,10)); bottom_frame.pack(side=tk.BOTTOM, fill=tk.BOTH, expand=True)
    status_var = tk.StringVar(value="Status: Initializing..."); status_label = ttk.Label(bottom_frame, textvariable=status_var, relief=tk.SUNKEN, anchor="w", wraplength=880); status_label.pack(fill=tk.X, pady=(5,5), side=tk.TOP)
    instruction_label = ttk.Label(bottom_frame, text=DEFAULT_INSTRUCTION, relief=tk.FLAT, anchor="w", justify=tk.LEFT, padding=(5,5,5,5), wraplength=850); instruction_label.pack(fill=tk.X, pady=(0,5), side=tk.TOP)
    log_area_frame = ttk.Frame(bottom_frame); log_area_frame.pack(fill=tk.BOTH, expand=True, side=tk.TOP, pady=(0,5))
    log_frame = ttk.LabelFrame(log_area_frame, text="Logs", padding="5"); log_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    log_scrollbar_y = Scrollbar(log_frame, orient=tk.VERTICAL)
    log_text = Text(log_frame, height=8, width=100, wrap=tk.WORD, relief=tk.SUNKEN, borderwidth=1, font=("Courier New",9), background='#2E2E2E', foreground='#D4D4D4', insertbackground='white', yscrollcommand=log_scrollbar_y.set)
    log_scrollbar_y.config(command=log_text.yview); log_scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y); log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    copy_log_button = ttk.Button(log_area_frame, text="Copy Logs", command=copy_logs_to_clipboard); copy_log_button.pack(side=tk.LEFT, padx=(5,0), anchor="ne")

# ==============================================================================
# == MAIN EXECUTION BLOCK (updater_v3.py) ==
# ==============================================================================
if __name__ == "__main__":
    # --- 1. Initial Setup (Paths, Directories) ---
    # APP_ prefixed constants are defined at the top of this script
    os.makedirs(APP_CHARACTER_JSON_OUTPUT_DIR, exist_ok=True)
    os.makedirs(APP_CONFIG_DIR, exist_ok=True)
    os.makedirs(APP_RAW_TEXT_DIR, exist_ok=True)
    os.makedirs(os.path.join(APP_CHARACTER_JSON_OUTPUT_DIR, "failed"), exist_ok=True)
    os.makedirs(APP_INFO_OUTPUT_DIR, exist_ok=True)

    # --- 2. Initialize json_manager with paths and configurations ---
    json_manager.init_json_manager_paths_and_config(
        APP_SCRIPT_DIR, APP_BASE_DIR, APP_RAW_TEXT_DIR, APP_CHARACTER_JSON_OUTPUT_DIR, APP_INFO_OUTPUT_DIR,
        CORE_GENERATED_KEYS_MAIN, PRESERVED_SECTIONS_DURING_CORE_GEN_MAIN, PRESERVED_NESTED_FIELDS_MAIN,
        CHARACTER_BASE_SPEEDS_MAIN, FINAL_JSON_SCHEMA_STRING_MAIN, TOP_LEVEL_SCHEMA_PROPERTIES_MAIN,
        APP_COLOR_POOLS_FILE
    )
    # Pass API_CALL_DELAY_SECONDS to json_manager if it needs it, or json_manager uses its own default
    # setattr(json_manager, 'API_CALL_DELAY_SECONDS', APP_API_CALL_DELAY_SECONDS) # Example if needed


    # --- 3. Load Initial Data using config_manager ---
    character_urls_main = config_manager.load_character_urls() # Populate global
    load_character_list_from_files_gui() # Populates ACTIVE_CHARACTER_LIST

    # --- 4. Build GUI ---
    print("GUI: Setting up GUI..."); setup_gui_main(); print("GUI: GUI Setup Complete.")

    # --- 5. Setup Log Redirection ---
    log_redirector = TextRedirector(log_text) # log_text is now a global GUI var
    sys.stdout = log_redirector
    sys.stderr = log_redirector
    print("="*40 + "\nMarvel Rivals Updater v3.1 (Modular)\n" + "="*40 + "\n")
    print(f"Base Dir: {APP_BASE_DIR}\nJSON Out: {APP_CHARACTER_JSON_OUTPUT_DIR}\nRaw Text: {APP_RAW_TEXT_DIR}\n")
    print(f"--- Lib Status ---\nGoogle AI: {GOOGLE_AI_LIB_PRESENT}\nDotEnv: {DOTENV_PRESENT}")

    # --- 6. Initial GUI Population & API Checks ---
    print("GUI: Populating initial dropdowns...")
    update_all_character_dropdowns_gui(initial_setup=True)

    def initial_api_and_settings_check(): # Renamed
        global google_api_key_main, AVAILABLE_MODELS_MAIN, DEFAULT_MODEL_MAIN # Use main script's vars
        print("\nGUI: Initializing API & Settings...")
        if not GOOGLE_AI_LIB_PRESENT:
            print("GUI ERROR: Google AI library not available for API calls.")
            # Fallback models for GUI if AI lib is missing
            AVAILABLE_MODELS_MAIN = ["gemini-1.5-pro-latest", "gemini-1.5-flash-latest"] # Hardcoded fallback
            DEFAULT_MODEL_MAIN = AVAILABLE_MODELS_MAIN[0]
            if status_var: status_var.set("Status: Google AI Lib Missing! AI features disabled.")
        elif not google_api_key_main:
            print("GUI ERROR: GOOGLE_API_KEY not found.")
            AVAILABLE_MODELS_MAIN = ["gemini-1.5-pro-latest", "gemini-1.5-flash-latest"] # Hardcoded fallback
            DEFAULT_MODEL_MAIN = AVAILABLE_MODELS_MAIN[0]
            if status_var: status_var.set("Status: Google API Key Missing! AI features limited.")
        else:
            print("GUI: Google API Key found.")
            print("GUI: Fetching available AI models via ai_processor...")
            # This list is now global to updater_v3.py
            AVAILABLE_MODELS_MAIN = ai_processor.list_available_models_from_ai(google_api_key_main)
            if AVAILABLE_MODELS_MAIN:
                 if "gemini-1.5-pro-latest" in AVAILABLE_MODELS_MAIN: DEFAULT_MODEL_MAIN = "gemini-1.5-pro-latest"
                 elif "gemini-1.5-flash-latest" in AVAILABLE_MODELS_MAIN: DEFAULT_MODEL_MAIN = "gemini-1.5-flash-latest"
                 else: DEFAULT_MODEL_MAIN = AVAILABLE_MODELS_MAIN[0]
                 print(f"GUI: AI Models fetched: {len(AVAILABLE_MODELS_MAIN)}. Default: {DEFAULT_MODEL_MAIN}")
            else: # Fallback if API returns no models
                print("GUI WARN: AI Processor returned no models. Using hardcoded fallbacks.")
                AVAILABLE_MODELS_MAIN = ["gemini-1.5-pro-latest", "gemini-1.5-flash-latest"]
                DEFAULT_MODEL_MAIN = AVAILABLE_MODELS_MAIN[0]
        
        print("GUI: Loading UI settings (model selections)...")
        load_settings_gui() # This will use AVAILABLE_MODELS_MAIN and DEFAULT_MODEL_MAIN to set comboboxes

        print("GUI: Triggering post-initialization UI updates...")
        if callable(update_json_paths_gui): update_json_paths_gui()
        if callable(load_current_json_for_tuning_gui): load_current_json_for_tuning_gui()
        print("GUI: --- Initialization Complete ---")
        if status_var: status_var.set("Status: Ready.")

    if root:
        print("GUI: Scheduling Initial API Checks & Starting GUI Main Loop...")
        root.after(200, initial_api_and_settings_check) # Slightly longer delay
        root.mainloop()
    else:
        print("GUI FATAL ERROR: Failed to create main Tkinter window.")
        sys.exit(1)
