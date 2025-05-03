# -*- coding: utf-8 -*-
# Marvel Rivals Updater v3.0 - Based on v1.2 + Enhancements + Fine-Tuning

# ==============================================================================
# == IMPORTS ==
# ==============================================================================
from tkinter import ttk, messagebox, Listbox, Scrollbar, END, SINGLE, Text, Toplevel, Label, Entry, Frame, Button # Added Button explicitly
import tkinter as tk
import requests
from bs4 import BeautifulSoup
import os
import re
import threading
import json
import time
import sys
import io
import datetime
import random
import subprocess # For opening files/dirs
import shutil 
import functools     
import urllib.parse 

# --- Google AI Library ---
try:
    import google.generativeai as genai
    from google.api_core import exceptions as google_exceptions
    GOOGLE_AI_AVAILABLE = True
except ImportError:
    print("ERROR: google-generativeai library not found. Please install it: pip install google-generativeai")
    GOOGLE_AI_AVAILABLE = False
    # Define dummy exceptions if library is missing
    class google_exceptions:
        class GoogleAPIError(Exception): pass
        class PermissionDenied(GoogleAPIError): pass
        class ResourceExhausted(GoogleAPIError): pass
        class InvalidArgument(GoogleAPIError): pass
        class FailedPrecondition(GoogleAPIError): pass
        class InternalServerError(GoogleAPIError): pass

# --- DotEnv for API Key ---
try:
    from dotenv import load_dotenv
    DOTENV_AVAILABLE = True
except ImportError:
    print("WARNING: python-dotenv library not found. .env file loading disabled. Install with: pip install python-dotenv")
    DOTENV_AVAILABLE = False
    def load_dotenv(): pass

# --- Tab-Specific Instructions ---
TAB_INSTRUCTIONS = {
    0: """Tab 1: Manage & Scrape
    1. Select Character: Choose a hero from the dropdown.
    2. Manage URLs: Add/Remove web page URLs (wiki, tracker) used for scraping data for the selected character.
    3. Scrape Raw Text: Click buttons to fetch raw text from the saved URLs (for selected char or all). This creates *_raw.txt files needed for Tab 3.
    4. Update Meta/Info: Use dedicated buttons to fetch latest tracker stats or official site news/patches (updates JSON/info files directly).""",
    1: """Tab 2: Add Character
    1. Fill Form: Enter the required (*) and optional details accurately.
    2. Image/Icon Files: Provide just the FILENAMES (e.g., 'Hulk_Icon.png'). Place the actual image files in the 'images' folder.
    3. Recommended Sizes: Icons ~64x64px, Main Card Images ~550x309px (will be cropped/scaled).
    4. Create Files: This generates the base JSON, adds to config files, and saves provided URLs.""",
    2: """Tab 3: Generate/Update JSON
    1. Select Character: Choose the character whose *_raw.txt file you want to process.
    2. Select AI Model: 'gemini-1.5-flash' is recommended for balance of speed/cost/accuracy. 'Pro' may be needed if Flash fails on complex characters.
    3. API Key: Requires a Google AI (Gemini) API Key. Create a '.env' file in the 'scraper' folder (see '.env.template') and add your key: GOOGLE_API_KEY=YOUR_API_KEY_HERE
    4. Generate: Creates/updates the final character JSON using AI, applying patches and preserving specific sections.""",
    3: """Tab 4: Fine-Tune JSON
    1. Select Character & Load JSON: Load the existing data for review.
    2. Enter Instruction: Clearly describe the specific change you want the AI to make to the loaded JSON.
    3. Select Model & Preview: AI will generate a proposed update based on your instruction.
    4. Save/Discard: Apply the proposed changes to the character's JSON file or discard them."""
}
DEFAULT_INSTRUCTION = "Select a tab to see instructions."

# ==============================================================================
# == CONFIGURATION & GLOBAL CONSTANTS ==
# ==============================================================================

# --- Load Environment Variables ---
if DOTENV_AVAILABLE:
    load_dotenv()
else:
    print("Skipping .env loading.")


# --- Define the Schema in Python ---
# (Load the schema string you already have defined)
FINAL_JSON_SCHEMA_STRING = """
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
""" # Keep your schema string definition here

# Load the schema string into a Python dictionary for validation
PYTHON_SCHEMA = None
try:
    # Attempt to load the schema string as JSON
    # NOTE: The provided schema string is NOT valid JSON itself because it contains comments and type unions like "string | null".
    # For jsonschema, you need a *valid* JSON schema definition.
    # We will SKIP strict validation for now and focus on key enforcement.
    # If you create a VALID JSON schema file, you can load it here:
    # with open('path/to/your/valid_schema.json', 'r') as f_schema:
    #     PYTHON_SCHEMA = json.load(f_schema)
    # print("Loaded PYTHON_SCHEMA for validation.")
    print("Skipping jsonschema loading - focusing on key enforcement.")
    # Let's define a simplified structure representing the top-level keys and their types for ensure_schema_keys
    # This is a manual representation, not full jsonschema
    SIMPLE_SCHEMA_STRUCTURE = {
        "name": "string", "role": "string", "stats": "object", "abilities": "array",
        "ultimate": "object", "passives": "array", "teamups": "array", "gameplay": "object",
        "lore_details": "object", "background": "object", "misc": "object",
        "meta_stats": "object", "data_sources": "object"
    } # Add nested structures as needed by ensure_schema_keys
except Exception as schema_load_e:
    print(f"FATAL ERROR: Could not prepare schema structure for validation/correction: {schema_load_e}")
    # Exit or raise exception if schema is critical and fails to load/parse




# --- Directories ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, os.pardir)) # Go up one level
RAW_TEXT_DIR = os.path.join(SCRIPT_DIR, "scraped_character_data") # Keep raw text local
CHARACTER_JSON_OUTPUT_DIR = os.path.join(BASE_DIR, "characters") # Output JSON to parent/characters
CONFIG_DIR = os.path.join(BASE_DIR, "config") # Config files in parent/config
IMAGE_DIR_CHECK = os.path.join(BASE_DIR, "images") # For user info


# --- Constants for Info File Scraping ---
INFO_CATEGORIES = {
    # "Internal Key": ("Output Filename", "URL")
    "Announcements": ("announcements.txt", "https://www.marvelrivals.com/announcements/"),
    "Balance Post": ("balance_post.txt", "https://www.marvelrivals.com/balancepost/"),
    "Dev Diaries": ("dev_diaries.txt", "https://www.marvelrivals.com/devdiaries/"),
    "Game Update": ("game_update.txt", "https://www.marvelrivals.com/gameupdate/"), # Patch Notes
    "News": ("news.txt", "https://www.marvelrivals.com/news/"),       # Latest News
    # Overview is tricky - cannot be easily scraped from these category pages. Omit for now.
    # "Overview": ("overview.txt", None),
}
INFO_OUTPUT_DIR = os.path.join(BASE_DIR, "info") # Define the output directory relative to base
MAX_ARTICLES_PER_CATEGORY = 5 # How many recent articles to scrape per category

# Keys primarily populated by the Wiki AI + Patch AI process
# Note: Nested fields like 'gameplay.achievements' are handled implicitly
# if the parent 'gameplay' is in this list.
CORE_GENERATED_KEYS = [
    "name",             # Generated, then corrected
    "role",             # Generated from wiki
    "stats",            # Base stats from wiki (speed/colors overwritten later)
    "abilities",        # Generated + Patched
    "ultimate",         # Generated + Patched
    "passives",         # Generated + Patched (if any)
    "gameplay",         # Contains achievements (from wiki), weaknesses (maybe preserve?), overview (PRESERVE)
    "lore_details"      # Contains bios (wiki), stories(wiki), balance(patch), official desc(wiki)
]

# Top-level keys to completely preserve from the old JSON during core generation,
# unless explicitly updated by their dedicated process (e.g., Meta Stats scraper).
# Sections like 'background', 'misc', 'teamups' are targeted for future dedicated scrapers or manual editing.
PRESERVED_SECTIONS_DURING_CORE_GEN = [
    "teamups",
    "background",
    "misc",
    "meta_stats",      # Only updated by the dedicated Meta Stats function
    "data_sources"     # Populated during 'Add Character' or potentially later
]

# Specific nested fields within CORE_GENERATED_KEYS that should ALSO be preserved.
# Use dot notation.
PRESERVED_NESTED_FIELDS = [
    "gameplay.strategy_overview", # Preserve manual strategy
    "gameplay.weaknesses",        # Preserve manual/wiki weaknesses for now
    "misc.community_buzz",        # Preserve manual entry OR the generated Reddit link
    "misc.helpful_links",         # Preserve manually added links
    "misc.quotes_link",           # Preserve manual link
    # Add other specific nested fields here if needed in the future
]

# --- Files ---
URL_DATA_FILE = os.path.join(SCRIPT_DIR, 'saved_character_urls.json') # v1.2 URL file
COLOR_POOLS_FILE = os.path.join(SCRIPT_DIR, 'character_color_pools.json')
API_PROMPT_TEMPLATE_FILE = os.path.join(SCRIPT_DIR, 'api_prompt_v3_template.txt')
DEFAULT_PROMPT_FILE = os.path.join(SCRIPT_DIR, 'api_prompt_v3_default.txt')
SETTINGS_FILE = os.path.join(SCRIPT_DIR, 'updater_settings.json')
API_PROMPT_TUNING_FILE = os.path.join(SCRIPT_DIR, 'api_prompt_v3_tuning.txt')
CHAR_IMG_CONFIG = 'character_images.json' # Relative to CONFIG_DIR
CHAR_ICON_CONFIG = 'character_icons.json' # Relative to CONFIG_DIR

# --- Settings ---
USER_AGENT = 'RivalsUpdater/3.0 (Manual Use; Learning Project)'
SCRAPE_DELAY_SECONDS = 1
API_CALL_DELAY_SECONDS = 1.5
ESTIMATED_SECONDS_PER_CHAR_SCRAPE = 4
FALLBACK_MODELS = ["gemini-1.5-pro-latest", "gemini-1.5-flash-latest"]
FALLBACK_DEFAULT_MODEL = FALLBACK_MODELS[0]


CHARACTER_BASE_SPEEDS = {
    "Adam Warlock": "6 m/s",
    "Black Panther": "7 m/s", # Note BP higher
    "Black Widow": "6 m/s",
    "Captain America": "6 m/s",
    "Cloak and Dagger": "6 m/s", # Assuming base for both
    "Doctor Strange": "6 m/s",
    "Groot": "6 m/s",
    "Hawkeye": "6 m/s",
    "Hela": "6 m/s",
    "Hulk": "6 m/s",
    "Human Torch": "6 m/s",
    "Invisible Woman": "6 m/s",
    "Iron Fist": "6 m/s",
    "Iron Man": "6 m/s",
    "Jeff the Land Shark": "6 m/s",
    "Loki": "6 m/s",
    "Luna Snow": "6 m/s",
    "Magik": "6 m/s",
    "Magneto": "6 m/s",
    "Mantis": "6 m/s",
    "Mister Fantastic": "6 m/s", # Name corrected
    "Moon Knight": "6 m/s",
    "Namor": "6 m/s",
    "Peni Parker": "6 m/s",
    "Psylocke": "6 m/s",
    "Punisher": "6 m/s", # Name corrected
    "Rocket Raccoon": "6 m/s",
    "Scarlet Witch": "6 m/s",
    "Spider-Man": "6 m/s", # Name corrected
    "Squirrel Girl": "6 m/s",
    "Star-Lord": "6 m/s", # Name corrected
    "Storm": "6 m/s",
    "The Thing": "6 m/s",
    "Thor": "6 m/s",
    "Venom": "6 m/s",
    "Winter Soldier": "6 m/s",
    "Wolverine": "7 m/s" # Note Wolverine higher
}

# --- Final Target JSON Schema (UPDATED with meta_stats and expanded misc) ---
# (Schema string remains the same as provided before)
FINAL_JSON_SCHEMA_STRING = """
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

# --- Google API Key ---
google_api_key = os.environ.get("GOOGLE_API_KEY")

# --- Global Variables ---
ACTIVE_CHARACTER_LIST = []
character_urls = {} # Loaded from URL_DATA_FILE
log_buffer = io.StringIO()
stop_scrape_all_flag = threading.Event()
AVAILABLE_MODELS = FALLBACK_MODELS
DEFAULT_MODEL = FALLBACK_DEFAULT_MODEL
# Threads
scrape_all_thread = None
json_gen_all_thread = None
json_gen_single_thread = None
json_tune_thread = None
# GUI Vars (Initialize to None, assigned in setup_gui)
root = None; notebook = None; status_var = None; log_text = None; copy_log_button = None;
scraper_character_var = None; scraper_character_dropdown = None; scraper_url_entry = None; scraper_url_listbox = None; add_url_button = None; remove_url_button = None; scrape_button = None; scrape_all_button = None; action_frame_tab1 = None; progress_var = None; progress_bar = None; time_remaining_var = None; time_remaining_label = None; stop_button = None; status_label = None # Added status_label here
add_char_name_entry = None; add_char_img_entry = None; add_char_icon_entry = None; add_char_wiki_entry = None; add_char_tracker_entry = None; add_char_comic_entry = None; create_char_button = None;
json_character_var = None; json_character_dropdown = None; model_selection_var = None; model_combobox = None; json_output_file_label = None; edit_prompt_button = None; open_prompt_dir_button = None; generate_json_button = None; generate_all_json_button = None;
tune_character_var = None; tune_character_dropdown = None; tune_load_button = None; current_json_display = None; tuning_instruction_input = None; tune_model_var = None; tune_model_combobox = None; tune_preview_button = None; proposed_json_display = None; tune_save_button = None; tune_discard_button = None; tune_status_var = None;
original_loaded_json_str = None
proposed_tuned_json_data = None

# --- Load Color Pools ---
character_color_pools = {}
try:
    if os.path.exists(COLOR_POOLS_FILE):
        with open(COLOR_POOLS_FILE, 'r', encoding='utf-8') as f: content = f.read().strip()
        if content and content.startswith('{'): character_color_pools = json.loads(content); print(f"Loaded color pools from {COLOR_POOLS_FILE}")
        elif not content: print(f"WARN: Color pools file {COLOR_POOLS_FILE} empty.")
        else: print(f"ERROR: Color pools file {COLOR_POOLS_FILE} invalid JSON.")
    else: print(f"WARN: Color pools file not found: {COLOR_POOLS_FILE}.")
except Exception as e: print(f"Error loading color pools: {e}.")
print(f"DEBUG STARTUP: character_color_pools loaded with {len(character_color_pools)} keys. Sample keys: {list(character_color_pools.keys())[:5]}")

# ==============================================================================
# == UTILITY & HELPER FUNCTION DEFINITIONS ==
# ==============================================================================
# --- Helper to Update Last Update Info ---
def update_last_update_file(update_key, value):
    """Reads last_update.json, updates a specific key, and saves it back."""
    # Define path relative to SCRAPER script directory -> config
    config_dir = os.path.join(SCRIPT_DIR, os.pardir, 'config') # Go up one level from scraper to root, then to config
    filepath = os.path.join(config_dir, 'last_update.json')
    data = {}
    try:
        # Ensure config directory exists
        os.makedirs(config_dir, exist_ok=True)
        # Read existing data if file exists
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                try:
                    data = json.load(f)
                    if not isinstance(data, dict): # Handle invalid content
                        print(f"Warning: Invalid content in {filepath}. Resetting.")
                        data = {}
                except json.JSONDecodeError:
                    print(f"Warning: Corrupt JSON in {filepath}. Resetting.")
                    data = {} # Reset if corrupt

        # Update the specific key
        data[update_key] = value
        print(f"  Updating '{update_key}' in {os.path.basename(filepath)} to '{value}'")

        # Write the updated data back
        with open(filepath, 'w', encoding='utf-8') as f_out:
            json.dump(data, f_out, indent=2) # Use indent for readability

    except Exception as e:
        print(f"ERROR: Failed to update {filepath}: {e}")

# --- Functions: Model Listing, Settings Persistence ---
def get_available_generative_models(api_key_to_check):
    global AVAILABLE_MODELS, DEFAULT_MODEL
    if not GOOGLE_AI_AVAILABLE: AVAILABLE_MODELS = FALLBACK_MODELS; DEFAULT_MODEL = FALLBACK_DEFAULT_MODEL; return FALLBACK_MODELS
    if not api_key_to_check: AVAILABLE_MODELS = FALLBACK_MODELS; DEFAULT_MODEL = FALLBACK_DEFAULT_MODEL; return FALLBACK_MODELS
    try:
        print("Listing available Google AI models...")
        genai.configure(api_key=api_key_to_check); model_list = [m.name.split('/')[-1] for m in genai.list_models() if 'generateContent' in m.supported_generation_methods and 'gemini' in m.name]
        if model_list:
            AVAILABLE_MODELS = sorted(list(set(model_list)), reverse=True)
            if "gemini-1.5-pro-latest" in AVAILABLE_MODELS: DEFAULT_MODEL = "gemini-1.5-pro-latest"
            elif "gemini-1.5-flash-latest" in AVAILABLE_MODELS: DEFAULT_MODEL = "gemini-1.5-flash-latest"
            else: DEFAULT_MODEL = AVAILABLE_MODELS[0] if AVAILABLE_MODELS else FALLBACK_DEFAULT_MODEL
            print(f"Found {len(AVAILABLE_MODELS)} models. Default: {DEFAULT_MODEL}")
        else: AVAILABLE_MODELS = FALLBACK_MODELS; DEFAULT_MODEL = FALLBACK_DEFAULT_MODEL; print("WARN: No Gemini models found.")
        return AVAILABLE_MODELS
    except Exception as e: print(f"ERROR listing models: {e}."); AVAILABLE_MODELS = FALLBACK_MODELS; DEFAULT_MODEL = FALLBACK_DEFAULT_MODEL; return FALLBACK_MODELS

# --- CORRECTED load_settings Function ---
def load_settings():
    global model_selection_var, tune_model_var, model_combobox, tune_model_combobox # Add comboboxes to global access
    selected_gen_model = DEFAULT_MODEL
    selected_tune_model = DEFAULT_MODEL
    try:
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f: settings_data = json.load(f)
            loaded_gen_model = settings_data.get("selected_model")
            loaded_tune_model = settings_data.get("tune_model")
            # Check against AVAILABLE_MODELS which should be populated by get_available_generative_models first
            if loaded_gen_model and loaded_gen_model in AVAILABLE_MODELS: selected_gen_model = loaded_gen_model; print(f"Loaded Gen model: {selected_gen_model}")
            elif loaded_gen_model: print(f"WARN: Saved Gen model '{loaded_gen_model}' unavailable. Using default: {DEFAULT_MODEL}")
            else: print(f"Gen model setting not found, using default: {DEFAULT_MODEL}") # Added default info

            if loaded_tune_model and loaded_tune_model in AVAILABLE_MODELS: selected_tune_model = loaded_tune_model; print(f"Loaded Tune model: {selected_tune_model}")
            elif loaded_tune_model: print(f"WARN: Saved Tune model '{loaded_tune_model}' unavailable. Using default: {DEFAULT_MODEL}")
            else: print(f"Tune model setting not found, using default: {DEFAULT_MODEL}") # Added default info
    except Exception as e: print(f"Error loading settings from {SETTINGS_FILE}: {e}.")

    # --- START: Block to Update GUI ---
    # Ensure AVAILABLE_MODELS is up-to-date before setting values
    if not AVAILABLE_MODELS:
        print("WARN: AVAILABLE_MODELS list is empty during load_settings. Should have been populated earlier.")
        # Optionally attempt refresh, but it indicates an issue in initialization order
        # get_available_generative_models(google_api_key)

    options = AVAILABLE_MODELS if AVAILABLE_MODELS else FALLBACK_MODELS # Use fallback if still empty

    # Update Generation Model Combobox
    if 'model_selection_var' in globals() and isinstance(model_selection_var, tk.StringVar):
        model_selection_var.set(selected_gen_model) # Set the variable first
        if 'model_combobox' in globals() and model_combobox and model_combobox.winfo_exists():
            try:
                model_combobox['values'] = options # Update the list of choices
                # Ensure the selected value is actually in the list before setting the combobox display text
                if selected_gen_model in options:
                    model_combobox.set(selected_gen_model)
                elif options: # If selection invalid, set to first available
                    model_combobox.set(options[0])
                    model_selection_var.set(options[0]) # Sync variable too
                    print(f"WARN: Gen model '{selected_gen_model}' not available, set to '{options[0]}'")
                else: # No options available
                    model_combobox.set("")
            except tk.TclError as e:
                print(f"Error updating model_combobox UI: {e}")
                pass # Ignore if widget destroyed

    # Update Tuning Model Combobox
    if 'tune_model_var' in globals() and isinstance(tune_model_var, tk.StringVar):
        tune_model_var.set(selected_tune_model) # Set the variable first
        if 'tune_model_combobox' in globals() and tune_model_combobox and tune_model_combobox.winfo_exists():
            try:
                tune_model_combobox['values'] = options # Update the list of choices
                # Ensure the selected value is actually in the list before setting the combobox display text
                if selected_tune_model in options:
                    tune_model_combobox.set(selected_tune_model)
                elif options: # If selection invalid, set to first available
                    tune_model_combobox.set(options[0])
                    tune_model_var.set(options[0]) # Sync variable too
                    print(f"WARN: Tune model '{selected_tune_model}' not available, set to '{options[0]}'")
                else: # No options available
                    tune_model_combobox.set("")
            except tk.TclError as e:
                print(f"Error updating tune_model_combobox UI: {e}")
                pass # Ignore if widget destroyed
    # --- END: Block to Update GUI ---

def save_settings(event=None):
    global model_selection_var, tune_model_var
    settings_data = {}
    gen_model_to_save = None
    tune_model_to_save = None

    # Get current selections safely
    try:
        if 'model_selection_var' in globals() and isinstance(model_selection_var, tk.StringVar):
            gen_model_to_save = model_selection_var.get()
        else: print("Warn: Gen model var not ready for save.")
    except tk.TclError: print("Warn: Gen model var TclError during save.")

    try:
        if 'tune_model_var' in globals() and isinstance(tune_model_var, tk.StringVar):
            tune_model_to_save = tune_model_var.get()
        else: print("Warn: Tune model var not ready for save.")
    except tk.TclError: print("Warn: Tune model var TclError during save.")

    # Only save if we got valid values
    if gen_model_to_save:
        settings_data["selected_model"] = gen_model_to_save
        print(f"Saving selected_model: {gen_model_to_save}")
    if tune_model_to_save:
        settings_data["tune_model"] = tune_model_to_save
        print(f"Saving tune_model: {tune_model_to_save}")

    # Write to file if there's data to save
    if settings_data:
        try:
            with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
                json.dump(settings_data, f, indent=4)
            print(f"Settings saved to {SETTINGS_FILE}")
        except Exception as e:
            print(f"Error saving settings to {SETTINGS_FILE}: {e}")
            messagebox.showerror("Settings Save Error", f"Could not save settings.\n{e}")
    else:
        print("No settings data to save.")


# --- Add this new helper function (Improved Version) ---
def ensure_schema_keys(data_node, schema_properties):
    """
    Recursively ensures that keys defined in schema_properties exist in data_node.
    Adds missing keys with default values (None, [], {}).
    Handles one level of nesting for objects defined in schema_properties.

    Args:
        data_node: The dictionary representing the current level of parsed data.
        schema_properties: A dictionary mapping expected keys to their schema details
                           (e.g., {"name": {"type": "string"}, "stats": {"type": "object", "properties": {...}}})
                           This needs to be derived from your full PYTHON_SCHEMA.
    """
    if not isinstance(data_node, dict):
        # If data isn't a dict where one is expected by the schema context calling this, log/return.
        # print(f"WARN: ensure_schema_keys expected dict, got {type(data_node)}. Skipping.")
        return data_node
    if not isinstance(schema_properties, dict):
        # Cannot proceed without schema properties for this level.
        # print(f"WARN: Invalid schema_properties provided to ensure_schema_keys: {type(schema_properties)}. Skipping.")
        return data_node

    # Iterate through keys defined in the schema properties for this level
    for key, prop_schema in schema_properties.items():
        expected_type = prop_schema.get("type")

        if key not in data_node:
            # Key is MISSING - Add it with default value based on expected type
            default_value = None # Default to null
            if expected_type == "array":
                default_value = []
            elif expected_type == "object":
                default_value = {}
            # Add other basic type defaults if needed (e.g., 0 for number, False for boolean)
            # else: default_value = None # Default fallback

            data_node[key] = default_value
            print(f"    Added missing key: '{key}' with default: {default_value}")

            # If we added an empty object, and that object has defined properties in the schema,
            # recursively call ensure_schema_keys to populate its required keys with defaults.
            if expected_type == "object" and "properties" in prop_schema and isinstance(default_value, dict):
                 ensure_schema_keys(default_value, prop_schema["properties"])

        else:
            # Key EXISTS - Check if we need to recurse into nested objects
            current_value = data_node[key]
            if expected_type == "object" and "properties" in prop_schema and isinstance(current_value, dict):
                ensure_schema_keys(current_value, prop_schema["properties"])
            elif expected_type == "array" and "items" in prop_schema and isinstance(current_value, list):
                # Handle arrays: ensure items within the array conform (if item schema is defined)
                item_schema = prop_schema.get("items", {})
                item_props = item_schema.get("properties") # Assuming array of objects for now
                if item_props and item_schema.get("type") == "object":
                     for item in current_value:
                         if isinstance(item, dict):
                             ensure_schema_keys(item, item_props)
            # Else: Key exists and is a primitive or we don't recurse further based on schema

    return data_node # Return the potentially modified data_node

# --- You will need to parse your FINAL_JSON_SCHEMA_STRING into a Python dict ---
# --- Add this near the top after defining FINAL_JSON_SCHEMA_STRING ---
PYTHON_SCHEMA_DICT = None
# WARNING: The schema string provided earlier is NOT valid JSON.
# You MUST convert it into a valid JSON structure first or define it directly
# as a Python dictionary. For now, we'll assume you have a function/way
# to get the 'properties' part of the top-level object.
# Example (IF your schema string was valid JSON):
# try:
#     PYTHON_SCHEMA_DICT = json.loads(FINAL_JSON_SCHEMA_STRING)
# except Exception as e:
#     print(f"FATAL: Could not parse FINAL_JSON_SCHEMA_STRING into dict: {e}")
#     PYTHON_SCHEMA_DICT = {} # Fallback to empty dict

# --- TEMPORARY Placeholder for Top-Level Properties (Replace with actual parsing) ---
# This is a MANUAL extraction based on your schema string. Needs proper parsing/definition.
TOP_LEVEL_SCHEMA_PROPERTIES = {
    "name": {"type": "string"},
    "role": {"type": "string"}, # Allowing null implicitly
    "stats": {"type": "object", "properties": {
        "health": {"type": "any"}, "speed": {"type": "string"}, "difficulty": {"type": "string"},
        "color_theme": {"type": "string"}, "color_theme_secondary": {"type": "string"}
    }},
    "abilities": {"type": "array", "items": {"type": "object", "properties": {
        "name": {"type": "string"}, "keybind": {"type": "string"}, "type": {"type": "string"},
        "description": {"type": "string"}, "casting": {"type": "string"}, "damage": {"type": "string"},
        "damage_falloff": {"type": "string"}, "fire_rate_interval": {"type": "string"},
        "ammo": {"type": "any"}, "critical_hit": {"type": "boolean"}, "cooldown": {"type": "string"},
        "range": {"type": "string"}, "projectile_speed": {"type": "string"}, "charges": {"type": "number"},
        "duration": {"type": "string"}, "movement_boost": {"type": "string"},
        "energy_cost_details": {"type": "string"}, "details": {"type": "string"}
    }}},
    "ultimate": {"type": "object", "properties": { # Assuming nullable object treated as object for keys
        "name": {"type": "string"}, "keybind": {"type": "string"}, "type": {"type": "string"},
        "description": {"type": "string"}, "casting": {"type": "string"}, "damage": {"type": "string"},
        "range": {"type": "string"}, "effect": {"type": "string"}, "duration": {"type": "string"},
        "health_upon_revival": {"type": "string"}, "slow_rate": {"type": "string"},
        "projectile_speed": {"type": "string"}, "movement_boost": {"type": "string"},
        "bonus_health_details": {"type": "string"}, "energy_cost": {"type": "any"}, "details": {"type": "string"}
    }},
     "passives": {"type": "array", "items": {"type": "object", "properties": {
        "name": {"type": "string"}, "keybind": {"type": "string"}, "type": {"type": "string"},
        "description": {"type": "string"}, "cooldown": {"type": "string"}, "damage": {"type": "string"},
        "range": {"type": "string"}, "trigger_condition": {"type": "string"},
        "effect_boost": {"type": "string"}, "speed_details": {"type": "string"}, "details": {"type": "string"}
    }}},
     "teamups": {"type": "array", "items": {"type": "object", "properties": {
        "name": {"type": "string"}, "keybind": {"type": "string"}, "partner": {"type": "any"},
        "effect": {"type": "string"}, "teamup_bonus": {"type": "string"}, "duration": {"type": "string"},
        "cooldown": {"type": "string"}, "range_target": {"type": "string"},
        "special_notes": {"type": "string"}, "details": {"type": "string"}
    }}},
    "gameplay": {"type": "object", "properties": {
        "strategy_overview": {"type": "string"}, "weaknesses": {"type": "array"},
        "achievements": {"type": "array", "items": {"type": "object", "properties": {
             "icon": {"type": "string"}, "name": {"type": "string"}, "description": {"type": "string"},
             "points": {"type": "any"}
        }}}
    }},
    "lore_details": {"type": "object", "properties": {
        "ingame_bio_quote": {"type": "string"}, "ingame_bio_text": {"type": "string"},
        "ingame_story_intro": {"type": "string"},
        "hero_stories": {"type": "array", "items": {"type": "object", "properties": {
            "title": {"type": "string"}, "content": {"type": "string"}, "status": {"type": "string"}
        }}},
        "balance_changes": {"type": "array", "items": {"type": "object", "properties": {
             "date_version": {"type": "string"}, "changes": {"type": "array"}
        }}},
        "official_quote": {"type": "string"}, "official_description": {"type": "string"}
    }},
    "background": {"type": "object", "properties": {
        "real_name": {"type": "string"}, "aliases": {"type": "array"}, "birthplace": {"type": "string"},
        "birthdate": {"type": "string"}, "gender": {"type": "string"}, "eye_color": {"type": "string"},
        "hair_color": {"type": "string"}, "relatives": {"type": "array"}, "affiliation": {"type": "array"},
        "first_appearance_comic": {"type": "string"}, "recommended_comics": {"type": "array"},
        "lore_powers_skills": {"type": "array"}
    }},
    "misc": {"type": "object", "properties": {
        "voice_actor": {"type": "string"}, "quotes_link": {"type": "string"},
        "community_buzz": {"type": "string"},
        "helpful_links": {"type": "array", "items": {"type": "object", "properties": {
            "title": {"type": "string"}, "url": {"type": "string"}
        }}}
    }},
    "meta_stats": {"type": "object", "properties": {
         "tier": {"type": "string"}, "win_rate": {"type": "string"}, "wr_change": {"type": "string"},
         "pick_rate": {"type": "string"}, "pr_change": {"type": "string"}, "ban_rate": {"type": "string"},
         "matches": {"type": "string"}
    }},
    "data_sources": {"type": "object", "properties": {
         "wiki": {"type": "array"}, "tracker": {"type": "array"}, "comic_wiki": {"type": "array"}
    }}
}
# --- End Schema Structure ---


class TextRedirector(io.StringIO):
    def __init__(self, widget):
        super().__init__()
        self.widget = widget
    def write(self, str_):
        log_buffer.write(str_) # Still write to buffer
        if self.widget and self.widget.winfo_exists():
            try:
                # Use after() to schedule the GUI update on the main thread
                self.widget.after(0, self._write_to_widget, str_)
            except tk.TclError:
                 # Handle cases where the widget might be destroyed between checks
                 pass
    def _write_to_widget(self, str_):
        """Internal method called by after() to update the widget."""
        # Check widget existence again inside the scheduled call
        if self.widget and self.widget.winfo_exists():
            try:
                # Ensure widget is in a state where it can be modified
                current_state = self.widget.cget("state")
                self.widget.config(state=tk.NORMAL)
                self.widget.insert(tk.END, str_)
                self.widget.see(tk.END) # Scroll to the end
                self.widget.config(state=current_state) # Restore original state
            except tk.TclError:
                # Handle potential errors during the update itself
                pass
    def flush(self):
        # This might be called, but Tkinter Text widget updates automatically
        pass

# --- Helper Functions ---
# --- Replace the existing sanitize_filename function with this ---
def sanitize_filename(name, extension=".txt"):
    # print(f"DEBUG: sanitize_filename called with name='{name}', extension='{extension}'")

    # --- Initial Input Check ---
    if not name or not isinstance(name, str): # Check if name is None, empty, or not a string
        result = f"invalid_character_name_{random.randint(1000,9999)}{extension}"
        print(f"WARN: sanitize_filename received invalid input '{name}'. Returning placeholder: '{result}'")
        # *** CRITICAL FIX: Added the missing return statement below ***
        return result

    # --- Proceed with Sanitization ---
    original_name = name # Keep original for debugging/logging

    # Replace problematic characters specifically for filenames
    name = name.replace('&', 'and') # Replace ampersand early
    name = name.replace(':', '-')   # Replace colons
    name = name.replace('/', '-')   # Replace forward slashes
    name = name.replace('\\', '-')  # Replace backslashes
    name = name.replace('*', '-')   # Replace asterisks
    name = name.replace('?', '')    # Remove question marks
    name = name.replace('"', '')   # Remove double quotes
    name = name.replace('<', '')    # Remove less than
    name = name.replace('>', '')    # Remove greater than
    name = name.replace('|', '')    # Remove pipe
    # Replace potentially multiple spaces/tabs/newlines with a single underscore
    name = re.sub(r'\s+', '_', name)

    # Remove leading/trailing whitespace, periods, and underscores that can cause issues on some OS
    name = name.strip('._ ')

    # --- Final Check after Cleaning ---
    if not name: # Check if name became empty AFTER cleaning
        result = f"invalid_character_name_{random.randint(1000,9999)}{extension}"
        print(f"WARN: sanitize_filename for '{original_name}' became empty after cleaning. Returning placeholder: '{result}'")
        return result
    else:
        # Construct the final filename
        result = f"{name}{extension}"
        # print(f"DEBUG: sanitize_filename returning: '{result}' (Original: '{original_name}')")
        return result
# --- End of sanitize_filename replacement ---




   # --- START: Nested Dictionary Helper Functions ---
def get_nested_value(data, key_path, default=None):
    """Safely gets a value from a nested dict using dot notation."""
    if not isinstance(data, dict) or not isinstance(key_path, str) or not key_path:
        return default
    keys = key_path.split('.')
    try:
        # Use reduce to traverse the dictionary
        value = functools.reduce(lambda d, key: d.get(key) if isinstance(d, dict) else None, keys, data)
        # Return the found value, or the default if None was encountered during traversal or at the end
        return value if value is not None else default
    except TypeError: # Handles cases where intermediate path is not a dict
        return default
    except Exception: # Catch other potential errors during traversal
        return default

def set_nested_value(data, key_path, value):
    """Safely sets a value in a nested dict using dot notation, creating keys if needed."""
    if not isinstance(data, dict) or not isinstance(key_path, str) or not key_path:
        print(f"WARN (set_nested_value): Invalid input data type ({type(data)}) or key_path ('{key_path}').")
        return False # Indicate failure

    keys = key_path.split('.')
    d = data
    try:
        # Traverse/create dictionary path until the last key
        for i, key in enumerate(keys[:-1]):
            # If key exists but is not a dict, we cannot proceed reliably. Overwrite? Log error?
            # Current behavior: Overwrite if not dict. Be careful if preserving nested structures.
            if key not in d or not isinstance(d.get(key), dict):
                # print(f"DEBUG (set_nested_value): Creating/overwriting nested key '{key}' at level {i}")
                d[key] = {} # Create nested dict if missing or not a dict
            d = d[key]

        # Set the value at the final key
        if keys: # Ensure keys list is not empty
            final_key = keys[-1]
            d[final_key] = value
            # print(f"DEBUG (set_nested_value): Set '{key_path}' to {type(value).__name__}")
            return True # Indicate success
        else:
            print(f"WARN (set_nested_value): key_path ('{key_path}') resulted in empty keys list.")
            return False # Indicate failure (empty key_path)

    except TypeError as e:
        # This might happen if a part of the path exists but isn't a dictionary
        print(f"ERROR (set_nested_value): TypeError setting '{key_path}'. Path conflict? Details: {e}")
        return False
    except Exception as e:
        print(f"ERROR (set_nested_value): Unexpected error setting '{key_path}': {e}")
        return False

    # Check if name became empty AFTER cleaning
    if not name:
        result = f"invalid_character_name_{random.randint(1000,9999)}{extension}"
        print(f"WARN: sanitize_filename became empty after cleaning '{original_name}'. Returning: '{result}'")
        return result
    else:
        result = f"{name}{extension}"
        # print(f"DEBUG: sanitize_filename returning (valid): '{result}'")
        return result


def scrape_article_content(article_url):
    """
    Fetches and parses a single article page, returning its main text content,
    cleaned of common footer/social media text.
    """
    print(f"      Scraping Article: {article_url}")
    headers = {'User-Agent': USER_AGENT}
    content_text = f"Failed to scrape content from: {article_url}\n" # Default error message

    try:
        response = requests.get(article_url, headers=headers, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        # Verified selector based on inspecting actual article pages
        article_body = soup.find('div', class_='art-inner-content')

        if article_body:
            # --- Optional: Remove specific unwanted sections INSIDE the article body ---
            # Example: remove a known comments section block if it exists within art-inner-content
            # comments_section = article_body.find('div', id='comments')
            # if comments_section:
            #    comments_section.decompose()
            # ----------------------------------------------------------------------

            # Extract text, using newline as separator and stripping extra whitespace
            content_text = article_body.get_text(separator='\n', strip=True)

            # --- Basic Cleanup ---
            # Reduce multiple newlines to max two
            content_text = re.sub(r'\n{3,}', '\n\n', content_text).strip()

            # --- START: Regex Filter for Social Media Footer ---
            # Define the pattern to match the common footer block.
            # It looks for the specific intro phrase, followed by whitespace,
            # then "Discord", and then any number of "| SocialMediaName" groups.
            # Uses re.IGNORECASE for flexibility in capitalization.
            # Uses re.DOTALL so '.' can potentially match newlines if needed, though \s handles it mostly.
            footer_pattern = r"For more information about us, check out and follow our other social channels\.\s+Discord(\s*\|\s*\w+)*\s*$"
            # The '$' at the end attempts to anchor the match to the end of the string/multiline block.

            # Remove the matched footer pattern
            cleaned_text = re.sub(footer_pattern, '', content_text, flags=re.IGNORECASE | re.MULTILINE).strip()

            # Check if removal actually changed something to avoid unnecessary assignments
            if len(cleaned_text) < len(content_text):
                print("      Removed common social media footer.")
                content_text = cleaned_text # Assign cleaned text back
            else:
                 # Optional: Try a slightly looser pattern if the first didn't match but you suspect it should have
                 # looser_footer_pattern = r"For more information about us.*?Twitch\s*$" # Example: match until Twitch
                 # cleaned_text_loose = re.sub(looser_footer_pattern, '', content_text, flags=re.IGNORECASE | re.DOTALL).strip()
                 # if len(cleaned_text_loose) < len(content_text):
                 #     print("      Removed common social media footer (using looser pattern).")
                 #     content_text = cleaned_text_loose
                 pass # No footer found or removed
            # --- END: Regex Filter ---

            if not content_text:
                 content_text = "(Article body found but contained no text after cleanup)\n"
                 print(f"      WARN: No text extracted from article body for {article_url}")

        else:
            content_text = "(Could not find main article content element 'div.art-inner-content' on page)\n"
            print(f"      ERROR: Could not find article content element for {article_url}")


    except requests.exceptions.RequestException as e:
        print(f"      ERROR: Network request failed for article {article_url}: {e}")
        content_text += f"Network Error: {e}\n"
    except Exception as e:
        print(f"      ERROR: Parsing failed for article {article_url}: {e}")
        content_text += f"Parsing Error: {e}\n"

    return content_text # Return the (potentially) cleaned text

    
# --- Config File Helpers ---
def load_config_json(filename, config_dir=CONFIG_DIR):
    filepath = os.path.join(config_dir, filename)
    try:
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f: content = f.read().strip();
            if not content: print(f"WARN: Config empty: {filepath}."); return {};
            if not content.startswith('{'): print(f"ERROR: Config not JSON: {filepath}."); return {};
            return json.loads(content)
        else: print(f"WARN: Config not found: {filepath}."); return {}
    except json.JSONDecodeError as e: print(f"ERROR: Invalid JSON in config: {filepath} - {e}."); return {}
    except Exception as e: print(f"ERROR: Failed load config {filepath}: {e}."); return {}

def save_config_json(data, filename, config_dir=CONFIG_DIR):
    if not isinstance(data, dict): print(f"ERROR: Data for {filename} must be dict."); return False
    filepath = os.path.join(config_dir, filename)
    try:
        os.makedirs(config_dir, exist_ok=True);
        with open(filepath, 'w', encoding='utf-8') as f: json.dump(data, f, indent=4, ensure_ascii=False)
        print(f"Saved config file: {filepath}"); return True
    except Exception as e: print(f"ERROR: Failed save config {filepath}: {e}"); messagebox.showerror("Config Save Error", f"Could not save:\n{filename}\n{e}"); return False

# --- Character List Loading (FIXED for errors and duplicates) ---
def load_character_list_from_files():
    """
    Scans the output directory for .json files, filters out error files,
    handles duplicates (preferring '&'), moves error files, and builds the list.
    """
    global ACTIVE_CHARACTER_LIST
    print(f"Scanning for character JSON files in: {CHARACTER_JSON_OUTPUT_DIR}")

    # Ensure directories exist
    failed_dir = os.path.join(CHARACTER_JSON_OUTPUT_DIR, "failed")
    try:
        if not os.path.isdir(CHARACTER_JSON_OUTPUT_DIR):
            print(f"INFO: Creating character directory: {CHARACTER_JSON_OUTPUT_DIR}")
            os.makedirs(CHARACTER_JSON_OUTPUT_DIR, exist_ok=True)
        if not os.path.isdir(failed_dir):
            print(f"INFO: Creating failed logs directory: {failed_dir}")
            os.makedirs(failed_dir, exist_ok=True)
    except OSError as e:
        print(f"ERROR: Could not create directories: {e}")
        ACTIVE_CHARACTER_LIST = []
        return

    temp_list = []
    found_chars = set() # Use a set to easily check for duplicates (case-insensitive)
    moved_error_files = 0

    try:
        for filename in os.listdir(CHARACTER_JSON_OUTPUT_DIR):
            filepath = os.path.join(CHARACTER_JSON_OUTPUT_DIR, filename)

            # --- Move Error Files ---
            # Check if it's a file first to avoid errors on directories
            if os.path.isfile(filepath) and filename.lower().endswith(".json.api_error.txt"):
                try:
                    # Generate a timestamp for uniqueness if needed, though move usually overwrites
                    # timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                    # destination_filename = f"{os.path.splitext(filename)[0]}_{timestamp}.api_error.txt"
                    destination = os.path.join(failed_dir, filename) # Keep original name for now
                    print(f"  Moving error file: {filename} -> failed\\")
                    # Use shutil.move for better cross-platform compatibility and overwrite handling
                    shutil.move(filepath, destination)
                    moved_error_files += 1
                except Exception as move_e:
                    print(f"  WARN: Could not move error file {filename}: {move_e}")
                continue # Skip further processing for error files

            # --- Process Regular JSON Files ---
            if filename.lower().endswith(".json") and os.path.isfile(filepath):
                char_name = os.path.splitext(filename)[0]
                char_lower = char_name.lower()

                # --- Duplicate Handling ('&' vs 'and') ---
                # Define variations to check
                name_with_and = char_name.replace('&', 'and')
                # Be specific about replacing ' and ' to avoid partial word matches if names change
                name_with_amp = char_name.replace(' and ', ' & ')

                # Check if a variation (or the name itself) is already processed
                already_found = False
                if char_lower in found_chars: already_found = True
                if name_with_and.lower() in found_chars: already_found = True
                if name_with_amp.lower() in found_chars: already_found = True

                if already_found:
                    # Preference: Keep the '&' version if encountered
                    # If current name uses '&' and the 'and' version was already added, replace it
                    # Need to check if name_with_and is actually in the temp_list being built
                    # Note: Case variations might exist, compare lower case for presence check
                    if '&' in char_name and name_with_and.lower() in [n.lower() for n in temp_list]:
                        # Find the exact 'and' version string (case sensitive) to remove
                        try:
                            # Find the original case version to remove
                            and_version_to_remove = next(n for n in temp_list if n.lower() == name_with_and.lower())
                            print(f"  Duplicate Handling: Replacing '{and_version_to_remove}' with preferred '{char_name}'")
                            temp_list.remove(and_version_to_remove)
                            temp_list.append(char_name)
                            # Update found_chars set
                            found_chars.discard(name_with_and.lower()) # Remove the 'and' version
                            found_chars.add(char_lower) # Add the '&' version
                        except StopIteration:
                             print(f"  WARN: Tried to replace '{name_with_and}' but couldn't find exact match in temp list.")
                             # Decide whether to add the '&' version anyway or skip
                             if char_lower not in found_chars:
                                  temp_list.append(char_name)
                                  found_chars.add(char_lower)


                    # Otherwise (if '&' version already found, or if current is 'and' version), just skip
                    else:
                         print(f"  Skipping duplicate/variation: {char_name}")
                         continue
                else:
                    # New character, add it
                    temp_list.append(char_name)
                    found_chars.add(char_lower)

    except OSError as e:
        print(f"ERROR: Failed to read character directory {CHARACTER_JSON_OUTPUT_DIR}: {e}")
        ACTIVE_CHARACTER_LIST = []
        return

    ACTIVE_CHARACTER_LIST = sorted(temp_list)
    print(f"Found {len(ACTIVE_CHARACTER_LIST)} valid characters.")
    if moved_error_files > 0:
        print(f"Moved {moved_error_files} error file(s) to 'failed' subfolder.")


# --- URL Persistence ---
def load_urls():
    global character_urls
    try:
        if os.path.exists(URL_DATA_FILE):
            with open(URL_DATA_FILE, 'r', encoding='utf-8') as f:
                loaded_data = json.load(f)
                # Basic validation: ensure it's a dict
                if isinstance(loaded_data, dict):
                    character_urls = loaded_data
                    print(f"Loaded URLs for {len(character_urls)} characters from {URL_DATA_FILE}")
                else:
                     print(f"ERROR: Invalid format in {URL_DATA_FILE}. Expected a dictionary.")
                     character_urls = {}
        else:
            character_urls = {}
            print(f"{URL_DATA_FILE} not found. Starting with empty URL list.")
    except json.JSONDecodeError as e:
        print(f"Error loading {URL_DATA_FILE}: Invalid JSON - {e}")
        character_urls = {}
    except Exception as e:
        print(f"Error loading {URL_DATA_FILE}: {e}.")
        character_urls = {}

def save_urls():
    global character_urls
    try:
        with open(URL_DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(character_urls, f, indent=4, ensure_ascii=False)
            print(f"Saved URLs to {URL_DATA_FILE}")
    except Exception as e:
        print(f"Error saving URLs: {e}")
        messagebox.showerror("Save Error", f"Could not save URLs.\n{e}")

# --- Replace the existing function with this ---
# --- DEBUGGING VERSION of generate_json_from_raw_via_api ---
def generate_json_from_raw_via_api(raw_text, character_name, selected_model_name):
    global google_api_key, FINAL_JSON_SCHEMA_STRING
    print(f"  DEBUG: generate_json_from_raw_via_api called for '{character_name}' with model '{selected_model_name}'") # DEBUG
    if not GOOGLE_AI_AVAILABLE: print("  DEBUG: Google AI Lib missing."); return {"error": "Google AI library missing."}
    if not google_api_key: print("  DEBUG: API Key missing."); return {"error": "API Key missing."}
    if not selected_model_name: print("  DEBUG: Model name missing."); return {"error": "No API model selected."}

    prompt_template_content = None
    prompt_source = "Unknown"

    # --- Load Prompt Template ---
    try:
        # (Load logic unchanged)
        if os.path.exists(API_PROMPT_TEMPLATE_FILE):
            with open(API_PROMPT_TEMPLATE_FILE, 'r', encoding='utf-8') as f: loaded_template = f.read()
            if loaded_template and loaded_template.strip(): prompt_template_content = loaded_template; prompt_source = f"custom ({os.path.basename(API_PROMPT_TEMPLATE_FILE)})"; print(f"  Loaded custom prompt: {prompt_source}")
        if prompt_template_content is None and os.path.exists(DEFAULT_PROMPT_FILE):
             with open(DEFAULT_PROMPT_FILE, 'r', encoding='utf-8') as f: loaded_default = f.read()
             if loaded_default and loaded_default.strip(): prompt_template_content = loaded_default; prompt_source = f"default ({os.path.basename(DEFAULT_PROMPT_FILE)})"; print(f"  Loaded default prompt: {prompt_source}")
        if prompt_template_content is None: raise FileNotFoundError("Could not load API prompt template from custom or default file.")
        print(f"  DEBUG: Prompt template loaded from {prompt_source}") # DEBUG
    except Exception as e: error_msg = f"ERROR loading prompt template: {e}"; print(error_msg); return {"error": error_msg}

    # --- Format Prompt ---
    try:
        required_placeholders = ["{json_schema_target}", "{character_name}", "{raw_text}"]
        for ph in required_placeholders:
            if ph not in prompt_template_content: raise ValueError(f"Placeholder {ph} missing in {prompt_source}.")
        prompt = prompt_template_content.format(character_name=character_name, raw_text=raw_text, json_schema_target=FINAL_JSON_SCHEMA_STRING)
        print(f"  DEBUG: Prompt formatted successfully. Length: {len(prompt)}") # DEBUG
    except Exception as e: error_msg = f"ERROR formatting prompt ({prompt_source}): {e}"; print(error_msg); return {"error": error_msg}

    # --- API Call ---
    response = None # Initialize response
    try:
        print("  DEBUG: Configuring GenAI...") # DEBUG
        genai.configure(api_key=google_api_key)
        generation_config = {
            "temperature": 0.1, "top_p": 1, "top_k": 1, "max_output_tokens": 8192,
        }
        safety_settings = [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        ]
        print(f"  DEBUG: Creating GenerativeModel for '{selected_model_name}'...") # DEBUG
        model = genai.GenerativeModel(model_name=selected_model_name, generation_config=generation_config, safety_settings=safety_settings)
        print(f"  DEBUG: Sending request to AI [{selected_model_name}] (expecting text)...") # DEBUG
        response = model.generate_content(prompt, request_options={"timeout": 180})
        print("  DEBUG: AI call completed.") # DEBUG

        # --- Process Text Response ---
        extracted_json_string = None
        parsed_data = None
        error_detail = None
        raw_ai_output = "" # Initialize

        try:
            # <<< DEBUG: Check response object itself >>>
            if response:
                 print(f"  DEBUG: Response object received. Type: {type(response)}")
                 # print(f"  DEBUG: Response content (first 100 chars): {str(response)[:100]}") # Might be too verbose
            else:
                 print("  DEBUG: Response object is None after API call!")
                 # This would likely lead to the TypeError later if not handled

            # Check for blocked prompts or empty responses
            if not response or not response.parts: # Added check for None response
                block_reason="?"; finish_reason="?";
                if response and response.prompt_feedback: block_reason = response.prompt_feedback.block_reason or "?";
                if response and response.candidates and response.candidates[0]: finish_reason = response.candidates[0].finish_reason.name if response.candidates[0].finish_reason else "?";
                error_detail = f"API Error (Blocked/No Parts/Null Response). BlockReason:{block_reason}, FinishReason:{finish_reason}" # Added Null Response possibility
                print(f"  DEBUG: API response blocked or empty. Details: {error_detail}") # DEBUG
                return {"error": "API response was blocked or empty.", "details": error_detail}

            # Get raw text output
            raw_ai_output = response.text
            print(f"  DEBUG: Received raw text response (length {len(raw_ai_output)}). Snippet: '{raw_ai_output[:100]}...'") # DEBUG + Snippet

            # --- Robust Extraction ---
            print("  DEBUG: Attempting to extract JSON block from text...") # DEBUG
            match = re.search(r'```json\s*(\{.*?\})\s*```', raw_ai_output, re.DOTALL)
            if match:
                extracted_json_string = match.group(1)
                print("    DEBUG: Extracted JSON using markdown pattern.") # DEBUG
            else:
                match = re.search(r'^\s*(\{.*?\})\s*$', raw_ai_output, re.DOTALL | re.MULTILINE)
                if match:
                    extracted_json_string = match.group(1)
                    print("    DEBUG: Extracted JSON using outer braces pattern.") # DEBUG
                else:
                    start_brace = raw_ai_output.find('{')
                    end_brace = raw_ai_output.rfind('}')
                    if start_brace != -1 and end_brace != -1 and end_brace > start_brace:
                        extracted_json_string = raw_ai_output[start_brace : end_brace + 1]
                        print("    DEBUG: Extracted JSON using first/last brace pattern (fallback).") # DEBUG
                    else:
                        error_detail = "Could not find any JSON block delimiters ({...} or ```json) in AI response."
                        print(f"  DEBUG: Extraction Failed: {error_detail}") # DEBUG
                        return {"error": "JSON block extraction failed.", "details": error_detail, "raw_response": raw_ai_output}

            # --- Attempt Parsing ---
            if extracted_json_string:
                print(f"  DEBUG: Attempting to parse extracted JSON string (length {len(extracted_json_string)})...") # DEBUG
                try:
                    parsed_data = json.loads(extracted_json_string)
                    print("  DEBUG: SUCCESS: Parsed extracted JSON string.") # DEBUG
                    # Return the successfully parsed Python dictionary
                    return parsed_data # <<< SUCCESS RETURN >>>
                except json.JSONDecodeError as e:
                    error_detail = f"Invalid JSON syntax in extracted block. Error: {e}"
                    print(f"  DEBUG: Parsing Failed: {error_detail}") # DEBUG
                    return {"error": "Invalid JSON syntax.", "details": str(e), "raw_response": extracted_json_string}
            else:
                 print("  DEBUG: Extraction succeeded but result was empty?") # DEBUG
                 return {"error": "Extraction succeeded but result was empty?", "raw_response": raw_ai_output}

        except Exception as e: # Catch other potential errors during response processing
            error_detail = f"Unexpected response processing error: {e}"
            print(f"  DEBUG: Unexpected response processing error: {error_detail}") # DEBUG
            import traceback; traceback.print_exc(file=sys.stderr)
            return {"error": "Unexpected response processing error.", "details": str(e), "raw_response": raw_ai_output if raw_ai_output else "Raw output unavailable"}

    # Handle specific Google API errors
    except google_exceptions.InvalidArgument as e: print(f"  DEBUG: Google API Error (Invalid Argument): {e}"); return {"error": "Google API Error: Invalid Argument", "details": str(e)}
    except google_exceptions.PermissionDenied as e: print(f"  DEBUG: Google API Error (Permission Denied): {e}"); return {"error": "Google API Error: Permission Denied", "details": str(e)}
    except google_exceptions.ResourceExhausted as e: print(f"  DEBUG: Google API Error (Resource Exhausted): {e}"); return {"error": "Google API Error: Resource Exhausted (Quota?)", "details": str(e)}
    except google_exceptions.FailedPrecondition as e: print(f"  DEBUG: Google API Error (Failed Precondition): {e}"); return {"error": "Google API Error: Failed Precondition", "details": str(e)}
    except google_exceptions.InternalServerError as e: print(f"  DEBUG: Google API Error (Internal Server Error): {e}"); return {"error": "Google API Error: Internal Server Error", "details": str(e)}
    except google_exceptions.GoogleAPIError as e: print(f"  DEBUG: Google API Error: {e}"); return {"error": "Google API Error", "details": str(e)}
    # Handle network/request errors
    except requests.exceptions.RequestException as e: print(f"  DEBUG: Network Error calling API: {e}"); return {"error": "Network Error during API call", "details": str(e)}
    # Catch any other unexpected errors during setup/call
    except Exception as e:
        print(f"  DEBUG: Unexpected API call setup error: {e}") # DEBUG
        import traceback; traceback.print_exc(file=sys.stderr)
        # <<< IMPORTANT: Ensure this path returns a dictionary for the calling function >>>
        return {"error": "Unexpected API call error", "details": str(e)}

# --- End DEBUGGING VERSION ---
# ==============================================================================
# == PATCH PROCESSING HELPER FUNCTIONS == # <<< NEW SECTION MARKER >>>
# ==============================================================================

# --- Add this function ---
def extract_patch_section(character_name, full_patch_text):
    """
    Extracts the relevant section for a character from the full balance patch text.
    Assumes character sections start with the character name as a heading (case-insensitive).
    """
    if not character_name or not full_patch_text:
        return None

    # Escape potential regex special characters in the name (like '.')
    safe_char_name = re.escape(character_name)

    # Regex to find the character section:
    # - Starts with optional markdown heading (##, ###) or just the name at line start
    # - Matches the character name (case-insensitive)
    # - Captures everything until the *next* heading (## or ###) or end of file/text
    # - Uses non-greedy matching (.*?) and DOTALL flag
    # - Includes lookahead `(?=...)` to stop *before* the next heading marker
    pattern = re.compile(
        r"^(?:#{2,3}\s*)?" + safe_char_name + r"\s*?\n(.*?)(?=\n^#{2,3}\s*\w|\Z)",
        re.IGNORECASE | re.MULTILINE | re.DOTALL
    )

    match = pattern.search(full_patch_text)

    if match:
        section = match.group(1).strip()
        print(f"    Found patch section for '{character_name}'. Length: {len(section)}")
        return section
    else:
        print(f"    No specific patch section found for '{character_name}' in the provided text.")
        return None

# --- CORRECTED interpret_patch_via_api using manual replacement ---
def interpret_patch_via_api(base_json_str, patch_section_text, character_name, model_name):
    """
    Calls the Gemini API using the patch interpretation prompt to get changes.
    Uses manual string replacement for prompt formatting.
    """
    global google_api_key

    # --- Basic Validations (Unchanged) ---
    if not GOOGLE_AI_AVAILABLE: return {"error": "Google AI library missing."}
    if not google_api_key: return {"error": "API Key missing."}
    if not model_name: return {"error": "No API model selected for patch interpretation."}
    if not patch_section_text: return {} # No text, no changes possible

    # --- Load Patch Prompt Template ---
    patch_prompt_template = None
    patch_prompt_filepath = os.path.join(SCRIPT_DIR, 'api_prompt_v3_patch_apply.txt')
    prompt_source = "Unknown"
    try:
        if os.path.exists(patch_prompt_filepath):
            with open(patch_prompt_filepath, 'r', encoding='utf-8') as f: patch_prompt_template = f.read()
            prompt_source = f"patch apply ({os.path.basename(patch_prompt_filepath)})"
        if not patch_prompt_template or not patch_prompt_template.strip():
             raise FileNotFoundError(f"Could not load patch interpretation prompt template: {patch_prompt_filepath}")
    except Exception as e:
        error_msg = f"ERROR loading patch prompt template: {e}"; print(error_msg); return {"error": error_msg}
    print(f"  Using patch prompt: {prompt_source}")

    # --- Format Patch Prompt (MANUAL REPLACEMENT) ---
    try:
        print("  DEBUG: Formatting patch prompt using manual replacement...") # DEBUG
        # Start with the raw template content
        prompt = patch_prompt_template

        # Replace placeholders one by one
        prompt = prompt.replace("{character_name}", str(character_name)) # Ensure string
        prompt = prompt.replace("{base_json_str}", str(base_json_str)) # Ensure string
        prompt = prompt.replace("{patch_section_text}", str(patch_section_text)) # Ensure string

        # Check if any placeholder remains (optional sanity check)
        if "{character_name}" in prompt or "{base_json_str}" in prompt or "{patch_section_text}" in prompt:
             print("  WARN: Not all placeholders seem to be replaced in patch prompt.")

        print(f"  DEBUG: Patch prompt formatted successfully (manual). Length: {len(prompt)}") # DEBUG

    except Exception as e: # Catch potential errors during replacement
        error_msg = f"ERROR formatting patch prompt (manual replacement): {e}"; print(error_msg);
        return {"error": f"Manual prompt format error: {e}"}

    # --- API Call & Response Processing (Identical to previous DEBUG version) ---
    # (Keep the rest of the function exactly as it was in the previous step,
    #  starting from the 'API Call' try block down to the end.
    #  This part includes the call to genai, response checking,
    #  JSON extraction, parsing, and error handling.)
    # --- API Call ---
    response = None
    try:
        print("  DEBUG: Configuring GenAI...")
        genai.configure(api_key=google_api_key)
        generation_config = {"temperature": 0.1, "top_p": 1, "top_k": 1, "max_output_tokens": 4096}
        safety_settings = [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            # ... other safety settings ...
             {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        ]
        print(f"  DEBUG: Creating GenerativeModel for '{model_name}'...")
        model = genai.GenerativeModel(model_name=model_name, generation_config=generation_config, safety_settings=safety_settings)
        print(f"  DEBUG: Sending request to AI [{model_name}] for patch interpretation (expecting text)...")
        response = model.generate_content(prompt, request_options={"timeout": 120})
        print("  DEBUG: AI call completed.")

        # --- Process Text Response ---
        extracted_json_string = None
        parsed_data = None
        error_detail = None
        raw_ai_output = ""

        try:
            if response: print(f"  DEBUG: Response object received. Type: {type(response)}")
            else: print("  DEBUG: Response object is None after API call!")

            if not response or not response.parts:
                block_reason="?"; finish_reason="?";
                if response and response.prompt_feedback: block_reason = response.prompt_feedback.block_reason or "?";
                if response and response.candidates and response.candidates[0]: finish_reason = response.candidates[0].finish_reason.name if response.candidates[0].finish_reason else "?";
                error_detail = f"Patch AI Error (Blocked/No Parts/Null Response). BlockReason:{block_reason}, FinishReason:{finish_reason}"
                print(f"  DEBUG: API response blocked or empty. Details: {error_detail}")
                return {"error": "Patch AI response was blocked or empty.", "details": error_detail}

            raw_ai_output = response.text
            print(f"  DEBUG: Received raw text response from patch AI (length {len(raw_ai_output)}). Snippet: '{raw_ai_output[:100]}...'")

            print("  DEBUG: Attempting to extract JSON block from text...")
            match = re.search(r'```json\s*(\{.*?\})\s*```', raw_ai_output, re.DOTALL)
            if match: extracted_json_string = match.group(1); print("    DEBUG: Extracted JSON using markdown pattern.")
            else:
                match = re.search(r'^\s*(\{.*?\})\s*$', raw_ai_output, re.DOTALL | re.MULTILINE)
                if match: extracted_json_string = match.group(1); print("    DEBUG: Extracted JSON using outer braces pattern.")
                else:
                    start_brace = raw_ai_output.find('{'); end_brace = raw_ai_output.rfind('}')
                    if start_brace != -1 and end_brace != -1 and end_brace > start_brace: extracted_json_string = raw_ai_output[start_brace : end_brace + 1]; print("    DEBUG: Extracted JSON using first/last brace pattern (fallback).")
                    else:
                         error_detail = "Could not find any JSON block delimiters in patch AI response."
                         print(f"  DEBUG: Extraction Failed: {error_detail}")
                         return {"error": "Patch JSON block extraction failed.", "details": error_detail, "raw_response": raw_ai_output}

            if extracted_json_string:
                print(f"  DEBUG: Attempting to parse extracted patch JSON string (length {len(extracted_json_string)})...")
                try:
                    parsed_data = json.loads(extracted_json_string)
                    if not parsed_data: print("  DEBUG: Patch AI returned empty JSON object '{}'."); return {}
                    else: print("  DEBUG: SUCCESS: Parsed patch JSON updates."); return parsed_data
                except json.JSONDecodeError as e:
                    error_detail = f"Invalid JSON syntax in extracted patch block. Error: {e}"
                    print(f"  DEBUG: Parsing Failed: {error_detail}")
                    return {"error": "Invalid Patch JSON syntax.", "details": str(e), "raw_response": extracted_json_string}
            else:
                 print("  DEBUG: Extraction succeeded but result was empty?")
                 return {"error": "Patch JSON extraction succeeded but result was empty?", "raw_response": raw_ai_output}

        except Exception as e:
            error_detail = f"Unexpected patch response processing error: {e}"
            print(f"  DEBUG: Unexpected patch response processing error: {error_detail}")
            import traceback; traceback.print_exc(file=sys.stderr)
            return {"error": "Unexpected patch response processing error.", "details": str(e), "raw_response": raw_ai_output if raw_ai_output else "Raw output unavailable"}

    except google_exceptions.GoogleAPIError as e: print(f"  DEBUG: Patch Google API Error: {e}"); return {"error": "Google API Error (Patch)", "details": str(e)}
    except requests.exceptions.RequestException as e: print(f"  DEBUG: Patch Network Error calling API: {e}"); return {"error": "Network Error during Patch API call", "details": str(e)}
    except Exception as e:
        print(f"  DEBUG: Unexpected Patch API call setup error: {e}")
        import traceback; traceback.print_exc(file=sys.stderr)
        return {"error": "Unexpected Patch API call error", "details": str(e)}
# --- End CORRECTED interpret_patch_via_api ---

# --- Add this function ---
def merge_updates(base_dict, updates_dict):
    """
    Recursively merges updates from updates_dict into base_dict.
    Handles nested dictionaries and updates items in 'abilities' list by name.
    Overwrites values in base_dict with values from updates_dict.
    """
    if not isinstance(base_dict, dict) or not isinstance(updates_dict, dict):
        print(f"WARN (merge_updates): Invalid input types (base: {type(base_dict)}, updates: {type(updates_dict)}). Skipping merge.")
        return base_dict # Return base unchanged

    if not updates_dict: # If updates dict is empty {}, nothing to merge
        print("    Merge: No updates to apply.")
        return base_dict

    print(f"    Merge: Applying updates: {list(updates_dict.keys())}")

    for key, value in updates_dict.items():
        # --- Special Handling for 'abilities' list ---
        if key == "abilities" and isinstance(value, list) and key in base_dict and isinstance(base_dict[key], list):
            print(f"      Merging '{key}' list...")
            base_abilities = base_dict[key]
            updates_abilities = value

            for update_ability in updates_abilities:
                if not isinstance(update_ability, dict): continue # Skip invalid entries in update list
                update_name = update_ability.get("name")
                if not update_name:
                    print(f"      WARN (merge_updates): Skipping ability update, missing 'name': {update_ability}")
                    continue

                # Find the corresponding ability in the base list
                found_base_ability = None
                for base_ability in base_abilities:
                    if isinstance(base_ability, dict) and base_ability.get("name") == update_name:
                        found_base_ability = base_ability
                        break

                if found_base_ability:
                    print(f"        Updating ability '{update_name}'...")
                    # Recursively merge the update_ability changes into the found_base_ability
                    merge_updates(found_base_ability, update_ability) # Reuse merge logic
                else:
                    # Option 1: Add the ability if not found? (Safer to only update existing for now)
                    # Option 2: Log a warning
                    print(f"      WARN (merge_updates): Ability '{update_name}' from patch updates not found in base JSON abilities list. Skipping update for this ability.")
            # --- End of 'abilities' special handling ---

        # --- Recursive merge for nested dictionaries ---
        elif key in base_dict and isinstance(base_dict[key], dict) and isinstance(value, dict):
            print(f"      Recursively merging dict '{key}'...")
            merge_updates(base_dict[key], value)

        # --- Default: Overwrite or add key/value ---
        # This handles simple values, replacing lists (other than abilities), etc.
        else:
            if key in base_dict:
                 print(f"      Updating key '{key}' (Type: {type(value).__name__}).")
            else:
                 print(f"      Adding new key '{key}' (Type: {type(value).__name__}).")
            base_dict[key] = value # Overwrite or add

    return base_dict # Return the modified base_dict











    # --- Load Prompt Template (unchanged logic) ---
    try:
        if os.path.exists(API_PROMPT_TEMPLATE_FILE):
            with open(API_PROMPT_TEMPLATE_FILE, 'r', encoding='utf-8') as f: loaded_template = f.read()
            if loaded_template and loaded_template.strip(): prompt_template_content = loaded_template; prompt_source = f"custom ({os.path.basename(API_PROMPT_TEMPLATE_FILE)})"; print(f"  Loaded custom prompt: {prompt_source}")
        if prompt_template_content is None and os.path.exists(DEFAULT_PROMPT_FILE):
             with open(DEFAULT_PROMPT_FILE, 'r', encoding='utf-8') as f: loaded_default = f.read()
             if loaded_default and loaded_default.strip(): prompt_template_content = loaded_default; prompt_source = f"default ({os.path.basename(DEFAULT_PROMPT_FILE)})"; print(f"  Loaded default prompt: {prompt_source}")
        if prompt_template_content is None: raise FileNotFoundError("Could not load API prompt template from custom or default file.")
    except Exception as e: error_msg = f"ERROR loading prompt template: {e}"; print(error_msg); return {"error": error_msg}
    print(f"  Using prompt: {prompt_source}")

    # --- Format Prompt (unchanged logic) ---
    try:
        required_placeholders = ["{json_schema_target}", "{character_name}", "{raw_text}"]
        for ph in required_placeholders:
            if ph not in prompt_template_content: raise ValueError(f"Placeholder {ph} missing in {prompt_source}.")
        prompt = prompt_template_content.format(character_name=character_name, raw_text=raw_text, json_schema_target=FINAL_JSON_SCHEMA_STRING)
    except Exception as e: error_msg = f"ERROR formatting prompt ({prompt_source}): {e}"; print(error_msg); return {"error": error_msg}

    # --- API Call ---
    try:
        genai.configure(api_key=google_api_key)
        # Configure generation settings (request TEXT output)
        generation_config = {
            "temperature": 0.1, "top_p": 1, "top_k": 1, "max_output_tokens": 8192,
            # "response_mime_type": "application/json" # REMOVED - Request plain text
        }
        safety_settings = [ # Keep safety settings
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        ]
        model = genai.GenerativeModel(model_name=selected_model_name, generation_config=generation_config, safety_settings=safety_settings)
        print(f"  Sending request to AI [{selected_model_name}] (expecting text)...")
        response = model.generate_content(prompt, request_options={"timeout": 180})

        # --- Process Text Response ---
        extracted_json_string = None
        parsed_data = None
        error_detail = None

        try:
            # Check for blocked prompts or empty responses
            if not response.parts:
                block_reason = response.prompt_feedback.block_reason or "?" if response.prompt_feedback else "?"
                finish_reason = response.candidates[0].finish_reason.name if response.candidates and response.candidates[0].finish_reason else "?"
                error_detail = f"API Error (Blocked/No Parts). BlockReason:{block_reason}, FinishReason:{finish_reason}"
                print(f"  {error_detail}")
                # Return error without raw response as there are no parts
                return {"error": "API response was blocked or empty.", "details": error_detail}

            # Get raw text output
            raw_ai_output = response.text
            print(f"  Received raw text response (length {len(raw_ai_output)}).")

            # --- Robust Extraction ---
            print("  Attempting to extract JSON block from text...")
            # 1. Try markdown block first
            match = re.search(r'```json\s*(\{.*?\})\s*```', raw_ai_output, re.DOTALL)
            if match:
                extracted_json_string = match.group(1)
                print("    Extracted JSON using markdown pattern.")
            else:
                # 2. Try outermost curly braces
                match = re.search(r'^\s*(\{.*?\})\s*$', raw_ai_output, re.DOTALL | re.MULTILINE) # Anchor to start/end
                if match:
                    extracted_json_string = match.group(1)
                    print("    Extracted JSON using outer braces pattern.")
                else:
                    # 3. Fallback: find first '{' and last '}' - more risky
                    start_brace = raw_ai_output.find('{')
                    end_brace = raw_ai_output.rfind('}')
                    if start_brace != -1 and end_brace != -1 and end_brace > start_brace:
                        extracted_json_string = raw_ai_output[start_brace : end_brace + 1]
                        print("    Extracted JSON using first/last brace pattern (fallback).")
                    else:
                        error_detail = "Could not find any JSON block delimiters ({...} or ```json) in AI response."
                        print(f"  FAIL: {error_detail}")
                        # Save raw output for debugging if extraction fails
                        # (Moved error file saving to the calling function for consistency)
                        return {"error": "JSON block extraction failed.", "details": error_detail, "raw_response": raw_ai_output}

            # --- Attempt Parsing ---
            if extracted_json_string:
                print(f"  Attempting to parse extracted JSON string (length {len(extracted_json_string)})...")
                try:
                    parsed_data = json.loads(extracted_json_string)
                    print("  SUCCESS: Parsed extracted JSON string.")
                    # Return the successfully parsed Python dictionary
                    return parsed_data
                except json.JSONDecodeError as e:
                    error_detail = f"Invalid JSON syntax in extracted block. Error: {e}"
                    print(f"  FAIL: {error_detail}")
                    # Return error WITH the faulty extracted string for debugging
                    return {"error": "Invalid JSON syntax.", "details": str(e), "raw_response": extracted_json_string}
            else:
                 # This case should be caught by extraction checks above, but as safety
                 return {"error": "Extraction succeeded but result was empty?", "raw_response": raw_ai_output}

        except Exception as e: # Catch other potential errors during response processing
            error_detail = f"Unexpected response processing error: {e}"
            print(f"  API Error processing response: {error_detail}")
            import traceback
            traceback.print_exc(file=sys.stderr)
            return {"error": "Unexpected response processing error.", "details": str(e), "raw_response": raw_ai_output if 'raw_ai_output' in locals() else "Raw output unavailable"}

    # Handle specific Google API errors (unchanged)
    except google_exceptions.InvalidArgument as e: print(f"  Google API Error (Invalid Argument): {e}"); return {"error": "Google API Error: Invalid Argument", "details": str(e)}
    except google_exceptions.PermissionDenied as e: print(f"  Google API Error (Permission Denied): {e}"); return {"error": "Google API Error: Permission Denied", "details": str(e)}
    except google_exceptions.ResourceExhausted as e: print(f"  Google API Error (Resource Exhausted): {e}"); return {"error": "Google API Error: Resource Exhausted (Quota?)", "details": str(e)}
    except google_exceptions.FailedPrecondition as e: print(f"  Google API Error (Failed Precondition): {e}"); return {"error": "Google API Error: Failed Precondition", "details": str(e)}
    except google_exceptions.InternalServerError as e: print(f"  Google API Error (Internal Server Error): {e}"); return {"error": "Google API Error: Internal Server Error", "details": str(e)}
    except google_exceptions.GoogleAPIError as e: print(f"  Google API Error: {e}"); return {"error": "Google API Error", "details": str(e)}
    # Handle network/request errors (unchanged)
    except requests.exceptions.RequestException as e: print(f"  Network Error calling API: {e}"); return {"error": "Network Error during API call", "details": str(e)}
    # Catch any other unexpected errors (unchanged)
    except Exception as e:
        print(f"  Unexpected API call setup error: {e}")
        import traceback
        traceback.print_exc(file=sys.stderr)
        return {"error": "Unexpected API call error", "details": str(e)}

def scrape_and_update_info_file(category_name, category_url, output_filepath):
    """
    Fetches a news category index page, gets links to recent articles,
    scrapes content from each article, combines them, and saves to a text file.
    """
    print(f"  Scraping Category Index: {category_name} from {category_url}")
    headers = {'User-Agent': USER_AGENT}
    # Start with a header for the output file
    combined_content = f"# {category_name} - Recent Posts (Fetched {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')})\n\n"
    any_article_scraped = False

    try:
        # Fetch the category index page
        index_response = requests.get(category_url, headers=headers, timeout=15)
        index_response.raise_for_status()
        index_soup = BeautifulSoup(index_response.text, 'html.parser')

        container = index_soup.select_one('div.cont-box')
        if not container:
            print(f"    ERROR: Could not find container 'div.cont-box' for {category_name}.")
            combined_content += "Error: Could not find article container on index page.\n"
        else:
            # Find all article links within the container
            article_links = container.select('a.list-item') # Find all article preview blocks/links
            if not article_links:
                 print(f"    WARN: No articles ('a.list-item') found in container for {category_name}.")
                 combined_content += "(No articles found on index page)\n"
            else:
                print(f"    Found {len(article_links)} links. Scraping content for top {MAX_ARTICLES_PER_CATEGORY}...")
                article_count = 0
                for link_tag in article_links[:MAX_ARTICLES_PER_CATEGORY]: # Limit number processed
                    article_url = link_tag.get('href')
                    if not article_url:
                        print("      WARN: Found list item without href link, skipping.")
                        continue

                    # Make URL absolute if it's relative
                    if not article_url.startswith(('http:', 'https:')):
                         from urllib.parse import urljoin
                         article_url = urljoin(category_url, article_url)

                    # Try to get title from the index page itself
                    title_tag = link_tag.select_one('h2')
                    title = title_tag.text.strip() if title_tag else f"Article {article_count + 1}"

                    # Scrape the content of the individual article page
                    article_text = scrape_article_content(article_url)

                    # Append formatted content to the combined string
                    combined_content += f"## {title}\n\n"
                    combined_content += f"{article_text}\n\n"
                    combined_content += f"Source URL: {article_url}\n"
                    combined_content += "---\n\n" # Separator between articles
                    any_article_scraped = True # Mark that we processed at least one
                    article_count += 1

                    time.sleep(0.3) # Small delay between scraping individual articles

                if not any_article_scraped:
                     combined_content += "(Could not process any article links found)\n"

    except requests.exceptions.RequestException as e:
        print(f"    ERROR: Network request failed for category index {category_name}: {e}")
        combined_content += f"Error fetching index page: {e}\n"
    except Exception as e:
        print(f"    ERROR: Parsing failed for category index {category_name}: {e}")
        combined_content += f"Error parsing index page: {e}\n"

    # Save the combined content (or error messages) to the file
    try:
        os.makedirs(INFO_OUTPUT_DIR, exist_ok=True)
        with open(output_filepath, 'w', encoding='utf-8') as f:
            f.write(combined_content.strip()) # Write combined content, remove trailing whitespace
        print(f"    Saved combined content to: {os.path.basename(output_filepath)}")
    except Exception as e:
        print(f"    ERROR: Failed to write to file {output_filepath}: {e}")
        any_article_scraped = False # Mark as overall failure if save fails

    return any_article_scraped # Return True if at least one article seemed to process okay



def update_all_info_files():
    """Loops through defined categories and updates their respective info files."""
    print("\n--- Updating Info Files from Official Site ---")
    success_count = 0
    error_count = 0
    total_categories = len(INFO_CATEGORIES)

    for i, (category, (filename, url)) in enumerate(INFO_CATEGORIES.items()):
        # --- GUI Progress Update ---
        if root and root.winfo_exists():
             try:
                 progress_percent = int(((i + 1) / total_categories) * 100) if total_categories > 0 else 0
                 status_msg = f"Status: Updating Info Files... ({i+1}/{total_categories}) {progress_percent}% - {category}"
                 root.after(0, lambda msg=status_msg: status_var.set(msg) if status_var else None)
             except Exception: pass
        # --- End GUI Update ---

        if not url: # Skip categories without a URL (like Overview if we kept it)
            print(f"  Skipping category '{category}' (no URL defined).")
            continue

        output_path = os.path.join(INFO_OUTPUT_DIR, filename)
        if scrape_and_update_info_file(category, url, output_path):
            success_count += 1
        else:
            error_count += 1
        time.sleep(0.5) # Small delay between category requests

    print(f"--- Finished Updating Info Files. Successful: {success_count}/{total_categories}, Errors: {error_count} ---")
    return total_categories, success_count, error_count




# --- CORRECTED Tracker Scraping Function ---
def scrape_rivals_tracker_stats_direct(tracker_url, hero_name):
    """Scrapes RivalsTracker.com stats directly using BeautifulSoup."""
    if not tracker_url:
        print(f"    SKIP (Tracker): No URL provided for {hero_name}.")
        return None # Return None if no URL

    print(f"    Requesting Tracker: {tracker_url[:80]}...")
    headers = {'User-Agent': USER_AGENT}
    stats = { # Initialize with None
        "tier": None, "win_rate": None, "wr_change": None,
        "pick_rate": None, "pr_change": None, "ban_rate": None, "matches": None
    }

    try:
        response = requests.get(tracker_url, headers=headers, timeout=15)
        response.raise_for_status() # Check for HTTP errors (4xx, 5xx)
    except requests.exceptions.Timeout:
        print(f"    ERROR (Tracker): Request timed out for {tracker_url}")
        return stats # Return initial None dict on timeout
    except requests.exceptions.RequestException as e:
        print(f"    ERROR (Tracker): Request failed: {e}")
        return stats # Return initial None dict on other request errors

    print(f"    Parsing tracker page for '{hero_name}'...")
    try:
        soup = BeautifulSoup(response.text, 'html.parser')

        # Find the table body - adjust selector if the site structure changes
        # Common structure is a table, tbody often contains the data rows
        table_body = soup.select_one('table tbody') # Basic selector, might need refinement
        if not table_body:
            # Fallback selectors if the first fails
            table_body = soup.find('tbody')
            if not table_body:
                 # Check if the table exists at all
                 table = soup.find('table')
                 if table:
                     print(f"    WARN (Tracker): Found table but no tbody. Trying direct rows.")
                     rows = table.find_all('tr')
                 else:
                     print(f"    ERROR (Tracker): Could not find table or tbody element.")
                     return stats # Return initial None dict if table structure not found
            else:
                 rows = table_body.find_all('tr') # Use find_all on tbody
        else:
            rows = table_body.find_all('tr') # Use find_all on tbody

        if not rows:
            print(f"    ERROR (Tracker): Found table structure but no data rows (tr).")
            return stats # Return initial None dict if no rows

        found_hero = False
        for row in rows:
            # Find the cell containing the hero name (usually the first or second cell with a link)
            # Adjust selector based on actual HTML structure
            # Example: Look for 'td' containing an 'a' tag with the hero name text
            # This selector looks for the 'a' tag directly within the 'td'
            name_cell_link = row.select_one('td a')
            if name_cell_link:
                current_row_hero_name = name_cell_link.text.strip()
            else:
                 # Fallback: if no link, try the first cell's text directly
                 name_cell_direct = row.select_one('td:nth-of-type(1)') # Try first cell directly
                 if name_cell_direct:
                     current_row_hero_name = name_cell_direct.text.strip()
                 else:
                     continue # Skip row if name cell cannot be found

            # Compare names (case-insensitive)
            if current_row_hero_name.lower() == hero_name.lower():
                found_hero = True
                print(f"    Found row for '{hero_name}'. Extracting stats...")
                cells = row.find_all('td') # Get all cells in this specific row

                # Expected number of cells (adjust based on website: Name, Tier, WR, WR+/-, PR, PR+/-, BR, Matches)
                expected_cells = 8
                if len(cells) >= expected_cells:
                    try:
                        # Extract stats based on typical column order. VERIFY THIS ORDER on the website.
                        # Indices are 0-based.
                        stats["tier"] = cells[1].text.strip() or None # Tier = 2nd cell
                        stats["win_rate"] = cells[2].text.strip() or None # WR = 3rd cell
                        stats["wr_change"] = cells[3].text.strip() or None # WR Change = 4th cell
                        stats["pick_rate"] = cells[4].text.strip() or None # PR = 5th cell
                        stats["pr_change"] = cells[5].text.strip() or None # PR Change = 6th cell
                        stats["ban_rate"] = cells[6].text.strip() or None # BR = 7th cell
                        stats["matches"] = cells[7].text.strip() or None # Matches = 8th cell
                        print(f"    SUCCESS (Tracker): Extracted stats: {stats}")
                        return stats # Return the populated dictionary
                    except IndexError:
                         print(f"    WARN (Tracker): Row for '{hero_name}' found, but cell index out of range (expected {expected_cells}, found {len(cells)}). Structure changed?")
                         return stats # Return the partially filled/None dict
                    except Exception as cell_e:
                         print(f"    WARN (Tracker): Error accessing cell data for '{hero_name}': {cell_e}")
                         return stats # Return the partially filled/None dict
                else:
                    print(f"    WARN (Tracker): Row for '{hero_name}' found, but incorrect cell count (expected {expected_cells}, found {len(cells)}).")
                    return stats # Return initial None dict

        if not found_hero:
            print(f"    WARN (Tracker): Hero '{hero_name}' not found in the tracker table.")
            return stats # Return initial None dict

    except Exception as e:
        print(f"    ERROR (Tracker): Parsing failed: {e}")
        import traceback
        traceback.print_exc(file=sys.stderr)
        return stats # Return initial None dict on parsing error


# ==============================================================================
# == GUI ACTION FUNCTION DEFINITIONS ==
# ==============================================================================

# --- GUI Helper to Update All Character Dropdowns ---
# --- CORRECTED update_all_character_dropdowns ---
def update_all_character_dropdowns(initial_setup=False):
    """Updates all character dropdowns with the current ACTIVE_CHARACTER_LIST."""
    global json_character_dropdown, scraper_character_dropdown, tune_character_dropdown # Make sure these are accessible

    dropdowns_vars = []
    if 'scraper_character_var' in globals() and 'scraper_character_dropdown' in globals():
        dropdowns_vars.append((scraper_character_var, scraper_character_dropdown))
    if 'json_character_var' in globals() and 'json_character_dropdown' in globals():
        dropdowns_vars.append((json_character_var, json_character_dropdown))
    if 'tune_character_var' in globals() and 'tune_character_dropdown' in globals():
        dropdowns_vars.append((tune_character_var, tune_character_dropdown))

    options = ACTIVE_CHARACTER_LIST if ACTIVE_CHARACTER_LIST else ["(No Characters Found)"]
    previously_selected_value = None # Store selection to try and restore

    # Get current selection if possible (only needed if restoring)
    if not initial_setup and dropdowns_vars:
        try:
            # Try getting from the first dropdown's variable
            if dropdowns_vars[0][0]:
                 previously_selected_value = dropdowns_vars[0][0].get()
                 if previously_selected_value not in ACTIVE_CHARACTER_LIST:
                      previously_selected_value = None # Invalidate if not in current list
        except tk.TclError:
            previously_selected_value = None

    # If no valid previous selection, default to first item if list is not empty
    if not previously_selected_value and options and options[0] != "(No Characters Found)":
        previously_selected_value = options[0]

    for var, dd in dropdowns_vars:
        if dd and dd.winfo_exists():
            try:
                # Store current value before changing options (though we use previously_selected_value)
                # current_val = var.get() if var else None

                dd['values'] = options # Update the list in the combobox

                # Try to set the value
                if previously_selected_value and previously_selected_value in options:
                    if var: var.set(previously_selected_value)
                    dd.set(previously_selected_value) # Also set combobox display
                elif options and options[0] != "(No Characters Found)":
                    # Set to first actual character if previous selection failed
                    if var: var.set(options[0])
                    dd.set(options[0])
                else:
                    # List is empty or only has placeholder
                    if var: var.set("")
                    dd.set("")

                # Trigger dependent updates *unless* initial setup
                if not initial_setup:
                    if dd == scraper_character_dropdown:
                        if 'update_scraper_url_listbox' in globals(): update_scraper_url_listbox()
                    elif dd == json_character_dropdown:
                        if 'update_json_paths' in globals(): update_json_paths()
                    elif dd == tune_character_dropdown:
                        if 'load_current_json_for_tuning' in globals(): load_current_json_for_tuning()
                # Special cases for initial setup if needed (e.g., path label)
                elif dd == json_character_dropdown:
                     if 'update_json_paths' in globals(): update_json_paths()


            except tk.TclError as e:
                print(f"Error updating dropdown UI: {e}")
            except Exception as e:
                print(f"Unexpected error updating dropdown {dd}: {e}")

# --- GUI Button/Callback Functions ---
def disable_buttons():
    try:
        widgets_to_disable = [
            scrape_button, scrape_all_button, add_url_button, remove_url_button,
            generate_json_button, generate_all_json_button, edit_prompt_button,
            open_prompt_dir_button, model_combobox, create_char_button,
            tune_load_button, tune_preview_button, tune_save_button,
            tune_discard_button, tune_model_combobox
        ]
        for w in widgets_to_disable:
             if w and isinstance(w, (tk.Widget, ttk.Widget)) and w.winfo_exists(): # Check type and existence
                 try:
                     w.config(state=tk.DISABLED)
                 except tk.TclError: pass # Ignore errors if widget destroyed mid-process

        # Handle stop button visibility separately
        is_scraping_all = scrape_all_thread and scrape_all_thread.is_alive()
        if 'stop_button' in globals() and stop_button and stop_button.winfo_exists():
            # Make sure action_frame_tab1 exists before trying to pack into it
            if is_scraping_all and 'action_frame_tab1' in globals() and action_frame_tab1 and action_frame_tab1.winfo_exists():
                try:
                    # Pack if not already packed in the correct parent
                    if stop_button.master != action_frame_tab1:
                        stop_button.pack(side=tk.LEFT, padx=(10, 0), in_=action_frame_tab1)
                    stop_button.config(text="Stop Scrape All", state=tk.NORMAL)
                except tk.TclError: pass # Ignore packing errors
            else:
                try:
                    stop_button.pack_forget() # Hide if scrape all not running
                except tk.TclError: pass
        elif is_scraping_all:
             print("WARN: Stop button defined but doesn't exist in disable_buttons.")

    except (tk.TclError, NameError, AttributeError) as e:
        # Avoid printing errors during shutdown or GUI transitions
        # print(f"Minor error during disable_buttons: {e}")
        pass


def enable_buttons():
    try:
        # Check which major processes are active
        scrape_active = scrape_all_thread and scrape_all_thread.is_alive()
        json_gen_active = (json_gen_single_thread and json_gen_single_thread.is_alive()) or \
                          (json_gen_all_thread and json_gen_all_thread.is_alive())
        tune_active = json_tune_thread and json_tune_thread.is_alive()
        any_process_active = scrape_active or json_gen_active or tune_active

        # Helper to set state safely
        def set_state(widget, target_state):
            if widget and isinstance(widget, (tk.Widget, ttk.Widget)) and widget.winfo_exists():
                try:
                    # Special handling for combobox readonly state
                    if isinstance(widget, ttk.Combobox) and target_state == tk.NORMAL:
                        widget.config(state="readonly")
                    else:
                        widget.config(state=target_state)
                except tk.TclError: pass # Ignore errors if widget is destroyed

        # --- Tab 1: Scraper ---
        set_state(scrape_button, tk.DISABLED if any_process_active else tk.NORMAL)
        set_state(scrape_all_button, tk.DISABLED if any_process_active else tk.NORMAL)
        set_state(add_url_button, tk.DISABLED if any_process_active else tk.NORMAL)
        # Remove button state depends on listbox selection
        if 'scraper_url_listbox' in globals() and scraper_url_listbox and scraper_url_listbox.winfo_exists():
             on_listbox_select(None) # Trigger update based on current selection
        else:
             set_state(remove_url_button, tk.DISABLED)

        # --- Tab 2: Add Character ---
        set_state(create_char_button, tk.DISABLED if any_process_active else tk.NORMAL)

        # --- Tab 3: Generate JSON ---
        set_state(generate_all_json_button, tk.DISABLED if any_process_active else tk.NORMAL)
        set_state(edit_prompt_button, tk.DISABLED if any_process_active else tk.NORMAL)
        set_state(open_prompt_dir_button, tk.DISABLED if any_process_active else tk.NORMAL)
        set_state(model_combobox, tk.DISABLED if any_process_active else tk.NORMAL) # Will be set to readonly
        # Single generate button state depends on raw file existence too
        if 'update_json_paths' in globals():
             update_json_paths() # Let this function handle generate_json_button state

        # --- Tab 4: Fine-Tune ---
        set_state(tune_load_button, tk.DISABLED if any_process_active else tk.NORMAL)
        set_state(tune_model_combobox, tk.DISABLED if any_process_active else tk.NORMAL) # Will be set to readonly

        # Preview button depends on JSON being loaded *and* no process active
        can_preview = original_loaded_json_str is not None and not any_process_active
        set_state(tune_preview_button, tk.NORMAL if can_preview else tk.DISABLED)

        # Save/Discard buttons depend on a proposal existing *and* no process active
        can_save_discard = proposed_tuned_json_data is not None and not any_process_active
        set_state(tune_save_button, tk.NORMAL if can_save_discard else tk.DISABLED)
        set_state(tune_discard_button, tk.NORMAL if can_save_discard else tk.DISABLED)

        # --- Stop Button ---
        if 'stop_button' in globals() and stop_button and stop_button.winfo_exists():
             if not scrape_active: # Hide only if scrape_all is definitely not running
                  stop_button.pack_forget()
             # else: it should have been configured in disable_buttons

        # --- Progress Bar ---
        if not scrape_active: # Reset progress only if scrape_all isn't running
             if 'progress_var' in globals() and progress_var and isinstance(progress_var, tk.DoubleVar):
                 try: progress_var.set(0)
                 except tk.TclError: pass
             if 'time_remaining_var' in globals() and time_remaining_var and isinstance(time_remaining_var, tk.StringVar):
                 try: time_remaining_var.set("")
                 except tk.TclError: pass

    except (tk.TclError, NameError, AttributeError) as e:
        # print(f"Minor error during enable_buttons: {e}") # Keep this commented unless debugging specific state issues
        pass

# --- Add Character Logic ---
def create_new_character():
    # Get values from GUI entries
    new_name = add_char_name_entry.get().strip() if add_char_name_entry else ""
    img_file = add_char_img_entry.get().strip() if add_char_img_entry else ""
    icon_file = add_char_icon_entry.get().strip() if add_char_icon_entry else ""
    wiki_url = add_char_wiki_entry.get().strip() if add_char_wiki_entry else ""
    tracker_url = add_char_tracker_entry.get().strip() if add_char_tracker_entry else ""
    comic_url = add_char_comic_entry.get().strip() if add_char_comic_entry else ""

    # --- Input Validation ---
    if not new_name: messagebox.showerror("Input Error", "Character Name cannot be empty."); return
    # Check for duplicates (case-insensitive)
    if new_name.lower() in [name.lower() for name in ACTIVE_CHARACTER_LIST]:
        messagebox.showerror("Duplicate Error", f"Character '{new_name}' already exists (check JSON folder)."); return
    # Basic check for required image/icon filenames (adjust if they become optional)
    if not img_file: messagebox.showerror("Input Error", "Main Image Filename cannot be empty."); return
    if not icon_file: messagebox.showerror("Input Error", "Icon Filename cannot be empty."); return
    # Basic URL validation (allow empty)
    urls_to_validate = [(wiki_url, "Wiki URL"), (tracker_url, "Tracker URL"), (comic_url, "Comic Wiki URL")];
    for url, label in urls_to_validate:
        if url and not (url.startswith("http://") or url.startswith("https://")):
             messagebox.showerror("Input Error", f"Invalid format for {label}. Must start with http:// or https:// (or be empty)."); return

    print(f"\n--- Creating Files for New Character: '{new_name}' ---");
    disable_buttons()
    success = True; error_details = []

    try:
        # --- 1. Create Base JSON ---
        print("  Creating base JSON file...")
        # Define base structure (matches schema, empty lists/nulls)
        char_data = {
            "name": new_name,
            "role": None,
            "stats": { "health": None, "speed": None, "difficulty": None, "color_theme": None, "color_theme_secondary": None },
            "abilities": [],
            "ultimate": None,
            "passives": [],
            "teamups": [],
            "gameplay": { "strategy_overview": None, "weaknesses": [], "achievements": [] },
            "lore_details": { "ingame_bio_quote": None, "ingame_bio_text": None, "ingame_story_intro": None, "hero_stories": [], "balance_changes": [], "official_quote": None, "official_description": None },
            "background": { "real_name": None, "aliases": [], "birthplace": None, "birthdate": None, "gender": None, "eye_color": None, "hair_color": None, "relatives": [], "affiliation": [], "first_appearance_comic": None, "recommended_comics": [], "lore_powers_skills": [] },
            "misc": { "voice_actor": None, "quotes_link": None, "community_buzz": None, "helpful_links": [] },
            "meta_stats": { "tier": None, "win_rate": None, "wr_change": None, "pick_rate": None, "pr_change": None, "ban_rate": None, "matches": None },
            "data_sources": { # Populate from input URLs
                "wiki": [wiki_url] if wiki_url else [],
                "tracker": [tracker_url] if tracker_url else [],
                "comic_wiki": [comic_url] if comic_url else []
            }
        }
        # Sanitize name for filename
        json_filename = sanitize_filename(new_name, ".json")
        if not json_filename: raise ValueError("Failed to sanitize character name for JSON file.") # Should not happen with corrected sanitize
        json_filepath = os.path.join(CHARACTER_JSON_OUTPUT_DIR, json_filename)
        # Ensure directory exists
        os.makedirs(CHARACTER_JSON_OUTPUT_DIR, exist_ok=True)
        # Write the JSON file
        with open(json_filepath, 'w', encoding='utf-8') as f:
            json.dump(char_data, f, indent=2, ensure_ascii=False) # Use indent=2 for readability
        print(f"    Created: {json_filepath}")

        # --- 2. Update Image Config ---
        print("  Updating image config...")
        img_config = load_config_json(CHAR_IMG_CONFIG)
        if isinstance(img_config, dict):
            img_config[new_name] = img_file # Add/update entry
            if not save_config_json(img_config, CHAR_IMG_CONFIG):
                success = False; error_details.append("Failed to save image config.")
                print("    ERROR: Failed saving image config.")
        else:
             success = False; error_details.append("Image config file is invalid.")
             print(f"    ERROR: Loaded image config ({CHAR_IMG_CONFIG}) is not a dictionary.")

        # --- 3. Update Icon Config (only proceed if previous steps successful) ---
        if success:
            print("  Updating icon config...")
            icon_config = load_config_json(CHAR_ICON_CONFIG)
            if isinstance(icon_config, dict):
                icon_config[new_name] = icon_file # Add/update entry
                if not save_config_json(icon_config, CHAR_ICON_CONFIG):
                    success = False; error_details.append("Failed to save icon config.")
                    print("    ERROR: Failed saving icon config.")
            else:
                 success = False; error_details.append("Icon config file is invalid.")
                 print(f"    ERROR: Loaded icon config ({CHAR_ICON_CONFIG}) is not a dictionary.")

        # --- 4. Update Scraper URL List (only proceed if previous steps successful) ---
        if success:
            print("  Updating scraper URL list...")
            new_char_urls = [url for url in [wiki_url, tracker_url, comic_url] if url] # Collect non-empty URLs
            if new_char_urls:
                load_urls() # Load current URLs
                character_urls[new_name] = new_char_urls # Add/update entry
                save_urls() # Save back to file
                print(f"    Added/Updated URLs for {new_name}: {new_char_urls}")
            else:
                print("    No URLs provided for scraper list.")

    except Exception as e:
        success = False; error_details.append(f"Unexpected error: {e}")
        messagebox.showerror("File Creation Error", f"An unexpected error occurred during file creation:\n{e}")
        print(f"ERROR during character creation: {e}")
        import traceback
        traceback.print_exc(file=sys.stderr) # Log detailed traceback

    finally:
        if success:
            print("  Refreshing character lists and GUI...")
            load_character_list_from_files() # Reload the master list
            update_all_character_dropdowns() # Update all dropdowns

            # Try to select the newly added character in dropdowns
            if 'scraper_character_var' in globals() and scraper_character_var: scraper_character_var.set(new_name)
            if 'json_character_var' in globals() and json_character_var: json_character_var.set(new_name)
            if 'tune_character_var' in globals() and tune_character_var: tune_character_var.set(new_name)

            # Clear input fields
            if add_char_name_entry: add_char_name_entry.delete(0, END)
            if add_char_img_entry: add_char_img_entry.delete(0, END)
            if add_char_icon_entry: add_char_icon_entry.delete(0, END)
            if add_char_wiki_entry: add_char_wiki_entry.delete(0, END)
            if add_char_tracker_entry: add_char_tracker_entry.delete(0, END)
            if add_char_comic_entry: add_char_comic_entry.delete(0, END)

            messagebox.showinfo("Success", f"Character '{new_name}' created successfully.\nRemember to place '{img_file}' and '{icon_file}' in the images folder if you haven't already.")
            if status_var: status_var.set(f"Status: Successfully added '{new_name}'.")
        else:
             errmsg = f"Failed to add '{new_name}'."
             if error_details: errmsg += f" Errors: {'; '.join(error_details)}"
             if status_var: status_var.set(f"Status: {errmsg}")
             print(f"--- Character Creation Failed for '{new_name}' ---")
             # No need for another messagebox, error should have been shown in except block

        enable_buttons() # Re-enable buttons regardless of success/failure


# ==============================================================================
# == CORE SCRAPING & PROCESSING LOGIC ==
# ==============================================================================

# --- Core Scraping Logic ---
def scrape_single_wiki_page(url, filepath, append_mode=False, source_url=""):
    headers = {'User-Agent': USER_AGENT}
    print(f"--> Scraping: {url[:80]}...")
    success = False
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
        soup = BeautifulSoup(response.text, 'html.parser')

        raw_text = ""
        # Try finding the main content area (common patterns)
        content_area = soup.find('div', class_='mw-parser-output') \
                       or soup.find('div', id='mw-content-text') \
                       or soup.find('main', id='content') \
                       or soup.find('div', id='bodyContent') \
                       or soup.find('article')

        extract_method = "Unknown"
        if content_area:
            extract_method = "Targeted Content Area"
            # Remove common unwanted elements *within* the content area
            # Navboxes, sidebars, infoboxes (often tables or divs)
            for tag in content_area.find_all(['div', 'table'], class_=re.compile(r'navbox|sidebar|infobox|metadata|ambox', re.I)):
                tag.decompose()
            # Table of Contents
            for tag in content_area.find_all(id='toc'):
                tag.decompose()
            # Image galleries
            for tag in content_area.find_all('ul', class_='gallery'):
                tag.decompose()
            # Edit section links
            for tag in content_area.find_all('span', class_='mw-editsection'):
                tag.decompose()
            # Other common clutter (related articles, ads, etc.) - Be cautious with broad regex
            for tag in content_area.find_all(['div', 'aside'], class_=re.compile(r'related|community|advert|promo|recommend|noprint|printfooter', re.I)):
                 tag.decompose()
            # Script and style tags just in case they are inside content
            for s in content_area.find_all(['script', 'style']):
                 s.decompose()

            # Extract text after cleaning
            raw_text = content_area.get_text(separator='\n', strip=True)
        else:
            # Fallback: Try finding the body tag
            body = soup.find('body')
            if body:
                extract_method = "Body Fallback"
                # Remove scripts and styles from the whole body
                for s in body.find_all(['script', 'style']):
                    s.decompose()
                raw_text = body.get_text(separator='\n', strip=True)
            else:
                # Absolute fallback: Full page text (least desirable)
                extract_method = "Page Fallback"
                # Attempt to remove script/style from whole soup
                for s in soup.find_all(['script', 'style']):
                     s.decompose()
                raw_text = soup.get_text(separator='\n', strip=True)
                print(f"    WARN: Could not find content area or body. Using {extract_method}.")

        # Post-processing text cleanup
        if raw_text:
            # Remove [edit] links specifically if missed
            raw_text = re.sub(r'\s*\[\s*edit\s*\]\s*', '', raw_text, flags=re.IGNORECASE)
            # Reduce multiple newlines to max two
            raw_text = re.sub(r'\n{3,}', '\n\n', raw_text).strip()

        if not raw_text:
            print(f"    WARN: No text extracted from {url} using method '{extract_method}'.")
            return False # Indicate failure if no text extracted

        # Ensure directory exists before writing
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        file_mode = 'a' if append_mode else 'w'

        # Write to file
        with open(filepath, file_mode, encoding='utf-8') as f:
            if append_mode:
                # Add a clear separator when appending
                f.write("\n\n" + "="*20 + f" APPENDED CONTENT FROM: {source_url} " + "="*20 + "\n\n")
            elif source_url and file_mode == 'w': # Add source only if overwriting
                f.write(f"===== CONTENT FROM: {source_url} =====\n\n")
            f.write(raw_text) # Write content

        print(f"    Success ({extract_method}) - Saved to: {os.path.basename(filepath)}")
        success = True
        return True

    except requests.exceptions.HTTPError as e:
        print(f"    Error scraping {url}: HTTP Error {e.response.status_code} - {e.response.reason}")
    except requests.exceptions.ConnectionError as e:
        print(f"    Error scraping {url}: Connection Error - {e}")
    except requests.exceptions.Timeout:
        print(f"    Error scraping {url}: Request Timed Out")
    except requests.exceptions.RequestException as e:
        print(f"    Error scraping {url}: General Request Error - {e}")
    except Exception as e:
        print(f"    Error scraping or processing {url}: {e}")
        import traceback
        traceback.print_exc(file=sys.stderr) # Print full traceback for unexpected errors

    return False # Return False if any exception occurred


def scrape_all_urls_for_single_character(character_name, urls_to_scrape):
    """Scrapes all provided URLs for a character, saving to a single _raw.txt file."""
    if not urls_to_scrape:
        print(f"Skipping Raw Text scrape for {character_name}: No URLs provided.")
        return 0 # Return 0 successes if no URLs

    print(f"\n--- Scraping Raw Text: {character_name} ---")
    sys.stdout.flush() # Ensure message appears immediately

    filename_base = sanitize_filename(character_name, extension="")
    if not filename_base:
        print(f"  ERROR: Could not generate valid filename base for '{character_name}'. Skipping scrape.")
        return 0
    filename = f"{filename_base}_raw.txt"
    filepath = os.path.join(RAW_TEXT_DIR, filename)

    success_count = 0
    total_urls = len(urls_to_scrape)
    first_scrape_successful = False # Track if we successfully wrote the first file (overwrite mode)

    # Ensure raw text directory exists
    os.makedirs(RAW_TEXT_DIR, exist_ok=True)

    # Overwrite existing file completely on the first successful scrape attempt for this character run
    # Remove file beforehand to ensure a clean start for this session
    if os.path.exists(filepath):
        try:
            os.remove(filepath)
            print(f"  Removed existing raw file: {os.path.basename(filepath)}")
        except OSError as e:
            print(f"  WARN: Failed to remove existing file '{os.path.basename(filepath)}': {e}")

    for i, url in enumerate(urls_to_scrape):
        if stop_scrape_all_flag.is_set():
            print(f"    Scrape cancelled by user request.")
            break # Exit loop if stop flag is set

        print(f"  Scraping URL {i+1}/{total_urls}:")
        sys.stdout.flush()

        # Determine append mode: Append if this is NOT the first *successful* scrape in this run
        append_mode = first_scrape_successful

        if scrape_single_wiki_page(url, filepath, append_mode=append_mode, source_url=url):
            success_count += 1
            first_scrape_successful = True # Mark that we've successfully written at least once

        # Add delay between requests for the same character
        time.sleep(SCRAPE_DELAY_SECONDS / 2) # Shorter delay between URLs for the same char

    print(f"--- Finished Raw Scrape for {character_name}: {success_count}/{total_urls} URLs successfully scraped. ---")
    sys.stdout.flush()
    return success_count

# --- Threading functions for scraping ---
# --- Replace the existing function with this CLEANED version ---
def scrape_single_character_thread(character_arg, urls_to_scrape_arg):
    """Target function for the thread that scrapes raw text for one character."""
    # Use the passed arguments directly throughout the function
    character = character_arg
    urls_to_scrape = urls_to_scrape_arg

    start_time = time.time()
    if status_var:
        # Use the local 'character' variable
        status_var.set(f"Status: Scraping Raw Text for {character}...")

    stop_scrape_all_flag.clear() # Ensure flag is clear for single scrape

    # Call the main scraping logic function, passing the arguments
    success_count = scrape_all_urls_for_single_character(character, urls_to_scrape) # Store the return value

    # Prepare result message using local variables
    duration = str(datetime.timedelta(seconds=int(time.time() - start_time)))
    num_urls = len(urls_to_scrape) if isinstance(urls_to_scrape, list) else 0
    result_msg = f"Status: Finished scraping raw text for {character} ({success_count}/{num_urls} URLs) in {duration}."

    # Update GUI from the main thread
    def update_ui():
        if root and root.winfo_exists():
            if status_var:
                status_var.set(result_msg) # Use the prepared result_msg
            # Re-enable buttons after completion
            enable_buttons()

    if root and root.winfo_exists():
        root.after(0, update_ui) # Schedule GUI update

    # --- REDUNDANT BLOCK HAS BEEN REMOVED ---

# --- End of scrape_single_character_thread function ---

update_info_files_thread_handle = None

# --- CORRECTED update_info_files_thread ---
# <<< Make sure this function definition exists in your file >>>
def update_info_files_thread():
    """Runs the info file update process in the background and updates last_update.json."""
    global update_info_files_thread_handle # Allow modification of the global handle

    start_time = time.time()
    if status_var: status_var.set("Status: Starting Info File update...")

    # --- Call the main function that does the scraping ---
    # Assumes update_all_info_files() exists and returns (total, success, errors)
    try:
        total, success, errors = update_all_info_files()
    except NameError:
        print("ERROR: update_all_info_files function not found!")
        total, success, errors = 0, 0, 1 # Simulate error
    except Exception as e:
        print(f"ERROR during info file update process: {e}")
        import traceback
        traceback.print_exc(file=sys.stderr)
        total, success, errors = len(INFO_CATEGORIES), 0, len(INFO_CATEGORIES) # Assume all failed on unexpected error
    # --- End scraping call ---

    end_time = time.time()
    duration = str(datetime.timedelta(seconds=int(end_time - start_time)))
    final_message = f"Status: Info File update COMPLETE. Categories checked: {total}. Success: {success}. Errors: {errors}. Duration: {duration}."

    # --- Update last_update.json ---
    if success > 0: # If at least one category was successfully scraped/saved
         print(f"  Updating last_update.json for Info Files completion...")
         update_last_update_file("last_info_update", datetime.datetime.now().isoformat()) #

         # Attempt to parse and save the latest patch version from balance_post.txt
         # Make sure INFO_OUTPUT_DIR is defined globally or accessible
         try:
             patch_file_path = os.path.join(INFO_OUTPUT_DIR, "balance_post.txt")
         except NameError:
             print("ERROR: INFO_OUTPUT_DIR not defined globally. Cannot check patch file.")
             patch_file_path = None

         latest_patch_version = "Unknown"
         if patch_file_path and os.path.exists(patch_file_path):
             try:
                 with open(patch_file_path, 'r', encoding='utf-8') as f_patch:
                     first_lines = [f_patch.readline() for _ in range(10)]
                 # Look for pattern like "Version YYYYMMDD Balance Post"
                 version_pattern = re.compile(r"Version\s+(\d{8})\s+Balance\s+Post", re.IGNORECASE)
                 for line in first_lines:
                     match = version_pattern.search(line)
                     if match:
                         latest_patch_version = match.group(1)
                         print(f"    Extracted Patch Version: {latest_patch_version}")
                         break
             except Exception as e_patch:
                 print(f"    Warning: Could not read/parse patch version from {os.path.basename(patch_file_path)}: {e_patch}")
         else:
             print(f"    Warning: Balance patch file not found at expected location for version check.")

         update_last_update_file("last_game_patch_parsed", latest_patch_version)
    # --- End Update ---

    print(f"\n=== {final_message} ===") # Keep the final print
    sys.stdout.flush()

    # --- Define the UI finalization callback ---
    def finalize_ui():
        if root and root.winfo_exists():
            if status_var: status_var.set(final_message)
            summary_title = "Info File Update Complete"
            summary_message = f"Info File update finished.\n\nChecked: {total}\nSuccessful: {success}\nErrors: {errors}\n\nCheck logs for details."
            if errors > 0:
                messagebox.showwarning(summary_title, summary_message)
            else:
                messagebox.showinfo(summary_title, summary_message)
            enable_buttons() # Re-enable buttons

    # --- Schedule the UI update on the main thread ---
    if root and root.winfo_exists():
        root.after(0, finalize_ui)

    # --- Clear the thread handle ---
    update_info_files_thread_handle = None # Clear handle

def scrape_all_characters_thread(status_var_ref, time_var_ref, progress_var_ref, status_label_ref, time_label_ref, progress_bar_ref):
    """Target function for scraping all characters with URLs."""
    global stop_scrape_all_flag
    start_time = time.time()

    # Filter characters that actually have URLs defined
    chars_with_urls = {name: urls for name, urls in character_urls.items() if urls and isinstance(urls, list)}
    total_characters_to_process = len(chars_with_urls)

    if total_characters_to_process == 0:
        print("Scrape All Raw Text: No characters with URLs defined.")
        def update_ui_no_urls():
             if root and root.winfo_exists():
                 if status_var_ref: status_var_ref.set("Status: Scrape All Raw Text skipped - no URLs defined.")
                 enable_buttons()
        if root and root.winfo_exists(): root.after(0, update_ui_no_urls)
        return

    processed_count = 0
    total_urls_scraped = 0
    stop_scrape_all_flag.clear() # Ensure flag is clear at start
    print(f"\n=== Starting Scrape ALL Characters Raw Text ({total_characters_to_process} characters) ===")

    # --- Safely update GUI for starting state ---
    def update_status_start(s_var, t_var, p_var, s_label, t_label, p_bar):
        try:
            if s_label and s_label.winfo_exists(): s_var.set(f"Status: Starting Scrape All Raw Text ({total_characters_to_process} characters)...")
            if t_label and t_label.winfo_exists(): t_var.set("Est. Time Left: Calculating...")
            if p_bar and p_bar.winfo_exists(): p_var.set(0)
        except tk.TclError: pass # Ignore if GUI is destroyed during update
    if root and root.winfo_exists(): root.after(0, update_status_start, status_var_ref, time_var_ref, progress_var_ref, status_label_ref, time_label_ref, progress_bar_ref)
    # --- End safe update ---

    # Process characters in sorted order for consistency
    sorted_chars_to_process = sorted(chars_with_urls.keys())

    for i, character_name in enumerate(sorted_chars_to_process):
        if stop_scrape_all_flag.is_set():
            print("\nScrape stopped by user.")
            break # Exit the loop if stop flag is set

        urls = chars_with_urls[character_name]
        elapsed_time = time.time() - start_time
        # Estimate remaining time (avoid division by zero)
        avg_time_per_char_scrape = elapsed_time / (i + 1) if i >= 0 else ESTIMATED_SECONDS_PER_CHAR_SCRAPE
        remaining_chars = total_characters_to_process - (i + 1)
        est_remaining_time = remaining_chars * avg_time_per_char_scrape
        time_left_str = str(datetime.timedelta(seconds=int(est_remaining_time))) if est_remaining_time > 0 else "..."
        # Calculate progress
        progress_percent = int(((i + 1) / total_characters_to_process) * 100) if total_characters_to_process > 0 else 0

        # --- Safely update GUI for progress ---
        def update_status_progress(s_var, t_var, p_var, s_label, t_label, p_bar, current_char_name, current_progress, time_str):
            try:
                current_iter = i + 1 # Get current iteration number for status message
                if s_label and s_label.winfo_exists(): s_var.set(f"Status: Scraping All Raw Text... ({current_iter}/{total_characters_to_process}) - Current: {current_char_name}")
                if t_label and t_label.winfo_exists(): t_var.set(f"Est. Time Left: {time_str}")
                if p_bar and p_bar.winfo_exists(): p_var.set(current_progress)
            except tk.TclError: pass # Ignore if GUI is destroyed during update
        if root and root.winfo_exists(): root.after(0, update_status_progress, status_var_ref, time_var_ref, progress_var_ref, status_label_ref, time_label_ref, progress_bar_ref, character_name, progress_percent, time_left_str)
        # --- End safe update ---

        # Perform the actual scrape for the character
        scraped_count = scrape_all_urls_for_single_character(character_name, urls)
        total_urls_scraped += scraped_count
        processed_count += 1

        # Add a delay between *characters* during scrape all
        if not stop_scrape_all_flag.is_set() and i < total_characters_to_process - 1: # Don't delay after the last one
            print(f"--- Delaying {SCRAPE_DELAY_SECONDS}s before next character ---")
            time.sleep(SCRAPE_DELAY_SECONDS)


    # --- Final Status Update ---
    end_time = time.time()
    duration = str(datetime.timedelta(seconds=int(end_time - start_time)))
    was_stopped = stop_scrape_all_flag.is_set()
    final_message = f"Status: Scrape All Raw Text {'STOPPED' if was_stopped else 'COMPLETE'}. Processed {processed_count}/{total_characters_to_process} chars ({total_urls_scraped} URLs total) in {duration}."

    # --- Safely update GUI for completion/stop ---
    def update_status_final(s_var, p_var, s_label, p_bar, final_msg, stopped):
         try:
             if s_label and s_label.winfo_exists(): s_var.set(final_msg)
             # Set progress to 100 only if completed fully
             if not stopped and p_bar and p_bar.winfo_exists(): p_var.set(100)
             # Re-enable buttons now that the process is finished or stopped
             enable_buttons()
         except tk.TclError: pass
    if root and root.winfo_exists(): root.after(0, update_status_final, status_var_ref, progress_var_ref, status_label_ref, progress_bar_ref, final_message, was_stopped)
    # --- End safe update ---

    print(f"\n=== {final_message} ===")
    sys.stdout.flush()


# --- GUI Tab 1 Callbacks ---
def update_scraper_url_listbox(*args):
    try:
        # Check if essential widgets exist
        if not root or not root.winfo_exists() \
           or 'scraper_url_listbox' not in globals() or not scraper_url_listbox or not scraper_url_listbox.winfo_exists() \
           or 'scraper_character_var' not in globals() or not scraper_character_var:
           # print("DEBUG: update_scraper_url_listbox - Widgets not ready") # Optional debug
           return

        selected_character = scraper_character_var.get()
        scraper_url_listbox.delete(0, END) # Clear existing entries

        if selected_character and selected_character in ACTIVE_CHARACTER_LIST:
            urls = character_urls.get(selected_character, []) # Get URLs for selected char
            if urls and isinstance(urls, list): # Check if list is not empty
                for url in urls:
                    scraper_url_listbox.insert(END, url)
            else:
                # Display placeholder if no URLs saved
                scraper_url_listbox.insert(END, "(No URLs saved for this character)")
                # Optionally style the placeholder
                scraper_url_listbox.itemconfig(0, {'fg':'grey'})
        else:
            # Display placeholder if no valid character selected
            scraper_url_listbox.insert(END, "(Select a character to view/manage URLs)")
            scraper_url_listbox.itemconfig(0, {'fg':'grey'})

        # Update the state of the remove button based on selection
        on_listbox_select(None)

    except (tk.TclError, NameError, AttributeError) as e:
        # print(f"Error in update_scraper_url_listbox: {e}") # Optional debug
        pass # Ignore GUI errors during updates

def add_scraper_url():
    # Check if widgets exist before accessing them
    if not all(['scraper_character_var' in globals() and scraper_character_var,
                'scraper_url_entry' in globals() and scraper_url_entry]):
        print("Error: Add URL widgets not ready.")
        return

    selected_character = scraper_character_var.get()
    new_url = scraper_url_entry.get().strip()

    # Validation
    if not selected_character or selected_character not in ACTIVE_CHARACTER_LIST:
        messagebox.showerror("Error", "Please select a valid character first."); return
    if not new_url:
         messagebox.showerror("Error", "Please enter a URL to add."); return
    if not (new_url.startswith("http://") or new_url.startswith("https://")):
        messagebox.showerror("Error", "Invalid URL format. Must start with http:// or https://"); return

    # Add URL logic
    current_urls = character_urls.get(selected_character, [])
    # Ensure it's a list (might be missing if loaded data was corrupt)
    if not isinstance(current_urls, list): current_urls = []
    if new_url in current_urls:
        messagebox.showwarning("Duplicate", "This URL is already saved for this character."); return

    current_urls.append(new_url)
    character_urls[selected_character] = current_urls
    save_urls() # Persist changes
    update_scraper_url_listbox() # Refresh listbox view
    scraper_url_entry.delete(0, END) # Clear the entry field
    print(f"Added URL for {selected_character}: {new_url}")
    if status_var: status_var.set(f"Status: Added URL for {selected_character}")

def remove_scraper_url():
     # Check if widgets exist before accessing them
    if not all(['scraper_character_var' in globals() and scraper_character_var,
                'scraper_url_listbox' in globals() and scraper_url_listbox]):
        print("Error: Remove URL widgets not ready.")
        return

    selected_character = scraper_character_var.get()
    selection_indices = scraper_url_listbox.curselection() # Get tuple of selected indices

    # Validation
    if not selected_character or selected_character not in ACTIVE_CHARACTER_LIST:
        messagebox.showerror("Error", "Please select a valid character first."); return
    if not selection_indices: # Check if tuple is empty
        messagebox.showerror("Error", "Please select a URL from the list to remove."); return

    selected_index = selection_indices[0] # Get the first selected index
    selected_url = scraper_url_listbox.get(selected_index)

    # Check if it's a placeholder item
    if selected_url.startswith("("):
         return # Do nothing if a placeholder is selected

    # Remove URL logic
    current_urls = character_urls.get(selected_character, [])
    if not isinstance(current_urls, list): current_urls = [] # Ensure list

    if selected_url in current_urls:
        current_urls.remove(selected_url)
        character_urls[selected_character] = current_urls
        save_urls() # Persist changes
        update_scraper_url_listbox() # Refresh listbox view
        print(f"Removed URL for {selected_character}: {selected_url}")
        if status_var: status_var.set(f"Status: Removed URL for {selected_character}")
    else:
        # This case shouldn't happen if listbox is synced, but handle defensively
        messagebox.showerror("Sync Error", "The selected URL was not found in the saved data. Refreshing list.")
        update_scraper_url_listbox()

def on_listbox_select(event):
    """Updates the state of the remove button based on listbox selection."""
    try:
        # Check if widgets exist
        if not all(['remove_url_button' in globals() and remove_url_button and remove_url_button.winfo_exists(),
                    'scraper_url_listbox' in globals() and scraper_url_listbox and scraper_url_listbox.winfo_exists()]):
            return

        # Disable button if any major process is running
        any_process_active = (scrape_all_thread and scrape_all_thread.is_alive()) or \
                             (json_gen_single_thread and json_gen_single_thread.is_alive()) or \
                             (json_gen_all_thread and json_gen_all_thread.is_alive()) or \
                             (json_tune_thread and json_tune_thread.is_alive())
        if any_process_active:
            remove_url_button.config(state=tk.DISABLED)
            return

        # Enable button only if a valid URL (not placeholder) is selected
        selected_text = ""
        selection_indices = scraper_url_listbox.curselection()
        if selection_indices:
            selected_text = scraper_url_listbox.get(selection_indices[0])

        if selected_text and not selected_text.startswith("("):
            remove_url_button.config(state=tk.NORMAL)
        else:
            remove_url_button.config(state=tk.DISABLED)

    except tk.TclError:
        pass # Ignore errors if widgets are destroyed during selection change


# --- CORRECTED update_json_paths ---
def update_json_paths(*args):
    """Updates the output path label and enables/disables the single generate button."""
    try:
        # Check if essential widgets exist
        if not root or not root.winfo_exists(): return
        widgets_exist = all([
            'json_character_var' in globals() and json_character_var is not None,
            'json_output_file_label' in globals() and json_output_file_label and json_output_file_label.winfo_exists(),
            'generate_json_button' in globals() and generate_json_button and generate_json_button.winfo_exists()
        ])
        if not widgets_exist:
            # print("DEBUG: update_json_paths - Widgets not ready") # Optional debug
            return # Don't proceed if GUI isn't ready

        selected_character = json_character_var.get()

        # Check if any generation/tuning process is active
        any_process_active = (json_gen_single_thread and json_gen_single_thread.is_alive()) or \
                              (json_gen_all_thread and json_gen_all_thread.is_alive()) or \
                              (json_tune_thread and json_tune_thread.is_alive())

        if selected_character and selected_character != "(No Characters Found)" and selected_character in ACTIVE_CHARACTER_LIST:
            # Sanitize filename for raw text file check
            raw_filename_base = sanitize_filename(selected_character, extension="")
            if not raw_filename_base:
                print(f"ERROR: sanitize_filename returned invalid base for RAW file check: '{selected_character}'")
                json_output_file_label.config(text="Output JSON: (Error sanitizing name)", foreground="red")
                generate_json_button.config(state=tk.DISABLED)
                return
            raw_filename = f"{raw_filename_base}_raw.txt"
            raw_filepath = os.path.join(RAW_TEXT_DIR, raw_filename)

            # Sanitize name for JSON output path display
            json_filename = sanitize_filename(selected_character, extension=".json")
            if not json_filename:
                 print(f"ERROR: sanitize_filename returned invalid name for JSON file display: '{selected_character}'")
                 json_output_file_label.config(text="Output JSON: (Error sanitizing name)", foreground="red")
                 generate_json_button.config(state=tk.DISABLED)
                 return
            json_filepath = os.path.join(CHARACTER_JSON_OUTPUT_DIR, json_filename)

            # Display the expected JSON output path
            json_output_file_label.config(text=f"Output JSON: {json_filepath}", foreground="black")

            # Determine if generation is possible
            can_generate = os.path.exists(raw_filepath) and not any_process_active
            generate_json_button.config(state=tk.NORMAL if can_generate else tk.DISABLED)

            # Explicitly disable if raw file is missing, even if no process is active
            if not os.path.exists(raw_filepath):
                generate_json_button.config(state=tk.DISABLED)
                # Optionally update status or label to indicate missing raw file
                # json_output_file_label.config(text=f"Output JSON: {json_filepath} (RAW MISSING)", foreground="orange")

        else: # No valid character selected
            json_output_file_label.config(text="Output JSON: (Select Character)", foreground="grey")
            generate_json_button.config(state=tk.DISABLED)

    except (tk.TclError, NameError, AttributeError) as e:
        # print(f"Debug: Error in update_json_paths: {e}") # Optional debug print
        pass # Ignore GUI errors during updates

# --- Button Trigger Functions (Scraping) ---
def start_scrape_single_character():
    if not scraper_character_var: print("Error: Scraper character var not ready."); return
    character = scraper_character_var.get()
    if not character or character not in ACTIVE_CHARACTER_LIST:
        messagebox.showerror("Error", "Please select a valid character from the dropdown."); return

    urls_to_scrape = character_urls.get(character, [])
    if not urls_to_scrape:
        messagebox.showinfo("No URLs", f"No URLs are saved for '{character}'. Add URLs using the 'Manage Source URLs' section."); return

    # Disable buttons and start thread
    disable_buttons()
    threading.Thread(target=scrape_single_character_thread, args=(character, urls_to_scrape), daemon=True).start()

def start_update_info_files():
    """Handles the 'Update Info Files' button click."""
    global update_info_files_thread_handle # Keep access to the handle

    if update_info_files_thread_handle and update_info_files_thread_handle.is_alive():
        print("INFO: Info File update process is already running.")
        messagebox.showinfo("Busy", "The Info File update process is already running.")
        return

    confirm_msg = (
        "This will scrape the official Marvel Rivals website for the latest\n"
        "Announcements, Balance Posts, Dev Diaries, Game Updates, and News.\n\n"
        "It will OVERWRITE the corresponding .txt files in the info/ folder.\n\n"
        "Proceed?"
    )
    if not messagebox.askyesno("Confirm Update Info Files", confirm_msg):
        return

    if status_var: status_var.set("Status: Starting Info File update...")
    disable_buttons()

    # Ensure the target is the correct function name below
    update_info_files_thread_handle = threading.Thread(target=update_info_files_thread, daemon=True)
    update_info_files_thread_handle.start()


def start_scrape_all_characters():
    global scrape_all_thread
    # Check if there are any characters with URLs
    chars_with_urls = {name: urls for name, urls in character_urls.items() if urls and isinstance(urls, list)}
    if not chars_with_urls:
        messagebox.showinfo("No URLs", "No URLs have been saved for any character. Cannot Scrape All."); return

    num_chars = len(chars_with_urls)
    confirm_msg = (
        f"This will attempt to scrape raw text for {num_chars} character(s) with defined URLs.\n\n"
        f"Estimated time depends on the number of URLs per character and the delay ({SCRAPE_DELAY_SECONDS}s between characters).\n\n"
        f"Do you want to proceed?"
    )
    if not messagebox.askyesno("Confirm Scrape All Raw Text", confirm_msg):
        return

    # Disable buttons, reset progress, and start thread
    disable_buttons()
    if progress_var: progress_var.set(0)
    if time_remaining_var: time_remaining_var.set("Starting...")
    stop_scrape_all_flag.clear() # Ensure flag is clear

    # Ensure all GUI refs passed to the thread are valid
    args_for_thread = (
        status_var, time_remaining_var, progress_var,
        status_label, time_remaining_label, progress_bar
    )

    scrape_all_thread = threading.Thread(target=scrape_all_characters_thread, args=args_for_thread, daemon=True)
    scrape_all_thread.start()

def stop_scrape_all():
    global stop_scrape_all_flag
    if scrape_all_thread and scrape_all_thread.is_alive():
        print("\n>>> Sending Stop Signal to Scrape All Raw Text... <<<")
        stop_scrape_all_flag.set()
        # Update button state immediately to give feedback
        if 'stop_button' in globals() and stop_button and stop_button.winfo_exists():
            try:
                stop_button.config(text="Stopping...", state=tk.DISABLED)
            except tk.TclError: pass
    else:
        print("No active 'Scrape All' process to stop.")


# --- Log Management ---
def copy_logs_to_clipboard():
    try:
        if root and root.winfo_exists():
            # Check if log_buffer has content
            log_content = log_buffer.getvalue()
            if log_content:
                root.clipboard_clear()
                root.clipboard_append(log_content)
                print("Log content copied to clipboard.")
                if status_var: status_var.set("Status: Logs copied to clipboard.")
            else:
                print("Log buffer is empty. Nothing to copy.")
                if status_var: status_var.set("Status: Log buffer is empty.")
    except Exception as e:
        print(f"Error copying logs to clipboard: {e}")
        if status_var: status_var.set("Status: Error copying logs.")


# --- Prompt Management ---
def edit_api_prompt():
    prompt_file_path = API_PROMPT_TEMPLATE_FILE
    default_prompt_file_path = DEFAULT_PROMPT_FILE # Keep reference to default

    try:
        # If custom doesn't exist, try creating it from default
        if not os.path.exists(prompt_file_path):
            print(f"Custom prompt template not found: {os.path.basename(prompt_file_path)}")
            if os.path.exists(default_prompt_file_path):
                print(f"Attempting to create '{os.path.basename(prompt_file_path)}' from default...")
                try:
                    shutil.copyfile(default_prompt_file_path, prompt_file_path)
                    print(f"Successfully created custom prompt from default.")
                except Exception as copy_e:
                     messagebox.showerror("Error", f"Could not create custom prompt file from default:\n{copy_e}"); return
            else:
                # If default also missing, cannot proceed
                 messagebox.showerror("Error", f"Cannot edit prompt: Custom template missing AND default template missing:\n{default_prompt_file_path}"); return

        # Now open the custom prompt file (which should exist)
        print(f"Opening prompt template file for editing: {prompt_file_path}")
        if sys.platform == "win32":
            os.startfile(prompt_file_path) # Preferred way on Windows
        elif sys.platform == "darwin": # macOS
            subprocess.call(["open", prompt_file_path])
        else: # Linux/Other Unix-like
            try:
                subprocess.call(["xdg-open", prompt_file_path])
            except FileNotFoundError:
                 messagebox.showerror("Error", "Could not open file. 'xdg-open' command not found. Please open the file manually:\n" + prompt_file_path)
                 return
        if status_var: status_var.set("Status: Opened prompt template file for editing.")

    except Exception as e:
        messagebox.showerror("Error Opening File", f"Could not open prompt template file:\n{e}")
        print(f"Error opening prompt file '{prompt_file_path}': {e}")

def open_prompt_directory():
    try:
        print(f"Opening script directory: {SCRIPT_DIR}")
        if sys.platform == "win32":
            # Use subprocess.Popen to avoid blocking, explorer handles it
            subprocess.Popen(f'explorer "{SCRIPT_DIR}"')
        elif sys.platform == "darwin":
            subprocess.call(["open", SCRIPT_DIR])
        else: # Linux/Other Unix-like
            try:
                subprocess.call(["xdg-open", SCRIPT_DIR])
            except FileNotFoundError:
                 messagebox.showerror("Error", "Could not open directory. 'xdg-open' command not found.")
                 return
        if status_var: status_var.set(f"Status: Opened script directory containing prompts.")

    except Exception as e:
        messagebox.showerror("Error Opening Directory", f"Could not open script directory:\n{e}")
        print(f"Error opening script directory '{SCRIPT_DIR}': {e}")


# ==============================================================================
# == JSON GENERATION FUNCTIONS ==
# ==============================================================================

# --- JSON Generator Tab Functions ---
# Note: update_json_paths is defined earlier due to call order requirements

def start_generate_single_json():
    """Validates input and starts the background thread for single JSON generation."""
    global json_gen_single_thread

    # Check if essential widgets exist
    if not all(['json_character_var' in globals() and json_character_var,
                'model_selection_var' in globals() and model_selection_var]):
        print("Error: JSON generation widgets not ready.")
        return

    selected_character = json_character_var.get()
    selected_model = model_selection_var.get()

    # Validation
    if not selected_character or selected_character not in ACTIVE_CHARACTER_LIST:
        messagebox.showerror("Error", "Please select a valid character."); return
    if not selected_model or selected_model not in AVAILABLE_MODELS:
        messagebox.showerror("Error", "Please select a valid API model."); return
    if not GOOGLE_AI_AVAILABLE:
        messagebox.showerror("Error", "Google AI library is required for JSON generation."); return
    if not google_api_key:
        messagebox.showerror("API Key Error", "Google API Key is missing or invalid. Check .env file or environment variables."); return

    # Check for raw text file
    raw_filename_base = sanitize_filename(selected_character, extension="")
    if not raw_filename_base: messagebox.showerror("Error", f"Could not create valid filename base for '{selected_character}'."); return
    raw_filename = f"{raw_filename_base}_raw.txt"
    raw_filepath = os.path.join(RAW_TEXT_DIR, raw_filename)
    if not os.path.exists(raw_filepath):
        messagebox.showerror("Error", f"Raw Text file not found:\n{raw_filepath}\n\nPlease scrape the raw text for this character first (Tab 1)."); return

    # Prevent starting if already running
    if json_gen_single_thread and json_gen_single_thread.is_alive():
        print("INFO: Single JSON generation process is already running.")
        messagebox.showinfo("Busy", "A JSON generation process is already running for a single character.")
        return

    # Start the process
    print(f"\n--- Starting JSON Generation for {selected_character} ({selected_model}) ---")
    if status_var: status_var.set(f"Status: Starting JSON generation for {selected_character} ({selected_model})...")
    disable_buttons()

    # Start the thread
    json_gen_single_thread = threading.Thread(
        target=generate_single_json_thread,
        args=(selected_character, raw_filepath, selected_model),
        daemon=True # Allows app to exit even if thread hangs
    )
    json_gen_single_thread.start()

# --- CORRECTED generate_single_json_thread function ---
# --- Replace the existing generate_single_json_thread function ---
def generate_single_json_thread(selected_character, raw_filepath, selected_model_name):
    """Performs Raw -> JSON generation, applies patches, preserves specified fields, adds static data."""
    global TOP_LEVEL_SCHEMA_PROPERTIES, PRESERVED_SECTIONS_DURING_CORE_GEN, PRESERVED_NESTED_FIELDS

    print(f"\n--- Processing Single: {selected_character} (Model: {selected_model_name}) ---")
    sys.stdout.flush()

    json_filename_base = sanitize_filename(selected_character, extension="")
    if not json_filename_base:
        error_message_details = f"Failed to sanitize character name '{selected_character}' for output file."
        print(f"  ERROR: {error_message_details}")
        success = False
        final_json_data = None # Ensure variable exists for finally block
    else:
        json_filename = f"{json_filename_base}.json"
        json_filepath = os.path.join(CHARACTER_JSON_OUTPUT_DIR, json_filename)
        success = False
        error_message_details = None
        final_json_data = None
        raw_response_on_error = None
        old_json_data = None # Store loaded existing data

        try:
            # --- 0. Load Existing JSON (for preservation) ---
            if os.path.exists(json_filepath):
                try:
                    with open(json_filepath, 'r', encoding='utf-8') as f_old:
                        old_json_data = json.load(f_old)
                    print(f"  Loaded existing JSON to preserve manual edits.")
                except Exception as load_err:
                    print(f"  WARN: Could not load existing JSON '{os.path.basename(json_filepath)}' for preservation: {load_err}. Will generate fresh.")
                    old_json_data = None # Ensure it's None if loading failed

            # --- 1. Read and Clean Raw Text ---
            print(f"  Reading Raw Text: {os.path.basename(raw_filepath)}")
            sys.stdout.flush()
            with open(raw_filepath, 'r', encoding='utf-8') as f: raw_content = f.read()
            # Basic cleaning (ensure latest cleaning logic is here)
            raw_content = re.sub(r'^===== CONTENT FROM:.*?=====\s*', '', raw_content, flags=re.MULTILINE).strip()
            raw_content = re.sub(r'\n\n={20,}\s*CONTENT FROM:.*?={20,}\s*\n\n', '\n\n---\n\n', raw_content, flags=re.DOTALL)
            raw_content = re.sub(r'\s*\[\s*edit\s*\]\s*', '', raw_content, flags=re.IGNORECASE)
            raw_content = re.sub(r'^\s*See\s*also\s*:.*?\n', '', raw_content, flags=re.MULTILINE | re.IGNORECASE)
            raw_content = re.sub(r'\n{3,}', '\n\n', raw_content).strip()
            print(f"  Raw text read and cleaned.")

            # --- 2. Call AI for Core JSON Structure (Base Generation) ---
            print(f"  Calling AI for Base JSON structure...")
            sys.stdout.flush()
            base_ai_result = generate_json_from_raw_via_api(
                raw_content, selected_character, selected_model_name
            )

            # --- 3. Process Base AI Result ---
            if not isinstance(base_ai_result, dict):
                error_message_details = "Base AI function returned unexpected data type."
                raw_response_on_error = str(base_ai_result)
                raise TypeError(error_message_details)

            if 'error' in base_ai_result:
                error_detail = base_ai_result.get('error', 'Unknown Base AI Error')
                details = base_ai_result.get('details', '')
                raw_response_on_error = base_ai_result.get('raw_response')
                error_message_details = f"Base AI JSON generation failed ({selected_model_name}). Error: {error_detail}. Details: {details}"
                raise Exception(f"Base AI Error: {error_detail}")

            # --- Success: Base AI returned a PARSED dictionary ---
            generated_data = base_ai_result # Rename for clarity
            print(f"  Base AI returned parsable JSON data.")

            # --- 4. Enforce Schema Keys on Generated Data (Important before merge) ---
            print("  Ensuring generated data adheres to schema keys...")
            sys.stdout.flush()
            if TOP_LEVEL_SCHEMA_PROPERTIES:
                generated_data = ensure_schema_keys(generated_data, TOP_LEVEL_SCHEMA_PROPERTIES)
                print("  Generated data schema key enforcement complete.")
            else:
                 print("  WARN: Simplified schema structure not available, skipping key enforcement on generated data.")

            # --- 5. Initialize Final Data (Start with old, or generated if no old) ---
            if old_json_data:
                # Use deep copy to avoid modifying old_json_data inadvertently if needed elsewhere
                import copy
                final_json_data = copy.deepcopy(old_json_data)
                print("  Initialized final data from existing JSON.")
            else:
                final_json_data = generated_data # Start fresh if no old data
                print("  Initialized final data from newly generated JSON (no existing file).")


            # --- 6. Apply Name Correction (to Generated Data before merge, and ensure Final has it) ---
            # Correct name based on AI output BEFORE potential patch merge
            proper_char_name_from_gen = generated_data.get("name", selected_character)
            original_casing_name = proper_char_name_from_gen # Default to what AI gave

            if proper_char_name_from_gen == "HULK": original_casing_name = "Hulk"
            elif proper_char_name_from_gen == "GROOT": original_casing_name = "Groot"
            elif proper_char_name_from_gen == "CLOAK & DAGGER": original_casing_name = "Cloak & Dagger"
            elif proper_char_name_from_gen == "PUNISHER": original_casing_name = "Punisher"
            elif proper_char_name_from_gen == "MISTER FANTASTIC": original_casing_name = "Mister Fantastic"
            # Add other specific ALL CAPS -> Proper Case rules here

            # Apply corrected proper-cased name to the final data
            final_json_data["name"] = original_casing_name
            print(f"  Ensured final character name is: '{original_casing_name}'")


            # --- 7. Merge CORE Generated Data into Final Data ---
            print(f"  Merging core generated fields into final data...")
            core_merged_count = 0
            for key in CORE_GENERATED_KEYS:
                if key in generated_data:
                     # For stats, merge selectively, don't overwrite speed/colors yet
                     if key == "stats" and isinstance(generated_data[key], dict) and isinstance(final_json_data.get(key), dict):
                         final_stats = final_json_data[key]
                         gen_stats = generated_data[key]
                         for stat_key, stat_value in gen_stats.items():
                             # Only update if it's not speed/color OR if the final doesn't have it
                             if stat_key not in ["speed", "color_theme", "color_theme_secondary"] or stat_key not in final_stats:
                                 final_stats[stat_key] = stat_value
                                 # print(f"    Merged stat: {stat_key}") # Verbose
                         core_merged_count +=1 # Count stats block as one merge
                     # For gameplay/lore_details, handle nested preservation
                     elif key == "gameplay" and isinstance(generated_data[key], dict) and isinstance(final_json_data.get(key), dict):
                         final_gameplay = final_json_data.setdefault(key, {}) # Ensure exists
                         gen_gameplay = generated_data[key]
                         for gameplay_key, gameplay_value in gen_gameplay.items():
                             nested_path = f"{key}.{gameplay_key}"
                             if nested_path not in PRESERVED_NESTED_FIELDS:
                                 final_gameplay[gameplay_key] = gameplay_value
                                 # print(f"    Merged gameplay field: {gameplay_key}") # Verbose
                         core_merged_count +=1 # Count gameplay block
                     elif key == "lore_details" and isinstance(generated_data[key], dict) and isinstance(final_json_data.get(key), dict):
                         final_lore = final_json_data.setdefault(key, {}) # Ensure exists
                         gen_lore = generated_data[key]
                         for lore_key, lore_value in gen_lore.items():
                             nested_path = f"{key}.{lore_key}"
                             if nested_path not in PRESERVED_NESTED_FIELDS:
                                 final_lore[lore_key] = lore_value
                                 # print(f"    Merged lore field: {lore_key}") # Verbose
                         core_merged_count +=1 # Count lore block
                     # Otherwise, directly copy/overwrite the top-level key
                     elif key != "name": # Avoid overwriting name again
                         final_json_data[key] = generated_data[key]
                         core_merged_count += 1
            print(f"  Merged {core_merged_count} core generated sections/fields.")


            # --- 8. Apply Patch Updates (to the 'final_json_data') ---
            print(f"  Attempting to apply balance patch updates for {original_casing_name}...")
            patch_applied = False
            patch_file_path = os.path.join(INFO_OUTPUT_DIR, "balance_post.txt")
            if os.path.exists(patch_file_path):
                try:
                    with open(patch_file_path, 'r', encoding='utf-8') as f_patch:
                        full_patch_text = f_patch.read()

                    # Use the proper-cased name for patch extraction
                    patch_section = extract_patch_section(original_casing_name, full_patch_text)

                    if patch_section:
                        # Convert final_json_data (potentially containing old preserved data) to string
                        base_json_str_for_prompt = json.dumps(final_json_data, indent=2)

                        patch_update_result = interpret_patch_via_api(
                            base_json_str_for_prompt, patch_section, original_casing_name, selected_model_name
                        )

                        if isinstance(patch_update_result, dict) and 'error' not in patch_update_result:
                            if patch_update_result:
                                print(f"  Patch AI provided updates. Merging into final data...")
                                # Merge patch updates INTO final_json_data
                                final_json_data = merge_updates(final_json_data, patch_update_result)
                                patch_applied = True
                                print(f"  Patch updates successfully merged into final data.")
                            else:
                                print(f"  Patch AI indicated no applicable changes for this character.")
                        elif isinstance(patch_update_result, dict) and 'error' in patch_update_result:
                             print(f"  WARN: Patch interpretation AI failed: {patch_update_result.get('error')} - Details: {patch_update_result.get('details', '')}. Proceeding without these patch changes.")
                        else:
                             print(f"  WARN: Patch interpretation returned unexpected data: {patch_update_result}. Proceeding without these patch changes.")
                    else:
                         print(f"  No relevant section found in balance_post.txt for {original_casing_name}.")
                except Exception as patch_e:
                     print(f"  ERROR reading or processing patch file {patch_file_path}: {patch_e}. Proceeding without patch changes.")
                     import traceback; traceback.print_exc(file=sys.stderr)
            else:
                 print(f"  WARN: Balance patch file not found at {patch_file_path}. Skipping patch application.")


            # --- 9. Inject Static Data & Reddit Link (into final_json_data) ---
            print(f"  Injecting static data (colors/speed/link) into final data...")
            sys.stdout.flush()
            # Colors
            color_pool = character_color_pools.get(original_casing_name, [])
            primary_color, secondary_color = None, None
            if color_pool and isinstance(color_pool, list):
                 try:
                     if len(color_pool) >= 2: primary_color, secondary_color = random.sample(color_pool, 2)
                     elif len(color_pool) == 1: primary_color = secondary_color = color_pool[0]
                 except ValueError: pass # Handle sample error if needed
            # Ensure 'stats' exists before setting
            final_json_data.setdefault('stats', {})
            if final_json_data['stats'] is None: final_json_data['stats'] = {} # Handle case where stats might be null
            final_json_data['stats']['color_theme'] = primary_color
            final_json_data['stats']['color_theme_secondary'] = secondary_color
            # Speed
            base_speed = CHARACTER_BASE_SPEEDS.get(original_casing_name)
            final_json_data['stats']['speed'] = base_speed
            # Ensure other sections exist before Reddit Link check
            final_json_data.setdefault("misc", {})
            if final_json_data['misc'] is None: final_json_data['misc'] = {}

            # Reddit Link
            try:
                 current_buzz = get_nested_value(final_json_data, "misc.community_buzz")
                 if current_buzz is None:
                     # Ensure we have a valid name from the final data
                     char_name_for_link = final_json_data.get("name", original_casing_name) # Use the final name

                     # URL encode the character name ONLY, adding quotes for exact match
                     encoded_char_name = urllib.parse.quote_plus(f'"{char_name_for_link}"')

                     # Construct the specific subreddit search URL with month filter
                     reddit_url = f"https://www.reddit.com/r/marvelrivals/search/?q={encoded_char_name}&type=posts&t=month"

                     set_nested_value(final_json_data, "misc.community_buzz", reddit_url)
                     print(f"    Generated Reddit search link for Community Buzz.")
            except Exception as reddit_link_e:
                 print(f"    WARN: Failed to generate Reddit link: {reddit_link_e}")

            # The "Static data injection complete" print comes AFTER this block
            print(f"  Static data injection complete.")


            # --- 10. Final Preservation Pass (Ensuring specific nested fields are kept from old) ---
            # This might be redundant if the merge logic in step 7 correctly skips preserved nested fields,
            # but acts as a safety net.
            if old_json_data:
                 print("  Final check/restore of specifically preserved nested fields...")
                 nested_preserved_count = 0
                 for field_path in PRESERVED_NESTED_FIELDS:
                     preserved_value = get_nested_value(old_json_data, field_path)
                     current_value = get_nested_value(final_json_data, field_path)
                     # Restore ONLY if the old value exists and is different from the current one
                     # (or if current is missing). Preserve None from old data too.
                     if preserved_value is not None and preserved_value != current_value:
                         if set_nested_value(final_json_data, field_path, preserved_value):
                              print(f"    Restored preserved nested field: '{field_path}'")
                              nested_preserved_count += 1
                         else:
                              print(f"    WARN: Failed to restore preserved nested field: '{field_path}'")
                 if nested_preserved_count > 0: print(f"  Restored {nested_preserved_count} specific nested field(s).")


            # --- 11. Save Final JSON ---
            os.makedirs(CHARACTER_JSON_OUTPUT_DIR, exist_ok=True)
            print(f"  Saving final processed JSON to: {os.path.basename(json_filepath)}")
            sys.stdout.flush()
            with open(json_filepath, 'w', encoding='utf-8') as f:
                json.dump(final_json_data, f, indent=2, ensure_ascii=False)

            print(f"  SUCCESS: Saved final JSON for {original_casing_name}.{' (Patch applied)' if patch_applied else ''}")
            success = True
            update_last_update_file("last_json_gen", datetime.datetime.now().isoformat())

        except FileNotFoundError:
            error_message_details = f"Raw Text file not found at:\n{raw_filepath}"
            print(f"  ERROR: {error_message_details}")
            success = False # Ensure success is false
        except Exception as e:
            # Capture error message from the exception
            error_msg_detail = f"ERROR during JSON generation pipeline for {selected_character}: {e}"
            print(error_msg_detail)
            if not error_message_details: error_message_details = str(e)
            # raw_response_on_error is already captured if it was a Base AI error
            import traceback; traceback.print_exc(file=sys.stderr)
            success = False # Ensure success is false


    # --- Update GUI (runs on main thread via root.after) ---
    def update_ui_after_single_gen():
        if root and root.winfo_exists():
            final_char_name_for_msg = original_casing_name if 'original_casing_name' in locals() else selected_character
            if success:
                success_msg = f"Status: Success: Generated '{os.path.basename(json_filepath)}' for {final_char_name_for_msg}"
                if status_var: status_var.set(success_msg)
                if 'tune_character_var' in globals() and tune_character_var.get() == final_char_name_for_msg:
                    load_current_json_for_tuning()
            else:
                if status_var: status_var.set(f"Status: Error generating JSON for {final_char_name_for_msg}.")
                error_display = f"Failed to generate/process JSON for {final_char_name_for_msg}.\n\n"
                if error_message_details: error_display += f"Details: {error_message_details}\n\n"
                error_file_path_check = os.path.join(CHARACTER_JSON_OUTPUT_DIR, "failed", f"{json_filename_base}.json.api_error.txt") # Check in failed dir

                # Save error file only if BASE AI failed and provided faulty output
                if raw_response_on_error and error_message_details and "Base AI Error" in error_message_details:
                    error_display += f"The BASE AI response likely had errors.\nCheck '{os.path.basename(error_file_path_check)}' (in failed subfolder) or logs."
                    error_dir = os.path.dirname(error_file_path_check)
                    try:
                         os.makedirs(error_dir, exist_ok=True) # Ensure 'failed' dir exists
                         if not os.path.exists(error_file_path_check): # Check before writing
                             with open(error_file_path_check, "w", encoding="utf-8") as err_f:
                                 err_f.write(f"-- BASE AI Generation Error [{selected_model_name}] --\n")
                                 err_f.write(f"Error: {error_message_details}\n")
                                 err_f.write(f"-- Faulty Extracted String/Raw Response --\n{raw_response_on_error}\n")
                             print(f"    DEBUG: Saved base AI error details to: {error_file_path_check}")
                         else:
                              print(f"    DEBUG: Base AI error file already exists: {error_file_path_check}")
                    except Exception as file_e:
                         print(f"    DEBUG: Failed saving base AI error file '{error_file_path_check}': {file_e}")
                else:
                    error_display += "Check console logs for details (e.g., file not found, schema issues, other errors)."
                messagebox.showerror("JSON Generation Error", error_display)

            enable_buttons()

    if root and root.winfo_exists():
        root.after(0, update_ui_after_single_gen)
    global json_gen_single_thread
    json_gen_single_thread = None # Clear the handle
# --- End Replacement ---



# --- Replace the existing generate_all_json_thread function ---
def generate_all_json_thread(character_names_list, selected_model_name):
    """Performs Raw -> JSON generation for a list of characters, preserving specified fields."""
    global TOP_LEVEL_SCHEMA_PROPERTIES, PRESERVED_SECTIONS_DURING_CORE_GEN, PRESERVED_NESTED_FIELDS

    total_files = len(character_names_list)
    
    print(f"\n=== Starting Generate ALL JSON ({total_files} files, Model: {selected_model_name}) ===")

    processed_count = 0
    success_count = 0
    error_count = 0
    start_time = time.time()
    os.makedirs(CHARACTER_JSON_OUTPUT_DIR, exist_ok=True)

    # --- Pre-load patch text once ---
    full_patch_text = None
    patch_file_path = os.path.join(INFO_OUTPUT_DIR, "balance_post.txt")
    if os.path.exists(patch_file_path):
        try:
            with open(patch_file_path, 'r', encoding='utf-8') as f_patch:
                full_patch_text = f_patch.read()
            print("  Successfully pre-loaded balance_post.txt for patch processing.")
        except Exception as pre_patch_e:
            print(f"  WARN: Failed to pre-load balance patch file {patch_file_path}: {pre_patch_e}. Patching will be skipped.")
    else:
        print(f"  WARN: Balance patch file not found at {patch_file_path}. Patching will be skipped.")

    # --- Safely update GUI progress ---
    def update_progress(current_index, total, char_name=""):
        if root and root.winfo_exists():
            try:
                progress_percent = int(((current_index + 1) / total) * 100) if total > 0 else 0
                if 'status_var' in globals() and status_var:
                     status_msg = f"Status: Generating All [{selected_model_name}] ({current_index+1}/{total}) {progress_percent}% - {char_name}"
                     root.after(0, lambda msg=status_msg: status_var.set(msg) if status_var else None)
                     global json_gen_all_thread
                     json_gen_all_thread = None # Clear the handle
            except Exception: pass
    # --- End safe update ---

    sorted_character_names = sorted(character_names_list) # Use names extracted from filenames

    for i, selected_character in enumerate(sorted_character_names): # Rename loop var
        update_progress(i, total_files, selected_character)
        print(f"\n--- Processing {i+1}/{total_files}: {selected_character} ---")
        sys.stdout.flush()

        # Initialize per-character variables
        current_success = False
        final_json_data = None
        raw_response_on_error = None
        error_message_details = None
        old_json_data = None
        original_casing_name = selected_character # Start with the filename version

        # Get file paths
        raw_filename_base = sanitize_filename(selected_character, extension="")
        if not raw_filename_base: print(f"  ERROR: Sanitize Fail (Raw) '{selected_character}'. Skipping."); error_count += 1; continue
        raw_filename = f"{raw_filename_base}_raw.txt"
        raw_filepath = os.path.join(RAW_TEXT_DIR, raw_filename)

        json_filename_base = sanitize_filename(selected_character, extension="")
        if not json_filename_base: print(f"  ERROR: Sanitize Fail (JSON) '{selected_character}'. Skipping."); error_count += 1; continue
        json_filename = f"{json_filename_base}.json"
        json_filepath = os.path.join(CHARACTER_JSON_OUTPUT_DIR, json_filename)

        # Check if raw file exists
        if not os.path.exists(raw_filepath):
            print(f"  SKIP: Raw text file not found: {os.path.basename(raw_filepath)}")
            continue

        processed_count += 1
        try:
            # --- 0. Load Existing JSON (for preservation) ---
            if os.path.exists(json_filepath):
                try:
                    with open(json_filepath, 'r', encoding='utf-8') as f_old:
                        old_json_data = json.load(f_old)
                    print(f"  Loaded existing JSON to preserve manual edits.")
                except Exception as load_err:
                    print(f"  WARN: Could not load existing JSON '{os.path.basename(json_filepath)}' for preservation: {load_err}. Will generate fresh.")
                    old_json_data = None

            # --- 1. Read and Clean Raw Text ---
            # (Same cleaning logic as single thread)
            with open(raw_filepath, 'r', encoding='utf-8') as f: raw_content = f.read().strip()
            raw_content = re.sub(r'^===== CONTENT FROM:.*?=====\s*', '', raw_content, flags=re.MULTILINE).strip()
            raw_content = re.sub(r'\n\n={20,}\s*CONTENT FROM:.*?={20,}\s*\n\n', '\n\n---\n\n', raw_content, flags=re.DOTALL)
            raw_content = re.sub(r'\s*\[\s*edit\s*\]\s*', '', raw_content, flags=re.IGNORECASE)
            raw_content = re.sub(r'^\s*See\s*also\s*:.*?\n', '', raw_content, flags=re.MULTILINE | re.IGNORECASE)
            raw_content = re.sub(r'\n{3,}', '\n\n', raw_content).strip()
            print(f"  Raw text read and cleaned.")

            # --- 2. Call Base AI ---
            print(f"  Calling Base AI [{selected_model_name}]...")
            sys.stdout.flush()
            base_ai_result = generate_json_from_raw_via_api(
                raw_content, selected_character, selected_model_name
            )

            # --- 3. Process Base AI Result ---
            if not isinstance(base_ai_result, dict):
                 error_message_details = "Base AI function returned unexpected data type."
                 raw_response_on_error = str(base_ai_result)
                 raise TypeError(error_message_details)

            if 'error' in base_ai_result:
                error_detail = base_ai_result.get('error', 'Unknown Base AI Error')
                details = base_ai_result.get('details', '')
                raw_response_on_error = base_ai_result.get('raw_response')
                error_message_details = f"Base AI Error: {error_detail}. Details: {details}"
                raise Exception(f"Base AI Error: {error_detail}")

            generated_data = base_ai_result
            print(f"  Base AI returned parsable JSON data.")

            # --- 4. Enforce Schema Keys on Generated Data ---
            print("  Ensuring generated data adheres to schema keys...")
            sys.stdout.flush()
            if TOP_LEVEL_SCHEMA_PROPERTIES:
                generated_data = ensure_schema_keys(generated_data, TOP_LEVEL_SCHEMA_PROPERTIES)
                print("  Generated data schema key enforcement complete.")
            else:
                 print("  WARN: Simplified schema structure not available, skipping key enforcement on generated data.")

            


            # --- 5. Initialize Final Data ---
            if old_json_data:
                import copy; final_json_data = copy.deepcopy(old_json_data)
                print("  Initialized final data from existing JSON.")
            else:
                final_json_data = generated_data
                print("  Initialized final data from newly generated JSON (no existing file).")

            # --- 6. Apply Name Correction ---
            proper_char_name_from_gen = generated_data.get("name", selected_character)
            original_casing_name = proper_char_name_from_gen # Keep case from AI by default now
            # Apply specific Proper Casing rules IF AI used ALL CAPS
            if proper_char_name_from_gen == "HULK": original_casing_name = "Hulk"
            elif proper_char_name_from_gen == "GROOT": original_casing_name = "Groot"
            elif proper_char_name_from_gen == "CLOAK & DAGGER": original_casing_name = "Cloak & Dagger"
            elif proper_char_name_from_gen == "PUNISHER": original_casing_name = "Punisher"
            elif proper_char_name_from_gen == "MISTER FANTASTIC": original_casing_name = "Mister Fantastic"
            # Add others as needed

            final_json_data["name"] = original_casing_name # Set the proper case name
            print(f"  Ensured final character name is: '{original_casing_name}'")


            # --- 7. Merge CORE Generated Data into Final Data ---
            print(f"  Merging core generated fields into final data...")
            core_merged_count = 0
            for key in CORE_GENERATED_KEYS:
                if key in generated_data:
                     # (Selective merge logic identical to single thread version)
                     if key == "stats" and isinstance(generated_data[key], dict) and isinstance(final_json_data.get(key), dict):
                         final_stats = final_json_data[key]
                         gen_stats = generated_data[key]
                         for stat_key, stat_value in gen_stats.items():
                             if stat_key not in ["speed", "color_theme", "color_theme_secondary"] or stat_key not in final_stats:
                                 final_stats[stat_key] = stat_value
                         core_merged_count +=1
                     elif key == "gameplay" and isinstance(generated_data[key], dict) and isinstance(final_json_data.get(key), dict):
                         final_gameplay = final_json_data.setdefault(key, {})
                         gen_gameplay = generated_data[key]
                         for gameplay_key, gameplay_value in gen_gameplay.items():
                             nested_path = f"{key}.{gameplay_key}"
                             if nested_path not in PRESERVED_NESTED_FIELDS: final_gameplay[gameplay_key] = gameplay_value
                         core_merged_count +=1
                     elif key == "lore_details" and isinstance(generated_data[key], dict) and isinstance(final_json_data.get(key), dict):
                         final_lore = final_json_data.setdefault(key, {})
                         gen_lore = generated_data[key]
                         for lore_key, lore_value in gen_lore.items():
                             nested_path = f"{key}.{lore_key}"
                             if nested_path not in PRESERVED_NESTED_FIELDS: final_lore[lore_key] = lore_value
                         core_merged_count +=1
                     elif key != "name": # Avoid name overwrite
                         final_json_data[key] = generated_data[key]
                         core_merged_count += 1
            print(f"  Merged {core_merged_count} core generated sections/fields.")


            # --- 8. Apply Patch Updates (to 'final_json_data') ---
            patch_applied = False
            if full_patch_text: # Check if patch text loaded at start
                print(f"  Attempting to apply balance patch updates for {original_casing_name}...")
                try:
                    # Use proper-cased name for extraction
                    patch_section = extract_patch_section(original_casing_name, full_patch_text)
                    if patch_section:
                        base_json_str_for_prompt = json.dumps(final_json_data, indent=2)
                        patch_update_result = interpret_patch_via_api(
                            base_json_str_for_prompt, patch_section, original_casing_name, selected_model_name
                        )
                        if isinstance(patch_update_result, dict) and 'error' not in patch_update_result:
                            if patch_update_result:
                                print(f"  Patch AI provided updates. Merging into final data...")
                                final_json_data = merge_updates(final_json_data, patch_update_result)
                                patch_applied = True
                                print(f"  Patch updates successfully merged into final data.")
                            else: print(f"  Patch AI indicated no applicable changes.")
                        elif isinstance(patch_update_result, dict) and 'error' in patch_update_result:
                             print(f"  WARN: Patch interpretation AI failed for {original_casing_name}: {patch_update_result.get('error')} - Details: {patch_update_result.get('details', '')}.")
                        else: print(f"  WARN: Patch interpretation returned unexpected data for {original_casing_name}: {patch_update_result}.")
                    else: print(f"  No relevant section found in balance_post.txt for {original_casing_name}.")
                except Exception as patch_loop_e: print(f"  ERROR during patch application step for {original_casing_name}: {patch_loop_e}.")
            else: print("  Skipping patch application (patch file was not loaded).")


            # --- 9. Inject Static Data & Reddit Link (into final_json_data) ---
            print(f"  Injecting static data (colors/speed/link) into final data...")
            sys.stdout.flush()
            # Colors
            color_pool = character_color_pools.get(original_casing_name, [])
            p_color, s_color = None, None
            if color_pool and isinstance(color_pool, list):
                 try:
                     if len(color_pool) >= 2: p_color, s_color = random.sample(color_pool, 2)
                     elif len(color_pool) == 1: p_color = s_color = color_pool[0]
                 except ValueError: pass
            final_json_data.setdefault('stats', {})
            if final_json_data['stats'] is None: final_json_data['stats'] = {}
            final_json_data['stats']['color_theme'] = p_color
            final_json_data['stats']['color_theme_secondary'] = s_color
            # Speed
            base_speed = CHARACTER_BASE_SPEEDS.get(original_casing_name)
            final_json_data['stats']['speed'] = base_speed
            # Ensure misc exists
            final_json_data.setdefault("misc", {})
            if final_json_data['misc'] is None: final_json_data['misc'] = {}
            # --- Generate Reddit Community Buzz Link (if null) --- <<< ENSURE THIS BLOCK IS PRESENT
            try:
                 # Use the name from the final data structure
                 current_buzz = get_nested_value(final_json_data, "misc.community_buzz")

                 # Only set if currently None (don't overwrite manual entry)
                 if current_buzz is None:
                     char_name_for_link = final_json_data.get("name", original_casing_name) # Use the final name

                     # URL encode the character name ONLY, adding quotes for exact match
                     encoded_char_name = urllib.parse.quote_plus(f'"{char_name_for_link}"')

                     # Construct the specific subreddit search URL with month filter
                     reddit_url = f"https://www.reddit.com/r/marvelrivals/search/?q={encoded_char_name}&type=posts&t=month"

                     set_nested_value(final_json_data, "misc.community_buzz", reddit_url)
                     print(f"    Generated Reddit search link for Community Buzz.")

            except Exception as reddit_link_e:
                 print(f"    WARN: Failed to generate Reddit link: {reddit_link_e}")
            # --- End Reddit Link Block ---
            
            # --- 10. Final Preservation Pass (Specific Nested Fields) ---
            if old_json_data:
                 print("  Final check/restore of specifically preserved nested fields...")
                 nested_preserved_count = 0
                 for field_path in PRESERVED_NESTED_FIELDS:
                     preserved_value = get_nested_value(old_json_data, field_path)
                     current_value = get_nested_value(final_json_data, field_path)
                     if preserved_value is not None and preserved_value != current_value:
                         if set_nested_value(final_json_data, field_path, preserved_value):
                              # print(f"    Restored preserved nested field: '{field_path}'") # Verbose
                              nested_preserved_count += 1
                         else: print(f"    WARN: Failed to restore preserved nested field: '{field_path}'")
                 if nested_preserved_count > 0: print(f"  Restored {nested_preserved_count} specific nested field(s).")


            # --- 11. Save Final JSON ---
            print(f"  Saving JSON: {os.path.basename(json_filepath)}")
            sys.stdout.flush()
            global scrape_all_thread
            scrape_all_thread = None # Clear the handle
            with open(json_filepath, 'w', encoding='utf-8') as f:
                json.dump(final_json_data, f, indent=2, ensure_ascii=False)
            print(f"  SUCCESS: Saved {os.path.basename(json_filepath)}{' (Patch applied)' if patch_applied else ''}")
            success_count += 1
            current_success = True

        except Exception as e:
            # General error during this character's processing
            print(f"  ERROR processing {selected_character}: {e}")
            error_count += 1 # Count as error for this char
            import traceback; traceback.print_exc(file=sys.stderr)
            # Save error file only if BASE AI failed and we have the faulty response
            if raw_response_on_error:
                 error_file_path = os.path.join(CHARACTER_JSON_OUTPUT_DIR, "failed", f"{json_filename_base}.json.api_error.txt")
                 error_dir = os.path.dirname(error_file_path)
                 try:
                     os.makedirs(error_dir, exist_ok=True)
                     if not os.path.exists(error_file_path): # Check before writing
                         with open(error_file_path, "w", encoding="utf-8") as err_f:
                              err_f.write(f"-- BASE AI Generation Error [{selected_model_name}] --\nError: {error_message_details or e}\n-- Faulty AI Output --\n{raw_response_on_error}")
                         print(f"    Saved base AI error details to: {os.path.basename(error_file_path)}")
                     else: print(f"    DEBUG: Base AI error file already exists: {os.path.basename(error_file_path)}")
                 except Exception as file_e: print(f"    WARN: Failed saving base AI error file: {file_e}")


        # --- API Call Delay ---
        if i < total_files - 1:
             print(f"  --- Delaying {API_CALL_DELAY_SECONDS}s before next character ---")
             time.sleep(API_CALL_DELAY_SECONDS)

    # --- Finalize Process ---
    end_time = time.time()
    duration = str(datetime.timedelta(seconds=int(end_time - start_time)))
    final_message = f"Status: Generate ALL COMPLETE! Processed: {processed_count}/{total_files}. Success: {success_count}, Errors: {error_count}. Duration: {duration}."
    if success_count > 0:
        print(f"  Updating last_update.json for Generate All completion...")
        update_last_update_file("last_json_gen", datetime.datetime.now().isoformat())
    print(f"\n=== {final_message} ===")
    sys.stdout.flush()

    # --- Safely Update GUI on Completion ---
    def finalize_all_json_ui():
        if root and root.winfo_exists():
            if status_var: status_var.set(final_message)
            summary_title = "Generate All Complete"
            summary_message = f"'Generate All' finished.\n\nProcessed: {processed_count}/{total_files}\nSuccess (Saved Files): {success_count}\nErrors (Failed Base Gen): {error_count}\n\nCheck logs for details on patch application and errors."
            if error_count > 0: messagebox.showwarning(summary_title, summary_message)
            else: messagebox.showinfo(summary_title, summary_message)
            enable_buttons()
            # Reload character list and update dropdowns AFTER finishing all generations
            load_character_list_from_files()
            update_all_character_dropdowns()

    if root and root.winfo_exists(): root.after(0, finalize_all_json_ui)
    # --- End safe update ---

# --- End Replacement ---
# ==============================================================================
# == META STATS SCRAPING & UPDATING FUNCTIONS ==  ### NEW SECTION MARKER ###
# ==============================================================================

def scrape_all_tracker_data(tracker_url="https://rivalstracker.com/heroes"):
    """
    Scrapes the entire hero table from RivalsTracker and returns a dictionary
    mapping hero names (as on tracker) to their stats dictionaries.
    Returns None on failure.
    """
    print(f"Scraping ALL hero stats from: {tracker_url}")
    headers = {'User-Agent': USER_AGENT}
    scraped_data = {}

    try:
        response = requests.get(tracker_url, headers=headers, timeout=20) # Increased timeout slightly
        response.raise_for_status()
        print("  Tracker page fetched successfully.")
    except requests.exceptions.Timeout:
        print(f"  ERROR (Tracker): Request timed out for {tracker_url}")
        messagebox.showerror("Tracker Error", f"Request timed out accessing:\n{tracker_url}")
        return None
    except requests.exceptions.RequestException as e:
        print(f"  ERROR (Tracker): Request failed: {e}")
        messagebox.showerror("Tracker Error", f"Failed to access tracker site:\n{e}")
        return None

    print("  Parsing tracker page...")
    try:
        soup = BeautifulSoup(response.text, 'html.parser')
        table_body = soup.select_one('table tbody') # Prioritize tbody selector
        if not table_body:
            table = soup.find('table') # Fallback to table
            if table:
                 print("    WARN (Tracker): Could not find tbody, attempting direct rows from table.")
                 rows = table.find_all('tr')
                 # Often the first row in a table without tbody is the header, skip it
                 if rows and rows[0].find('th'): # Check if first row has header cells
                     rows = rows[1:]
            else:
                 print("    ERROR (Tracker): Could not find table element.")
                 messagebox.showerror("Tracker Error", "Could not find the stats table on the tracker page.")
                 return None
        else:
             rows = table_body.find_all('tr')

        if not rows:
            print("    ERROR (Tracker): Found table structure but no data rows (tr).")
            messagebox.showerror("Tracker Error", "Found table structure but no hero data rows.")
            return None

        print(f"  Found {len(rows)} rows in table. Processing...")
        expected_cells = 8 # Name, Tier, WR, WR+/-, PR, PR+/-, BR, Matches
        processed_count = 0

        for row in rows:
            cells = row.find_all('td')
            if len(cells) < expected_cells:
                # print(f"    WARN (Tracker): Skipping row with {len(cells)} cells (expected {expected_cells}).") # Less verbose
                continue

            # Extract Name (Try link, then first cell's text more robustly)
            hero_name_tracker = None
            name_cell = cells[0] # Get the first cell
            if name_cell:
                # Improved: Check for nested divs/spans common in frameworks
                name_container = name_cell.select_one('a, div, span') # Look for link or common containers
                if name_container:
                     hero_name_tracker = name_container.text.strip()
                else: # Fallback to direct cell text
                     hero_name_tracker = name_cell.text.strip()


            if not hero_name_tracker:
                # print("    WARN (Tracker): Skipping row with missing hero name.") # Less verbose
                continue

            # Extract Stats
            try:
                stats = {
                    # Use .get_text(strip=True) for potentially complex cell contents
                    "tier": cells[1].get_text(strip=True) or None,
                    "win_rate": cells[2].get_text(strip=True) or None,
                    "wr_change": cells[3].get_text(strip=True) or None,
                    "pick_rate": cells[4].get_text(strip=True) or None,
                    "pr_change": cells[5].get_text(strip=True) or None,
                    "ban_rate": cells[6].get_text(strip=True) or None,
                    "matches": cells[7].get_text(strip=True) or None,
                }
                # Basic validation: Ensure at least 'tier' has a value maybe? Or accept all.
                # For now, accept even if some stats are empty strings (they become None above)
                scraped_data[hero_name_tracker] = stats # Store using name from tracker site
                processed_count += 1
            except Exception as cell_e:
                 print(f"    WARN (Tracker): Error parsing cells for row likely containing '{hero_name_tracker}': {cell_e}")

        print(f"  Successfully scraped stats for {processed_count} heroes.")
        if not scraped_data:
             print("  ERROR (Tracker): Failed to extract any valid hero stats.")
             messagebox.showerror("Tracker Error", "Failed to extract any hero stats from the table.")
             return None
        return scraped_data

    except Exception as e:
        print(f"  ERROR (Tracker): Parsing failed unexpectedly: {e}")
        import traceback
        traceback.print_exc(file=sys.stderr)
        messagebox.showerror("Tracker Error", f"An unexpected error occurred during parsing:\n{e}")
        return None


def update_all_json_with_tracker_data(scraped_tracker_data):
    """
    Iterates through JSON files, loads them, matches names (case-insensitive,
    handling common variations) with scraped data, updates meta_stats,
    and saves back. Returns counts: (processed, updated, errors).
    """
    print("\n--- Updating JSON files with scraped Tracker data ---")
    if not scraped_tracker_data:
        print("  Skipping update: No tracker data provided.")
        return 0, 0, 0 # processed, updated, errors

    files_processed = 0
    files_updated = 0
    update_errors = 0
    files_in_dir = []
    try:
        files_in_dir = [f for f in os.listdir(CHARACTER_JSON_OUTPUT_DIR)
                        if f.lower().endswith('.json') and os.path.isfile(os.path.join(CHARACTER_JSON_OUTPUT_DIR, f))]
    except OSError as e:
        print(f"  ERROR: Cannot list files in {CHARACTER_JSON_OUTPUT_DIR}: {e}")
        messagebox.showerror("File Error", f"Cannot read character directory:\n{CHARACTER_JSON_OUTPUT_DIR}\n{e}")
        return 0, 0, 1 # Treat as one error

    total_files = len(files_in_dir)
    print(f"  Found {total_files} JSON files to check.")

    # Create a lower-case mapping of tracker names for easier lookup
    tracker_names_lower = {name.lower(): name for name in scraped_tracker_data.keys()}

    for i, filename in enumerate(files_in_dir):
        filepath = os.path.join(CHARACTER_JSON_OUTPUT_DIR, filename)
        # --- GUI Progress Update within loop ---
        # Use root.after to schedule GUI updates on the main thread safely
        if root and root.winfo_exists():
            try:
                 progress_percent = int(((i + 1) / total_files) * 100) if total_files > 0 else 0
                 status_msg = f"Status: Updating Meta Stats... ({i+1}/{total_files}) {progress_percent}% - {filename}"
                 # Pass the message explicitly to the lambda
                 root.after(0, lambda msg=status_msg: status_var.set(msg) if status_var else None)
            except Exception as gui_e:
                 # print(f"Debug: GUI update error {gui_e}") # Optional
                 pass # Ignore GUI update errors
        # --- End GUI Update ---

        files_processed += 1
        try:
            # Read the JSON file
            with open(filepath, 'r', encoding='utf-8') as f:
                char_data = json.load(f)

            json_char_name = char_data.get("name")
            if not json_char_name:
                print(f"    WARN: Skipping '{filename}': Missing 'name' field in JSON.")
                update_errors += 1
                continue

            # --- Name Matching Logic (Handle variations) ---
            matched_tracker_name = None
            # Use the name from JSON, which might have '&' or proper casing
            local_name_lower = json_char_name.lower()

            # Direct match (lowercase) - Primary check
            if local_name_lower in tracker_names_lower:
                matched_tracker_name = tracker_names_lower[local_name_lower]
            else:
                # Check common variations against the tracker's lowercase names
                variations_to_check = []
                # Convert local name potential variations to lowercase for checking
                if ' ' in local_name_lower: variations_to_check.append(local_name_lower.replace(' ', '-'))
                if '-' in local_name_lower: variations_to_check.append(local_name_lower.replace('-', ' '))
                if '&' in local_name_lower: variations_to_check.append(local_name_lower.replace('&', 'and')) # check tracker's 'and' version
                if ' and ' in local_name_lower: variations_to_check.append(local_name_lower.replace(' and ', '&')) # check tracker's '&' version
                # Explicit checks based on known differences
                if local_name_lower == 'spider-man': variations_to_check.append('spider man')
                elif local_name_lower == 'spider man': variations_to_check.append('spider-man')
                elif local_name_lower == 'the punisher': variations_to_check.append('punisher')
                elif local_name_lower == 'punisher': variations_to_check.append('the punisher')
                # Add more specific cases if needed

                for variation_lower in variations_to_check:
                     if variation_lower in tracker_names_lower:
                         matched_tracker_name = tracker_names_lower[variation_lower]
                         print(f"    Matched '{json_char_name}' to tracker name '{matched_tracker_name}' via variation '{variation_lower}'.")
                         break # Found match

            # --- Update if Match Found ---
            if matched_tracker_name:
                tracker_stats = scraped_tracker_data.get(matched_tracker_name)
                if tracker_stats:
                    # Ensure meta_stats key exists, creating if necessary
                    char_data.setdefault("meta_stats", {})
                    # Overwrite meta_stats with the newly scraped data
                    if not isinstance(char_data["meta_stats"], dict):
                        print(f"    WARN: meta_stats for '{json_char_name}' was not a dictionary. Resetting and updating.")
                        char_data["meta_stats"] = {} # Reset to empty dict if invalid type

                    updated_count = 0
                    for key, value in tracker_stats.items():
                        # Check if the key exists in the schema's meta_stats
                        # Or just update blindly if the keys match exactly
                        if key in char_data["meta_stats"]: # Update only if key exists in our schema
                            char_data["meta_stats"][key] = value
                            updated_count +=1
                        else: # Optionally log unexpected keys from tracker
                           print(f"    INFO: Key '{key}' from tracker not in schema's meta_stats for {filename}")

                    # Save the updated file only if stats were actually updated
                    if updated_count > 0:
                        try:
                            with open(filepath, 'w', encoding='utf-8') as f_out:
                                json.dump(char_data, f_out, indent=2, ensure_ascii=False)
                            # print(f"    SUCCESS: Updated {updated_count} meta_stats for '{json_char_name}' in '{filename}'.") # Verbose
                            files_updated += 1
                        except Exception as save_e:
                            print(f"    ERROR: Failed to save updated file '{filename}': {save_e}")
                            update_errors += 1
                    else:
                         print(f"    INFO: No schema-matching stats found in scraped data for '{matched_tracker_name}'. File '{filename}' not modified.")

                else:
                    print(f"    WARN: Matched name '{matched_tracker_name}' but no stats object found in scraped data for '{filename}'.")
            else:
                print(f"    INFO: No matching tracker stats found for '{json_char_name}' ('{filename}').")

        except json.JSONDecodeError as json_e:
            print(f"    ERROR: Invalid JSON in file '{filename}': {json_e}. Skipping.")
            update_errors += 1
        except Exception as load_e:
            print(f"    ERROR: Failed to load or process file '{filename}': {load_e}")
            update_errors += 1

    print(f"--- Finished updating JSON files. Processed: {files_processed}, Updated: {files_updated}, Errors: {update_errors} ---")
    return files_processed, files_updated, update_errors

# --- Add this near the other thread functions ---
update_meta_stats_thread_handle = None # Global handle for the thread

def update_all_meta_stats_thread():
    global update_meta_stats_thread_handle
    start_time = time.time()
    if status_var: status_var.set("Status: Starting Meta Stats update...")

    scraped_data = None # Initialize
    files_processed, files_updated, update_errors = 0, 0, 0

    try: # Main processing block
        # Step 1: Scrape all data from tracker
        scraped_data = scrape_all_tracker_data() # Assign result

        if scraped_data:
            # Step 2: Update JSON files if scraping succeeded
            files_processed, files_updated, update_errors = update_all_json_with_tracker_data(scraped_data)
        else:
            # Scraping failed logic...
            print("  Meta stats update aborted because tracker scraping failed.")
            update_errors = 1

    except Exception as e: # Catch errors during scraping/updating
        print(f"ERROR during meta stats processing: {e}")
        import traceback
        traceback.print_exc(file=sys.stderr)
        update_errors = 1 # Assume error if exception occurs
        # Ensure counts are reasonable defaults on error
        files_processed = files_processed or 0
        files_updated = files_updated or 0

    # --- DEFINE finalize_ui HERE (Outside the try...except) ---
    def finalize_ui():
        if root and root.winfo_exists():
            if status_var: status_var.set(final_message) # Use final_message calculated below
            # Show summary message box
            summary_title = "Meta Stats Update Complete"
            summary_message = f"Meta Stats update finished.\n\n"
            if update_errors > 0 and scraped_data is None: # Check if scraping specifically failed
                 summary_message += "Tracker scraping failed. No files updated.\n"
            else:
                summary_message += f"Files Checked: {files_processed}\nFiles Updated: {files_updated}\nErrors: {update_errors}\n\n" # Use calculated counts
            summary_message += "Check logs for details."

            if update_errors > 0: messagebox.showwarning(summary_title, summary_message)
            else: messagebox.showinfo(summary_title, summary_message)
            enable_buttons() # Re-enable buttons
    # --- End finalize_ui definition ---

    # --- Calculate final message AFTER try...except ---
    end_time = time.time()
    duration = str(datetime.timedelta(seconds=int(end_time - start_time)))
    # Use the counts determined within the try...except block
    final_message = f"Status: Meta Stats update COMPLETE. Files Checked: {files_processed}. Files Updated: {files_updated}. Errors: {update_errors}. Duration: {duration}."

    # --- Update last_update.json if scraping/update was attempted ---
    if scraped_data is not None: # Check if scraping attempt succeeded
         print(f"  Updating last_update.json for Meta Stats completion...")
         update_last_update_file("last_meta_update", datetime.datetime.now().isoformat()) # Correct datetime call

    print(f"\n=== {final_message} ===") # Print final status

    # --- Schedule the UI update (finalize_ui is now defined) ---
    if root and root.winfo_exists():
        root.after(0, finalize_ui) # Call the function defined above

    # --- Clear the thread handle ---
    update_meta_stats_thread_handle = None
# --- End of update_all_meta_stats_thread function ---

def start_generate_all_json_thread():
    """Validates input and starts the background thread for generating all JSON files."""
    global json_gen_all_thread

    # Check if essential widgets exist
    if not all(['model_selection_var' in globals() and model_selection_var]):
        print("Error: JSON generation widgets not ready.")
        return

    selected_model = model_selection_var.get()

    # Validation
    if not selected_model or selected_model not in AVAILABLE_MODELS:
        messagebox.showerror("Error", "Please select a valid API model."); return
    if not GOOGLE_AI_AVAILABLE:
        messagebox.showerror("Error", "Google AI library is required for JSON generation."); return
    if not google_api_key:
        messagebox.showerror("API Key Error", "Google API Key is missing or invalid. Check .env file or environment variables."); return

    # Find characters with existing raw text files
    raw_files_found = []
    characters_to_process = []
    if os.path.isdir(RAW_TEXT_DIR):
        try:
            for f in os.listdir(RAW_TEXT_DIR):
                filepath = os.path.join(RAW_TEXT_DIR, f)
                # Ensure it's a file and ends with _raw.txt
                if os.path.isfile(filepath) and f.lower().endswith("_raw.txt"):
                    # Extract character name (part before _raw.txt)
                    char_name_match = re.match(r'^(.*?)_raw\.txt$', f, re.IGNORECASE)
                    if char_name_match:
                        char_name = char_name_match.group(1)
                        # Add the name extracted from the filename
                        characters_to_process.append(char_name)
                        raw_files_found.append(f)
                    else:
                        print(f"WARN: File '{f}' ends with _raw.txt but couldn't extract character name.")
        except OSError as e:
            messagebox.showerror("Input Directory Error", f"Cannot read Raw Text directory:\n'{RAW_TEXT_DIR}'\n{e}")
            return
    else:
        messagebox.showerror("Input Directory Missing", f"Raw text directory not found:\n'{RAW_TEXT_DIR}'.\n\nRun the scraper first (Tab 1).")
        return

    if not characters_to_process:
        messagebox.showinfo("No Files Found", f"No raw text files (_raw.txt) found in:\n'{RAW_TEXT_DIR}'.\n\nRun the scraper first (Tab 1).")
        return

    num_files = len(characters_to_process)
    confirm_msg = (
        f"This will attempt to generate/update JSON for {num_files} character(s) with existing raw text files.\n\n"
        f"Process includes:\n"
        f"1. Generating base JSON from wiki text via AI.\n"
        f"2. Applying latest balance patch updates via AI.\n"
        f"3. Injecting static data (colors, speed).\n\n"
        f"Model: {selected_model}\n"
        f"Output Directory: '{CHARACTER_JSON_OUTPUT_DIR}'\n\n"
        f"This process uses the AI API and involves a delay ({API_CALL_DELAY_SECONDS}s) between each character.\n"
        f"Significant time and potentially API costs may be involved.\n\n"
        f"Do you want to proceed?"
    )
    if not messagebox.askyesno("Confirm Generate All JSON", confirm_msg):
        return

    # Prevent starting if already running
    if json_gen_all_thread and json_gen_all_thread.is_alive():
        print("INFO: 'Generate All JSON' process is already running.")
        messagebox.showinfo("Busy", "The 'Generate All JSON' process is already running.")
        return

    # Start the process
    if status_var: status_var.set(f"Status: Starting Generate All JSON ({num_files} files, {selected_model})...")
    disable_buttons()

    # Start the thread
    json_gen_all_thread = threading.Thread(
        target=generate_all_json_thread, # Target the actual processing function (which now includes patch logic)
        args=(characters_to_process, selected_model),
        daemon=True
    )
    json_gen_all_thread.start()


# --- Add this near the other button trigger functions ---
def start_update_all_meta_stats():
    """Handles the 'Update Meta Stats' button click."""
    global update_meta_stats_thread_handle

    # Prevent starting if already running
    if update_meta_stats_thread_handle and update_meta_stats_thread_handle.is_alive():
        print("INFO: Meta Stats update process is already running.")
        messagebox.showinfo("Busy", "The Meta Stats update process is already running.")
        return

    confirm_msg = (
        "This will attempt to:\n"
        "1. Scrape the latest stats from rivalstracker.com/heroes.\n"
        "2. Update the 'meta_stats' section in ALL existing character JSON files.\n\n"
        "This will overwrite any existing meta_stats data. Proceed?"
    )
    if not messagebox.askyesno("Confirm Update All Meta Stats", confirm_msg):
        return

    # Start the process
    if status_var: status_var.set("Status: Starting Meta Stats update...")
    disable_buttons()

    # Start the thread
    update_meta_stats_thread_handle = threading.Thread(target=update_all_meta_stats_thread, daemon=True)
    update_meta_stats_thread_handle.start()





# --- Fine-Tuning Functions ---
def preview_ai_tuning():
    """Starts the background thread for AI-based JSON tuning."""
    global json_tune_thread

    # Check if essential widgets exist
    if not all(['tune_character_var' in globals() and tune_character_var,
                'tuning_instruction_input' in globals() and tuning_instruction_input,
                'tune_model_var' in globals() and tune_model_var]):
        print("Error: Tuning widgets not ready.")
        return

    selected_char = tune_character_var.get()
    instruction = tuning_instruction_input.get("1.0", END).strip()
    tune_model = tune_model_var.get()

    # Validation
    if not selected_char or selected_char == "(No Characters Found)":
        messagebox.showerror("Error", "Please select a character and load their JSON first."); return
    if not instruction:
        messagebox.showerror("Error", "Please enter a tuning instruction in the text box."); return
    if not tune_model or tune_model not in AVAILABLE_MODELS:
        messagebox.showerror("Error", "Please select a valid AI model for tuning."); return
    if not original_loaded_json_str: # Check if JSON was actually loaded
        messagebox.showerror("Error", "No current JSON data loaded. Please load the character's JSON first."); return
    if not GOOGLE_AI_AVAILABLE:
         messagebox.showerror("Error", "Google AI library is required for tuning."); return
    if not google_api_key:
         messagebox.showerror("API Key Error", "Google API Key is missing or invalid."); return

    # Check for raw text file (optional but helpful for context)
    raw_filename_base = sanitize_filename(selected_char, extension="")
    if not raw_filename_base: messagebox.showerror("Error", f"Could not sanitize filename base for '{selected_char}'."); return
    raw_filename = f"{raw_filename_base}_raw.txt"
    raw_filepath = os.path.join(RAW_TEXT_DIR, raw_filename)
    raw_content = "Source raw text not available." # Default if file missing

    if not os.path.exists(raw_filepath):
        messagebox.showwarning("Raw Text Missing", f"Raw Text file not found:\n{raw_filepath}\n\nAI tuning may be less accurate without the original source text for context.")
    else:
        try:
            with open(raw_filepath, 'r', encoding='utf-8') as f:
                raw_content = f.read()
            print("  Included source raw text for tuning context.")
        except Exception as e:
            messagebox.showerror("Error Reading Raw Text", f"Failed to read raw text file:\n{raw_filepath}\n{e}\n\nProceeding without raw text context.")
            # Proceed without raw_content, it's already defaulted

    # Prevent starting if already running
    if json_tune_thread and json_tune_thread.is_alive():
        print("INFO: Tuning process is already running.")
        messagebox.showinfo("Busy", "An AI tuning process is already running.")
        return

    # Start the process
    print(f"\n--- Starting AI Fine-Tuning Preview for {selected_char} ({tune_model}) ---")
    if tune_status_var: tune_status_var.set("Status: Sending tuning request to AI...")
    disable_buttons() # Disable buttons across all tabs
    disable_tuning_buttons(keep_load=False) # Disable tuning buttons too

    # Start the thread
    json_tune_thread = threading.Thread(
        target=tune_json_thread,
        args=(selected_char, original_loaded_json_str, raw_content, instruction, tune_model),
        daemon=True
    )
    json_tune_thread.start()


# --- Replace the existing function with this ---
def tune_json_thread(character_name, current_json_str, raw_source_text, user_instruction, tune_model_name):
    """Background thread to call AI for JSON tuning, extracting response and enforcing schema."""
    global proposed_tuned_json_data, TOP_LEVEL_SCHEMA_PROPERTIES # Use global schema structure

    local_proposed_data = None
    ai_result_raw_text = "" # Store raw text from AI
    error_msg = None
    response = None
    extracted_json_string = None # Store extracted string

    try:
        # --- Load Tuning Prompt Template (unchanged) ---
        tuning_prompt_template = None
        tuning_prompt_filepath = API_PROMPT_TUNING_FILE
        if os.path.exists(tuning_prompt_filepath):
            with open(tuning_prompt_filepath, 'r', encoding='utf-8') as f: tuning_prompt_template = f.read()
        if not tuning_prompt_template or not tuning_prompt_template.strip(): raise ValueError(f"Tuning prompt file empty/missing: {tuning_prompt_filepath}")

        # --- Validate and Format Tuning Prompt (unchanged) ---
        print("  Validating and Formatting Tuning Prompt...")
        required_placeholders = ["{json_schema_target}", "{raw_source_text}", "{current_json_str}", "{user_instruction}"]
        for ph in required_placeholders:
             if ph not in tuning_prompt_template: raise ValueError(f"Tuning prompt template missing placeholder: {ph}")
        final_tuning_prompt = tuning_prompt_template.format(json_schema_target=FINAL_JSON_SCHEMA_STRING, raw_source_text=raw_source_text, current_json_str=current_json_str, user_instruction=user_instruction)
        print(f"  Tuning prompt formatted successfully.")

        # --- Call Tuning AI (Requesting TEXT) ---
        print(f"  Calling tuning AI model: {tune_model_name} (expecting text)...")
        genai.configure(api_key=google_api_key)
        generation_config = { "temperature": 0.2, "max_output_tokens": 8192 }
        model = genai.GenerativeModel(model_name=tune_model_name, generation_config=generation_config)
        response = model.generate_content(final_tuning_prompt, request_options={"timeout": 180})

        # --- Process Tuning Response ---
        print("  Processing AI tuning response...")
        if not response or not response.parts:
            block_reason="?"; finish_reason="?";
            if response and response.prompt_feedback: block_reason = response.prompt_feedback.block_reason or "?";
            if response and response.candidates and response.candidates[0]: finish_reason = response.candidates[0].finish_reason.name if response.candidates[0].finish_reason else "?";
            error_msg = f"Tuning AI Error (Blocked/No Parts/Null Response). Block:{block_reason}, Finish:{finish_reason}";
            raise ValueError(error_msg)

        ai_result_raw_text = response.text # Store raw output
        # ---- START: Robust Extraction Logic ----
        print("  Attempting to extract JSON block from tuning response...")
        match = re.search(r'```json\s*(\{.*?\})\s*```', ai_result_raw_text, re.DOTALL)
        if match:
            extracted_json_string = match.group(1)
            print("    Extracted JSON using markdown pattern.")
        else:
            match = re.search(r'^\s*(\{.*?\})\s*$', ai_result_raw_text, re.DOTALL | re.MULTILINE)
            if match:
                extracted_json_string = match.group(1)
                print("    Extracted JSON using outer braces pattern.")
            else:
                start_brace = ai_result_raw_text.find('{')
                end_brace = ai_result_raw_text.rfind('}')
                if start_brace != -1 and end_brace != -1 and end_brace > start_brace:
                    extracted_json_string = ai_result_raw_text[start_brace : end_brace + 1]
                    print("    Extracted JSON using first/last brace pattern (fallback).")
                else:
                    error_msg = "Could not find JSON block delimiters in tuning AI response."
                    # Store the raw text for error reporting before raising
                    # Note: ai_result_raw_text already holds this
                    raise ValueError(error_msg)
        # ---- END: Robust Extraction Logic ----

        # --- Attempt Parsing (on extracted string) ---
        if not extracted_json_string: raise ValueError("Extraction seemed successful but result was empty?") # Safety check
        print(f"  Attempting to parse extracted tuning JSON string (length {len(extracted_json_string)})...")
        try:
            parsed_proposed_data = json.loads(extracted_json_string)
            print("  Successfully parsed tuning proposal.")
        except json.JSONDecodeError as e:
            # Store the extracted (but faulty) string for error reporting
            # Note: extracted_json_string holds this
            error_msg = f"Invalid JSON syntax in extracted tuning AI response. Error: {e}"
            raise ValueError(error_msg) # Raise to be caught by outer block

        # Check for AI reporting logical errors within the valid JSON
        if isinstance(parsed_proposed_data, dict) and "error" in parsed_proposed_data:
            error_msg = f"Tuning AI reported an error: {parsed_proposed_data['error']}"
            print(f"  {error_msg}")
            local_proposed_data = None # Discard the error JSON
        else:
            # --- Enforce Schema on successful proposal ---
            print("  Ensuring proposal adheres to schema keys...")
            if TOP_LEVEL_SCHEMA_PROPERTIES:
                local_proposed_data = ensure_schema_keys(parsed_proposed_data, TOP_LEVEL_SCHEMA_PROPERTIES)
                print("  Schema key enforcement complete for proposal.")
            else:
                print("  WARN: Simplified schema structure not available, using proposal as-is.")
                local_proposed_data = parsed_proposed_data

    except Exception as e:
        if not error_msg: error_msg = f"Error during tuning process: {e}"
        print(f"  {error_msg}")
        local_proposed_data = None # Ensure None on error
        # Use extracted_json_string if available for error context, else use raw text
        error_context_string = extracted_json_string if extracted_json_string else ai_result_raw_text
        if not error_context_string: error_context_string = "Raw AI output unavailable due to error."
        import traceback
        traceback.print_exc(file=sys.stderr)

    # Assign final result to the global variable
    proposed_tuned_json_data = local_proposed_data

    # --- Define and Schedule Update GUI (Callback uses updated error handling) ---
    def update_ui_after_tuning(final_data, final_error_msg, context_string_on_error):
         if root and root.winfo_exists():
            enable_buttons() # Re-enable main buttons

            if final_data and final_error_msg is None: # Success
                # (Success case UI update - unchanged from previous version)
                try:
                    pretty_proposed_json = json.dumps(final_data, indent=2, ensure_ascii=False)
                    if proposed_json_display and proposed_json_display.winfo_exists():
                         proposed_json_display.config(state=tk.NORMAL); proposed_json_display.delete('1.0', END); proposed_json_display.insert('1.0', pretty_proposed_json); proposed_json_display.config(state=tk.DISABLED);
                    if tune_save_button and tune_save_button.winfo_exists(): tune_save_button.config(state=tk.NORMAL)
                    if tune_discard_button and tune_discard_button.winfo_exists(): tune_discard_button.config(state=tk.NORMAL)
                    if tune_status_var: tune_status_var.set("Status: Review proposal and Save or Discard.")
                except Exception as display_e:
                    display_error = f"Error displaying proposal: {display_e}"
                    if tune_status_var: tune_status_var.set(f"Status: {display_error}")
                    if proposed_json_display and proposed_json_display.winfo_exists():
                        proposed_json_display.config(state=tk.NORMAL); proposed_json_display.delete('1.0', END); proposed_json_display.insert('1.0', f"Error displaying JSON:\n{display_e}"); proposed_json_display.config(state=tk.DISABLED);
                    disable_tuning_buttons(keep_load=True)
                    print(f"  ERROR: {display_error}")
            else: # Failure
                if not final_error_msg: final_error_msg = "Unknown tuning error."
                if tune_status_var: tune_status_var.set(f"Status: AI tuning failed. {final_error_msg}")
                if proposed_json_display and proposed_json_display.winfo_exists():
                    proposed_json_display.config(state=tk.NORMAL); proposed_json_display.delete('1.0', END);
                    error_display_text = f"Tuning Error:\n{final_error_msg}"
                    # Display the faulty extracted string OR raw text if extraction failed
                    snippet = (context_string_on_error or "")[:500] # Take first 500 chars
                    if snippet and snippet != "Raw AI output unavailable due to error.":
                         error_display_text += f"\n\n--- Faulty Extracted/Raw AI Response Snippet ---\n{snippet}..."
                    proposed_json_display.insert('1.0', error_display_text)
                    proposed_json_display.config(state=tk.DISABLED);
                messagebox.showerror("AI Tuning Error", f"AI tuning failed:\n{final_error_msg}\n\n(Check logs/text area for details/snippet)", parent=root) # Modified message
                disable_tuning_buttons(keep_load=True)

    # Schedule UI update
    if root and root.winfo_exists():
        # Pass the context string captured during error
        error_context_string_for_ui = extracted_json_string if 'extracted_json_string' in locals() and extracted_json_string else ai_result_raw_text
        if 'error_context_string' not in locals(): error_context_string = "Context unavailable." # Fallback

        root.after(0, update_ui_after_tuning, proposed_tuned_json_data, error_msg, error_context_string_for_ui)
        global json_tune_thread
        json_tune_thread = None # Clear the handle

def save_tuned_json():
    """Saves the proposed tuned JSON data to the character's file."""
    # Check if widgets exist
    if not all(['tune_character_var' in globals() and tune_character_var,
                 # Check if proposed_tuned_json_data exists and is a dict
                 'proposed_tuned_json_data' in globals() and isinstance(proposed_tuned_json_data, dict)]):
        print("Error: Cannot save tuned JSON - data or widgets not ready.")
        return

    selected_char = tune_character_var.get()
    if not selected_char or selected_char == "(No Characters Found)":
        messagebox.showerror("Error", "Cannot save: No valid character selected.")
        return

    # Sanitize filename
    json_filename_base = sanitize_filename(selected_char, extension="")
    if not json_filename_base: messagebox.showerror("Error", f"Cannot save: Failed to sanitize filename for '{selected_char}'."); return
    json_filename = f"{json_filename_base}.json"
    filepath = os.path.join(CHARACTER_JSON_OUTPUT_DIR, json_filename)

    print(f"--- Saving Tuned JSON for {selected_char} ---")
    print(f"  Saving to: {filepath}")
    disable_buttons() # Disable all buttons during save
    disable_tuning_buttons()

    try:
        # Ensure directory exists
        os.makedirs(CHARACTER_JSON_OUTPUT_DIR, exist_ok=True)
        # Write the tuned data
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(proposed_tuned_json_data, f, indent=2, ensure_ascii=False)

        print("  Save successful.")
        # Reload the JSON for the current character to reflect changes and clear proposal
        load_current_json_for_tuning()
        if tune_status_var: tune_status_var.set(f"Status: Successfully saved tuned JSON for {selected_char}.")
        messagebox.showinfo("Save Successful", f"Tuned JSON saved successfully for {selected_char}.")
        # No need to manually clear proposed_tuned_json_data, load_current_json does it

    except Exception as e:
        messagebox.showerror("Save Error", f"Failed to save tuned JSON for {selected_char}:\n{e}")
        if tune_status_var: tune_status_var.set(f"Status: Error saving tuned JSON.")
        print(f"ERROR saving tuned JSON: {e}")
        # Re-enable buttons on save error
        enable_buttons()

def discard_tuned_changes():
    """Clears the proposed JSON and instruction input."""
    global proposed_tuned_json_data

    # Check if widgets exist
    if not all(['tuning_instruction_input' in globals() and tuning_instruction_input,
                'proposed_json_display' in globals() and proposed_json_display,
                'tune_save_button' in globals() and tune_save_button,
                'tune_discard_button' in globals() and tune_discard_button,
                'tune_preview_button' in globals() and tune_preview_button]):
        print("WARN: Discard widgets not fully ready.")
        return

    print("Discarding tuned JSON proposal.")
    # Clear instruction input
    tuning_instruction_input.delete('1.0', END)
    # Clear proposed JSON display
    proposed_json_display.config(state=tk.NORMAL); proposed_json_display.delete('1.0', END); proposed_json_display.config(state=tk.DISABLED);
    # Disable Save/Discard buttons
    tune_save_button.config(state=tk.DISABLED)
    tune_discard_button.config(state=tk.DISABLED)
    # Re-enable Preview button if JSON is loaded
    tune_preview_button.config(state=tk.NORMAL if original_loaded_json_str else tk.DISABLED)

    if tune_status_var: tune_status_var.set("Status: Discarded proposed AI changes. Load JSON or enter instruction to preview again.")
    proposed_tuned_json_data = None # Clear the stored proposal data

# --- CORRECTED disable_tuning_buttons ---
def disable_tuning_buttons(keep_load=False):
        """Helper to disable buttons on the tuning tab."""
        # --- Define list of widgets specific to the tuning tab ---
        # Make sure these global variable names match exactly what's defined
        # at the top and assigned in setup_gui
        tuning_widgets_to_disable = [
            tune_preview_button, tune_save_button, tune_discard_button,
            tune_model_combobox
        ]
        # Handle load button separately based on keep_load flag
        load_state = tk.DISABLED if not keep_load else tk.NORMAL

        try:
            # --- Helper to set state safely ---
            def set_state(widget, state):
                if widget and isinstance(widget, (tk.Widget, ttk.Widget)) and widget.winfo_exists():
                    try:
                        # Special handling for combobox readonly state
                        if isinstance(widget, ttk.Combobox) and state == tk.NORMAL:
                            widget.config(state="readonly")
                        else:
                            widget.config(state=state)
                    except tk.TclError: pass # Ignore errors if widget destroyed

            # --- Disable/Enable the widgets ---
            set_state(tune_load_button, load_state) # Set load button state first
            for widget in tuning_widgets_to_disable:
                 set_state(widget, tk.DISABLED) # Disable others unconditionally

        except (tk.TclError, NameError, AttributeError) as e:
            # print(f"Minor error during disable_tuning_buttons: {e}") # Keep commented unless debugging
            pass # Ignore errors if widgets destroyed etc.

# --- Function to Update Instructions Based on Selected Tab ---
def update_instructions(event=None):
    """Updates the instruction label based on the currently selected notebook tab."""
    global instruction_label, notebook # Need access to these globals

    if notebook is None or instruction_label is None:
        # print("DEBUG: Notebook or Instruction Label not ready.") # Optional debug
        return # Widgets not ready yet

    try:
        # Get the index of the currently selected tab
        current_tab_index = notebook.index(notebook.select())
        # Get the instruction text from the dictionary, use default if index not found
        instruction_text = TAB_INSTRUCTIONS.get(current_tab_index, DEFAULT_INSTRUCTION)

        # Update the label's text
        if instruction_label.winfo_exists(): # Check if widget still exists
            instruction_label.config(text=instruction_text)
        else:
            print("WARN: Instruction label widget destroyed, cannot update text.")

    except tk.TclError:
        # This can happen if the notebook/widget is destroyed while trying to access it
        # print("DEBUG: TclError during instruction update (likely widget destroyed).") # Optional debug
        pass
    except Exception as e:
        print(f"ERROR updating instruction label: {e}")

# --- CORRECTED Fine-Tuning Load Function ---
def load_current_json_for_tuning():
    """Loads the selected character's JSON into the tuning display."""
    global original_loaded_json_str, proposed_tuned_json_data

    # --- ADDED: Check if essential tuning widgets exist ---
    widgets_ready = all([
        'tune_character_var' in globals() and tune_character_var,
        'current_json_display' in globals() and current_json_display and current_json_display.winfo_exists(),
        'tuning_instruction_input' in globals() and tuning_instruction_input and tuning_instruction_input.winfo_exists(),
        'proposed_json_display' in globals() and proposed_json_display and proposed_json_display.winfo_exists(),
        'tune_status_var' in globals() and tune_status_var,
        'tune_preview_button' in globals() and tune_preview_button and tune_preview_button.winfo_exists(), # Check preview button too
        'tune_save_button' in globals() and tune_save_button and tune_save_button.winfo_exists(), # Check save
        'tune_discard_button' in globals() and tune_discard_button and tune_discard_button.winfo_exists() # Check discard
    ])
    if not widgets_ready:
        # print("WARN: Tuning GUI elements not fully ready during load_current_json_for_tuning.") # Less verbose
        return
    # --- END ADDED CHECK ---

    selected_char = tune_character_var.get()

    # Clear previous state regardless of selection validity
    current_json_display.config(state=tk.NORMAL); current_json_display.delete('1.0', END); current_json_display.config(state=tk.DISABLED);
    tuning_instruction_input.delete('1.0', END);
    proposed_json_display.config(state=tk.NORMAL); proposed_json_display.delete('1.0', END); proposed_json_display.config(state=tk.DISABLED);
    original_loaded_json_str = None
    proposed_tuned_json_data = None
    disable_tuning_buttons() # Disable action buttons initially

    if not selected_char or selected_char == "(No Characters Found)":
        current_json_display.config(state=tk.NORMAL); current_json_display.insert('1.0', "(Select a valid character)"); current_json_display.config(state=tk.DISABLED);
        tune_status_var.set("Select character to load."); return

    # --- START: Added Debugging prints ---
    print(f"DEBUG: load_current_json_for_tuning: Selected Character = '{selected_char}'")
    json_filename = sanitize_filename(selected_char, ".json")
    print(f"DEBUG: load_current_json_for_tuning: Sanitized Filename = '{json_filename}'")
    # --- END: Added Debugging prints ---

    if not json_filename: # Handle potential error from sanitize_filename
        messagebox.showerror("Error", f"Could not create a valid filename for '{selected_char}'.")
        tune_status_var.set("Error: Invalid character name for file.")
        return

    filepath = os.path.join(CHARACTER_JSON_OUTPUT_DIR, json_filename)
    # --- START: Added Debugging print for full path ---
    print(f"DEBUG: load_current_json_for_tuning: Checking path = '{filepath}'")
    # --- END: Added Debugging print for full path ---

    if not os.path.exists(filepath):
        # --- START: Added More specific error message ---
        print(f"ERROR: File not found check failed for path: {filepath}")
        # --- END: Added More specific error message ---
        # Display message in text area instead of just status bar
        current_json_display.config(state=tk.NORMAL)
        current_json_display.delete('1.0', END)
        # Improve message shown in GUI
        current_json_display.insert('1.0', f"JSON file not found for '{selected_char}'.\n\nExpected at:\n{filepath}\n\nVerify the file exists with this exact name and location.\nRun 'Generate JSON' on Tab 3 if needed.")
        current_json_display.config(state=tk.DISABLED)
        tune_status_var.set(f"Error: JSON file not found for {selected_char}")
        # Keep buttons disabled via the initial disable_tuning_buttons call
        return

    try:
        with open(filepath, 'r', encoding='utf-8') as f: original_loaded_json_str = f.read()
        json_data = json.loads(original_loaded_json_str)
        pretty_json = json.dumps(json_data, indent=2, ensure_ascii=False)
        current_json_display.config(state=tk.NORMAL); current_json_display.insert('1.0', pretty_json); current_json_display.config(state=tk.DISABLED)
        tune_status_var.set(f"Loaded current JSON for {selected_char}.")
        # Only enable preview if loading was successful and no process is active
        any_process_active = (scrape_all_thread and scrape_all_thread.is_alive()) or \
                             (json_gen_single_thread and json_gen_single_thread.is_alive()) or \
                             (json_gen_all_thread and json_gen_all_thread.is_alive()) or \
                             (json_tune_thread and json_tune_thread.is_alive())
        if not any_process_active:
             # Also ensure essential widgets are available before enabling
             if tune_preview_button and tune_preview_button.winfo_exists():
                  tune_preview_button.config(state=tk.NORMAL) # Enable preview

    except Exception as e:
        messagebox.showerror("Load Error", f"Failed to load/parse JSON for {selected_char}:\n{e}")
        current_json_display.config(state=tk.NORMAL); current_json_display.delete('1.0', END); current_json_display.insert('1.0', f"Error loading:\n{e}"); current_json_display.config(state=tk.DISABLED);
        tune_status_var.set(f"Error loading JSON for {selected_char}");
        original_loaded_json_str = None;
        disable_tuning_buttons() # Ensure buttons remain disabled on error





# ==============================================================================
# == GUI SETUP FUNCTION ==
# ==============================================================================
def setup_gui():
    # Make all potentially referenced GUI variables global within setup
    # (Ensure this list matches the variables actually used below)
    global root, notebook, status_var, status_label, instruction_label, log_text, copy_log_button, stop_button, \
           scraper_character_var, scraper_character_dropdown, scraper_url_entry, scraper_url_listbox, \
           add_url_button, remove_url_button, scrape_button, scrape_all_button, action_frame_tab_manage, \
           progress_var, progress_bar, time_remaining_var, time_remaining_label, \
           add_char_name_entry, add_char_img_entry, add_char_icon_entry, add_char_wiki_entry, \
           add_char_tracker_entry, add_char_comic_entry, create_char_button, \
           json_character_var, json_character_dropdown, model_selection_var, model_combobox, \
           json_output_file_label, edit_prompt_button, open_prompt_dir_button, \
           generate_json_button, generate_all_json_button, \
           tune_character_var, tune_character_dropdown, tune_load_button, current_json_display, \
           tuning_instruction_input, tune_model_var, tune_model_combobox, tune_preview_button, \
           proposed_json_display, tune_save_button, tune_discard_button, tune_status_var, \
           update_meta_button, update_info_button # Added missing buttons

    root = tk.Tk()
    root.title("Marvel Rivals Updater v3.1") # Minor version bump maybe
    root.geometry("900x800")
    style = ttk.Style()
    style.configure("Grey.TLabel", foreground="grey")
    style.configure("Stop.TButton", foreground="red", font=('TkDefaultFont', 10, 'bold'))

    notebook = ttk.Notebook(root)
    notebook.pack(pady=10, padx=10, fill=tk.BOTH, expand=True)
        # Bind tab changes to update the instruction label
    notebook.bind("<<NotebookTabChanged>>", update_instructions)
    # Set initial instructions for the first tab
    root.after(100, update_instructions) # Use 'after' to ensure everything is drawn first

    # --- Tab 1: Manage & Scrape ---
    manage_frame = ttk.Frame(notebook, padding="10")
    notebook.add(manage_frame, text='1. Manage & Scrape')
    manage_frame.columnconfigure(1, weight=1)

    ttk.Label(manage_frame, text="Character:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
    scraper_character_var = tk.StringVar(root)
    scraper_character_options = ACTIVE_CHARACTER_LIST if ACTIVE_CHARACTER_LIST else ["(No Characters Found)"]
    scraper_character_dropdown = ttk.Combobox(manage_frame, textvariable=scraper_character_var, values=scraper_character_options, state="readonly", width=40)
    scraper_character_dropdown.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
    scraper_character_var.trace_add("write", update_scraper_url_listbox)

    scraper_url_frame = ttk.LabelFrame(manage_frame, text="Manage Source URLs (Wiki, Tracker, etc.)", padding="10")
    scraper_url_frame.grid(row=1, column=0, columnspan=2, padx=5, pady=(5,10), sticky="nsew")
    scraper_url_frame.columnconfigure(1, weight=1)
    ttk.Label(scraper_url_frame, text="New URL:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
    scraper_url_entry = ttk.Entry(scraper_url_frame, width=50)
    scraper_url_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
    add_url_button = ttk.Button(scraper_url_frame, text="Add URL", command=add_scraper_url)
    add_url_button.grid(row=0, column=2, padx=5, pady=5)
    ttk.Label(scraper_url_frame, text="Saved URLs:").grid(row=1, column=0, padx=5, pady=5, sticky="nw")
    scraper_listbox_frame = ttk.Frame(scraper_url_frame)
    scraper_listbox_frame.grid(row=1, column=1, columnspan=2, padx=5, pady=5, sticky="nsew")
    scraper_listbox_frame.rowconfigure(0, weight=1)
    scraper_listbox_frame.columnconfigure(0, weight=1)
    scraper_url_scrollbar = Scrollbar(scraper_listbox_frame, orient=tk.VERTICAL)
    scraper_url_listbox = Listbox(scraper_listbox_frame, height=5, width=60, yscrollcommand=scraper_url_scrollbar.set, exportselection=False, selectmode=SINGLE)
    scraper_url_scrollbar.config(command=scraper_url_listbox.yview)
    scraper_url_scrollbar.grid(row=0, column=1, sticky="ns")
    scraper_url_listbox.grid(row=0, column=0, sticky="nsew")
    scraper_url_listbox.bind('<<ListboxSelect>>', on_listbox_select)
    remove_url_button = ttk.Button(scraper_url_frame, text="Remove Selected URL", command=remove_scraper_url, state=tk.DISABLED)
    remove_url_button.grid(row=2, column=1, columnspan=2, padx=5, pady=(0,5), sticky="e")

    action_frame_tab_manage = ttk.Frame(manage_frame)
    action_frame_tab_manage.grid(row=2, column=0, columnspan=2, pady=(10, 5), sticky="ew")
    scrape_button = ttk.Button(action_frame_tab_manage, text="Scrape Raw Text (Selected Char)", command=start_scrape_single_character, width=30)
    scrape_button.pack(side=tk.LEFT, padx=5, pady=2)
    scrape_all_button = ttk.Button(action_frame_tab_manage, text="Scrape Raw Text (ALL Chars)", command=start_scrape_all_characters, width=30)
    scrape_all_button.pack(side=tk.LEFT, padx=5, pady=2)
    update_meta_button = ttk.Button(action_frame_tab_manage, text="Update Meta Stats from Tracker", command=start_update_all_meta_stats, width=30)
    update_meta_button.pack(side=tk.LEFT, padx=5, pady=2)
    update_info_button = ttk.Button(action_frame_tab_manage, text="Update Info Files from Site", command=start_update_info_files, width=30)
    update_info_button.pack(side=tk.LEFT, padx=5, pady=2)
    stop_button = ttk.Button(action_frame_tab_manage, text="Stop Scrape All", command=stop_scrape_all, style="Stop.TButton") # Defined but not packed initially

    progress_frame = ttk.Frame(manage_frame)
    progress_frame.grid(row=3, column=0, columnspan=2, pady=5, sticky="ew")
    progress_var = tk.DoubleVar()
    progress_bar = ttk.Progressbar(progress_frame, variable=progress_var, maximum=100)
    progress_bar.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
    time_remaining_var = tk.StringVar()
    time_remaining_label = ttk.Label(progress_frame, textvariable=time_remaining_var, width=25, anchor="e")
    time_remaining_label.pack(side=tk.RIGHT, padx=5)
    manage_frame.rowconfigure(4, weight=1)

    # --- Tab 2: Add Character ---
    add_char_frame = ttk.Frame(notebook, padding="10")
    notebook.add(add_char_frame, text='2. Add Character')
    add_char_frame.columnconfigure(1, weight=1)
    ttk.Label(add_char_frame, text="Enter details for the new character. Required fields marked with *.").grid(row=0, column=0, columnspan=2, padx=5, pady=(5,10), sticky="w")
    ttk.Label(add_char_frame, text="Character Name*:").grid(row=1, column=0, padx=5, pady=3, sticky="w")
    add_char_name_entry = ttk.Entry(add_char_frame, width=50)
    add_char_name_entry.grid(row=1, column=1, padx=5, pady=3, sticky="ew")
    ttk.Label(add_char_frame, text="Main Image Filename*:").grid(row=2, column=0, padx=5, pady=3, sticky="w")
    add_char_img_entry = ttk.Entry(add_char_frame, width=50)
    add_char_img_entry.grid(row=2, column=1, padx=5, pady=3, sticky="ew")
    ttk.Label(add_char_frame, text="Icon Filename*:").grid(row=3, column=0, padx=5, pady=3, sticky="w")
    add_char_icon_entry = ttk.Entry(add_char_frame, width=50)
    add_char_icon_entry.grid(row=3, column=1, padx=5, pady=3, sticky="ew")
    ttk.Label(add_char_frame, text="Wiki URL:").grid(row=4, column=0, padx=5, pady=3, sticky="w")
    add_char_wiki_entry = ttk.Entry(add_char_frame, width=50)
    add_char_wiki_entry.grid(row=4, column=1, padx=5, pady=3, sticky="ew")
    ttk.Label(add_char_frame, text="Tracker URL:").grid(row=5, column=0, padx=5, pady=3, sticky="w")
    add_char_tracker_entry = ttk.Entry(add_char_frame, width=50)
    add_char_tracker_entry.grid(row=5, column=1, padx=5, pady=3, sticky="ew")
    ttk.Label(add_char_frame, text="Comic Wiki URL:").grid(row=6, column=0, padx=5, pady=3, sticky="w")
    add_char_comic_entry = ttk.Entry(add_char_frame, width=50)
    add_char_comic_entry.grid(row=6, column=1, padx=5, pady=3, sticky="ew")
    ttk.Label(add_char_frame, text=f"(Place image/icon files in: '{IMAGE_DIR_CHECK}')", style="Grey.TLabel").grid(row=7, column=1, padx=5, pady=(0,10), sticky="w")
    create_char_button = ttk.Button(add_char_frame, text="Create New Character Files", command=create_new_character, width=30)
    create_char_button.grid(row=8, column=1, padx=5, pady=10, sticky="e")
    add_char_frame.rowconfigure(9, weight=1)

    # --- Tab 3: Generate/Update JSON ---
    json_gen_frame = ttk.Frame(notebook, padding="10")
    notebook.add(json_gen_frame, text='3. Generate/Update JSON')
    json_gen_frame.columnconfigure(1, weight=1)
    ttk.Label(json_gen_frame, text="1. Character:").grid(row=0, column=0, padx=5, pady=(10,5), sticky="w")
    json_character_var = tk.StringVar(root)
    json_character_options = ACTIVE_CHARACTER_LIST if ACTIVE_CHARACTER_LIST else ["(No Characters Found)"]
    json_character_dropdown = ttk.Combobox(json_gen_frame, textvariable=json_character_var, values=json_character_options, state="readonly", width=40)
    json_character_dropdown.grid(row=0, column=1, columnspan=2, padx=5, pady=(10,5), sticky="ew")
    json_character_var.trace_add("write", update_json_paths)
    model_label = ttk.Label(json_gen_frame, text="2. Select AI Model:")
    model_label.grid(row=1, column=0, padx=5, pady=5, sticky="w")
    model_selection_var = tk.StringVar(root)
    model_combobox = ttk.Combobox(json_gen_frame, textvariable=model_selection_var, values=AVAILABLE_MODELS, state="readonly", width=40)
    model_combobox.grid(row=1, column=1, columnspan=2, padx=5, pady=5, sticky="ew")
    model_combobox.bind('<<ComboboxSelected>>', save_settings)
    json_output_file_label = ttk.Label(json_gen_frame, text="Output JSON: (Select Character)", style="Grey.TLabel", relief=tk.SUNKEN, anchor="w", wraplength=700)
    json_output_file_label.grid(row=3, column=0, columnspan=3, padx=5, pady=2, sticky="ew")
    prompt_edit_frame = ttk.Frame(json_gen_frame)
    prompt_edit_frame.grid(row=4, column=0, columnspan=3, pady=(10,5), sticky="ew")
    edit_prompt_button = ttk.Button(prompt_edit_frame, text="Edit API Prompt Template (v3)", command=edit_api_prompt, width=28)
    edit_prompt_button.pack(side=tk.LEFT, padx=5)
    open_prompt_dir_button = ttk.Button(prompt_edit_frame, text="Open Script Folder", command=open_prompt_directory, width=28)
    open_prompt_dir_button.pack(side=tk.LEFT, padx=5)
    json_action_frame = ttk.Frame(json_gen_frame)
    json_action_frame.grid(row=5, column=0, columnspan=3, pady=(5, 20), sticky="ew")
    generate_json_button = ttk.Button(json_action_frame, text="Generate JSON (Selected Char)", command=start_generate_single_json, state=tk.DISABLED, width=28)
    generate_json_button.pack(side=tk.LEFT, padx=(0, 10))
    generate_all_json_button = ttk.Button(json_action_frame, text="Generate ALL JSON", command=start_generate_all_json_thread, width=28)
    generate_all_json_button.pack(side=tk.LEFT, padx=(10, 0))
    json_gen_frame.rowconfigure(6, weight=1)

    # --- Tab 4: Fine-Tune JSON ---
    tune_frame = ttk.Frame(notebook, padding="10")
    notebook.add(tune_frame, text='4. Fine-Tune JSON')
    tune_frame.columnconfigure(0, weight=1)
    tune_frame.columnconfigure(1, weight=1)
    tune_frame.rowconfigure(2, weight=1) # Current JSON display row
    tune_frame.rowconfigure(4, weight=1) # Instruction input row

    tune_top_frame = ttk.Frame(tune_frame)
    tune_top_frame.grid(row=0, column=0, columnspan=2, padx=5, pady=5, sticky="ew")
    tune_top_frame.columnconfigure(1, weight=1)
    ttk.Label(tune_top_frame, text="Character:").pack(side=tk.LEFT, padx=(0,5))
    tune_character_var = tk.StringVar(root)
    tune_character_options = ACTIVE_CHARACTER_LIST if ACTIVE_CHARACTER_LIST else ["(No Characters Found)"]
    tune_character_dropdown = ttk.Combobox(tune_top_frame, textvariable=tune_character_var, values=tune_character_options, state="readonly", width=30)
    tune_character_dropdown.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
    tune_character_var.trace_add("write", lambda name, index, mode: load_current_json_for_tuning())
    tune_load_button = ttk.Button(tune_top_frame, text="Load Current JSON", command=load_current_json_for_tuning, width=20)
    tune_load_button.pack(side=tk.LEFT, padx=(10, 5))

    ttk.Label(tune_frame, text="Current JSON:").grid(row=1, column=0, padx=5, pady=(10,0), sticky="nw")
    current_json_frame = ttk.Frame(tune_frame)
    current_json_frame.grid(row=2, column=0, padx=5, pady=2, sticky="nsew")
    current_json_frame.rowconfigure(0, weight=1); current_json_frame.columnconfigure(0, weight=1)
    current_json_scroll = Scrollbar(current_json_frame)
    current_json_scroll.pack(side=tk.RIGHT, fill=tk.Y)
    current_json_display = Text(current_json_frame, wrap=tk.WORD, height=10, width=50, yscrollcommand=current_json_scroll.set, state=tk.DISABLED, font=("Courier New", 9))
    current_json_scroll.config(command=current_json_display.yview)
    current_json_display.pack(fill=tk.BOTH, expand=True)

    ttk.Label(tune_frame, text="Proposed JSON (AI Generated):").grid(row=1, column=1, padx=5, pady=(10,0), sticky="nw")
    proposed_json_frame = ttk.Frame(tune_frame)
    proposed_json_frame.grid(row=2, column=1, padx=5, pady=2, sticky="nsew")
    proposed_json_frame.rowconfigure(0, weight=1); proposed_json_frame.columnconfigure(0, weight=1)
    proposed_json_scroll = Scrollbar(proposed_json_frame)
    proposed_json_scroll.pack(side=tk.RIGHT, fill=tk.Y)
    proposed_json_display = Text(proposed_json_frame, wrap=tk.WORD, height=10, width=50, yscrollcommand=proposed_json_scroll.set, state=tk.DISABLED, font=("Courier New", 9))
    proposed_json_scroll.config(command=proposed_json_display.yview)
    proposed_json_display.pack(fill=tk.BOTH, expand=True)

    ttk.Label(tune_frame, text="Tuning Instruction (Describe the change you want the AI to make):").grid(row=3, column=0, columnspan=2, padx=5, pady=(10,0), sticky="sw")
    instruction_frame = ttk.Frame(tune_frame)
    instruction_frame.grid(row=4, column=0, columnspan=2, padx=5, pady=2, sticky="nsew")
    instruction_frame.rowconfigure(0, weight=1); instruction_frame.columnconfigure(0, weight=1)
    instruction_scroll = Scrollbar(instruction_frame)
    instruction_scroll.pack(side=tk.RIGHT, fill=tk.Y)
    tuning_instruction_input = Text(instruction_frame, wrap=tk.WORD, height=4, width=100, yscrollcommand=instruction_scroll.set)
    instruction_scroll.config(command=tuning_instruction_input.yview)
    tuning_instruction_input.pack(fill=tk.BOTH, expand=True)

    tune_controls_frame = ttk.Frame(tune_frame)
    tune_controls_frame.grid(row=5, column=0, columnspan=2, padx=5, pady=5, sticky="ew")
    tune_controls_frame.columnconfigure(2, weight=1) # Allow space for right-aligned buttons
    ttk.Label(tune_controls_frame, text="AI Model (Tuning):").pack(side=tk.LEFT, padx=(0,5))
    tune_model_var = tk.StringVar(root)
    tune_model_combobox = ttk.Combobox(tune_controls_frame, textvariable=tune_model_var, values=AVAILABLE_MODELS, state="readonly", width=30)
    tune_model_combobox.pack(side=tk.LEFT, padx=5)
    tune_model_combobox.bind('<<ComboboxSelected>>', save_settings)
    tune_preview_button = ttk.Button(tune_controls_frame, text="Preview AI Tuning", command=preview_ai_tuning, width=20, state=tk.DISABLED)
    tune_preview_button.pack(side=tk.LEFT, padx=5)

    tune_action_buttons_frame = ttk.Frame(tune_controls_frame) # Frame to hold Save/Discard on right
    tune_action_buttons_frame.pack(side=tk.RIGHT) # Pack this frame to the right
    tune_save_button = ttk.Button(tune_action_buttons_frame, text="Save Tuned JSON", command=save_tuned_json, width=20, state=tk.DISABLED)
    tune_save_button.pack(side=tk.LEFT, padx=5) # Pack buttons inside this frame
    tune_discard_button = ttk.Button(tune_action_buttons_frame, text="Discard Changes", command=discard_tuned_changes, width=20, state=tk.DISABLED)
    tune_discard_button.pack(side=tk.LEFT, padx=5)

    tune_status_var = tk.StringVar(value="Load character JSON to begin tuning.")
    tune_status_label = ttk.Label(tune_frame, textvariable=tune_status_var, relief=tk.SUNKEN, anchor="w", wraplength=880)
    tune_status_label.grid(row=6, column=0, columnspan=2, padx=5, pady=(10,0), sticky="sew")

    # --- CORRECTED Shared Bottom Section ---
    bottom_frame = ttk.Frame(root, padding=(10, 0, 10, 10))
    bottom_frame.pack(side=tk.BOTTOM, fill=tk.BOTH, expand=True) # Pack at bottom

    # Status Label (First element in bottom_frame)
    status_var = tk.StringVar(value="Status: Initializing...")
    status_label = ttk.Label(bottom_frame, textvariable=status_var, relief=tk.SUNKEN, anchor="w", wraplength=880)
    status_label.pack(fill=tk.X, pady=(5, 5), side=tk.TOP) # Pack status at the top of bottom_frame

    # Instruction Label (Packed below status, above logs)
    instruction_label = ttk.Label(
        bottom_frame,
        text=DEFAULT_INSTRUCTION, # Start with default text
        relief=tk.FLAT,           # Make it look less like a status bar
        anchor="w",
        justify=tk.LEFT,          # Align text left
        padding=(5, 5, 5, 5),     # Add some internal padding
        wraplength=850            # Adjust wrap length as needed (~window width - padding)
        # Optional: Add background/foreground colors if desired
        # background="#333333",
        # foreground="#CCCCCC",
    )
    instruction_label.pack(fill=tk.X, pady=(0, 5), side=tk.TOP) # Pack below status, fill horizontally

    # Frame to hold Log Box and Copy Button horizontally
    log_area_frame = ttk.Frame(bottom_frame)
    log_area_frame.pack(fill=tk.BOTH, expand=True, side=tk.TOP, pady=(0, 5)) # Pack below status, expand

    # Log Box Frame (Inside log_area_frame)
    log_frame = ttk.LabelFrame(log_area_frame, text="Logs", padding="5")
    log_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True) # Pack log frame to left, let it expand

    log_scrollbar_y = Scrollbar(log_frame, orient=tk.VERTICAL)
    log_text = Text(log_frame, height=8, width=100, wrap=tk.WORD, relief=tk.SUNKEN, borderwidth=1, font=("Courier New", 9), background='#2E2E2E', foreground='#D4D4D4', insertbackground='white', yscrollcommand=log_scrollbar_y.set)
    log_scrollbar_y.config(command=log_text.yview)
    log_scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)
    log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    # Copy Log Button (Inside log_area_frame, next to log_frame)
    copy_log_button = ttk.Button(log_area_frame, text="Copy Logs", command=copy_logs_to_clipboard)
    copy_log_button.pack(side=tk.LEFT, padx=(5, 0), anchor="ne") # Pack next to log frame, align top-east (adjust anchor as needed)

# --- End of setup_gui function ---
# ==============================================================================
# == MAIN EXECUTION BLOCK ==
# ==============================================================================
if __name__ == "__main__":
    # 1. Ensure necessary directories exist
    # Use exist_ok=True to avoid errors if they already exist
    os.makedirs(CHARACTER_JSON_OUTPUT_DIR, exist_ok=True)
    os.makedirs(CONFIG_DIR, exist_ok=True)
    os.makedirs(RAW_TEXT_DIR, exist_ok=True)
    os.makedirs(os.path.join(CHARACTER_JSON_OUTPUT_DIR, "failed"), exist_ok=True) # For error files

    # 2. Load essential data needed BEFORE GUI setup
    load_character_list_from_files() # Scans CHARACTER_JSON_OUTPUT_DIR
    load_urls()                    # Loads scraper/saved_character_urls.json

    # 3. Build the GUI
    print("--- Setting up GUI ---")
    setup_gui() # Creates all widgets and assigns them to global variables
    print("--- GUI Setup Complete ---")

    # 4. Setup log redirection (Optional - currently commented out)
    # If enabling, ensure log_text widget exists from setup_gui()
    # print("Setting up log redirection...")
    log_redirector = TextRedirector(log_text)
    sys.stdout = log_redirector
    sys.stderr = log_redirector
    # print("Log redirection active.")
    print("--- Log redirection bypassed (using console) ---") # If commented out

    # 5. Print startup messages
    print("="*40); print("Marvel Rivals Updater v3.0"); print("="*40 + "\n")
    print(f"Base Directory: {BASE_DIR}")
    print(f"Character JSON Dir: {CHARACTER_JSON_OUTPUT_DIR}")
    print(f"Raw Text Dir: {RAW_TEXT_DIR}")
    print(f"Config Dir: {CONFIG_DIR}")
    print("\n--- Library Status ---")
    print(f"Google AI Library Available: {GOOGLE_AI_AVAILABLE}")
    print(f"DotEnv Library Available: {DOTENV_AVAILABLE}")
    if not GOOGLE_AI_AVAILABLE: print("-> Please install: pip install google-generativeai")
    if not DOTENV_AVAILABLE: print("-> Optional: pip install python-dotenv (for .env API key loading)")

    # 6. Initial GUI Population (Dropdowns)
    print("--- Populating Initial Dropdown Values ---")
    update_all_character_dropdowns(initial_setup=True) # Pass flag to prevent premature callbacks

    # 7. Define the function to run after GUI is ready
    def initial_api_checks():
        global google_api_key # Ensure global key is accessible if modified

        print("\n--- Initializing API & Settings ---")
        if not GOOGLE_AI_AVAILABLE:
            print("ERROR: Google AI library not installed.")
            # Update GUI elements safely if they exist
            if model_combobox and model_combobox.winfo_exists(): model_combobox['values'] = FALLBACK_MODELS; model_combobox.set(FALLBACK_DEFAULT_MODEL); model_combobox.config(state=tk.DISABLED)
            if tune_model_combobox and tune_model_combobox.winfo_exists(): tune_model_combobox['values'] = FALLBACK_MODELS; tune_model_combobox.set(FALLBACK_DEFAULT_MODEL); tune_model_combobox.config(state=tk.DISABLED)
            if status_var: status_var.set("Status: Google AI Lib Missing!")
            if model_selection_var: model_selection_var.set(FALLBACK_DEFAULT_MODEL)
            if tune_model_var: tune_model_var.set(FALLBACK_DEFAULT_MODEL)
            return # Stop further checks

        # Check API Key (Loaded from environment/dotenv earlier)
        if not google_api_key:
            print("ERROR: GOOGLE_API_KEY not found in environment or .env file.")
            # Update GUI elements safely if they exist
            if model_combobox and model_combobox.winfo_exists(): model_combobox['values'] = FALLBACK_MODELS; model_combobox.set(FALLBACK_DEFAULT_MODEL); model_combobox.config(state=tk.DISABLED)
            if tune_model_combobox and tune_model_combobox.winfo_exists(): tune_model_combobox['values'] = FALLBACK_MODELS; tune_model_combobox.set(FALLBACK_DEFAULT_MODEL); tune_model_combobox.config(state=tk.DISABLED)
            if status_var: status_var.set("Status: Google API Key Missing!")
            if model_selection_var: model_selection_var.set(FALLBACK_DEFAULT_MODEL)
            if tune_model_var: tune_model_var.set(FALLBACK_DEFAULT_MODEL)
            return # Stop further checks
        else:
             print("Google API Key found.")

        # Get available models *first* - This updates global AVAILABLE_MODELS
        print("Fetching available AI models...")
        get_available_generative_models(google_api_key)
        print(f"Available models fetched ({len(AVAILABLE_MODELS)}).")

        # Now load settings, which will use AVAILABLE_MODELS and update comboboxes
        print("Loading settings and updating model selection UI...")
        load_settings()

        # Trigger dependent updates AFTER settings are loaded and models populated
        print("Triggering post-initialization UI updates...")
        if 'update_json_paths' in globals(): update_json_paths()
        if 'load_current_json_for_tuning' in globals(): load_current_json_for_tuning() # Load initial tuning state

        print("--- Initialization Complete ---")
        if status_var: status_var.set("Status: Ready.") # Update status if checks passed

    # 8. Schedule initial checks and run main loop
    if root:
        print("--- Scheduling Initial API Checks & Starting GUI Main Loop ---")
        # Schedule initial_api_checks to run shortly after mainloop starts
        root.after(150, initial_api_checks)
        root.mainloop() # Start the Tkinter event loop
    else:
        print("FATAL ERROR: Failed to create main Tkinter window.")
        sys.exit(1) # Exit if GUI failed to initialize