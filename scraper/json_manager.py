# File: json_manager.py
import json
import os
import re
import datetime
import random
import urllib.parse # For Reddit link generation
import shutil # For moving error files
import copy # For deepcopy
import sys
# Import from our other new modules
# We assume these are in the same directory or Python's path can find them
import scraper_utils  # For scraping functions
import ai_processor   # For AI interaction functions
import config_manager # For loading/saving certain configs like color pools

# --- Constants & Paths needed by this module ---
# These paths are relative to where updater_v3.py (the main script) is.
# For a module, it's often better if the main script passes these paths,
# or they are retrieved from a shared configuration.
# For now, we'll define them assuming SCRIPT_DIR is from the main script's context.
# This will require the main script to pass SCRIPT_DIR or pre-calculated paths.

# Placeholder: These will be initialized by a function called from updater_v3.py
JM_SCRIPT_DIR = ""
JM_BASE_DIR = ""
JM_RAW_TEXT_DIR = ""
JM_CHARACTER_JSON_OUTPUT_DIR = ""
JM_INFO_OUTPUT_DIR = ""
JM_FAILED_JSON_DIR = "" # For API error files

# Global constants from the main script that json_manager might need
# These should also ideally be passed or accessed from a shared config.
# For now, we'll assume they get set via an init function or are passed.
JM_CORE_GENERATED_KEYS = []
JM_PRESERVED_SECTIONS_DURING_CORE_GEN = []
JM_PRESERVED_NESTED_FIELDS = []
JM_CHARACTER_BASE_SPEEDS = {}
JM_FINAL_JSON_SCHEMA_STRING = "" # For AI prompts
JM_TOP_LEVEL_SCHEMA_PROPERTIES = {} # For ensure_schema_keys

# Character color pools will be loaded via config_manager
character_color_pools_jm = {}


def init_json_manager_paths_and_config(
    script_dir, base_dir, raw_text_dir, char_json_dir, info_dir,
    core_keys, preserved_sections, preserved_nested, base_speeds,
    json_schema_str, top_level_schema_props, color_pools_file_path):
    """
    Initializes paths and configurations for the json_manager module.
    This should be called by the main script (updater_v3.py) once at startup.
    """
    global JM_SCRIPT_DIR, JM_BASE_DIR, JM_RAW_TEXT_DIR, JM_CHARACTER_JSON_OUTPUT_DIR, JM_INFO_OUTPUT_DIR
    global JM_CORE_GENERATED_KEYS, JM_PRESERVED_SECTIONS_DURING_CORE_GEN, JM_PRESERVED_NESTED_FIELDS
    global JM_CHARACTER_BASE_SPEEDS, JM_FINAL_JSON_SCHEMA_STRING, JM_TOP_LEVEL_SCHEMA_PROPERTIES
    global character_color_pools_jm, JM_FAILED_JSON_DIR

    JM_SCRIPT_DIR = script_dir
    JM_BASE_DIR = base_dir
    JM_RAW_TEXT_DIR = raw_text_dir
    JM_CHARACTER_JSON_OUTPUT_DIR = char_json_dir
    JM_FAILED_JSON_DIR = os.path.join(JM_CHARACTER_JSON_OUTPUT_DIR, "failed") # Define here
    JM_INFO_OUTPUT_DIR = info_dir

    JM_CORE_GENERATED_KEYS = core_keys
    JM_PRESERVED_SECTIONS_DURING_CORE_GEN = preserved_sections
    JM_PRESERVED_NESTED_FIELDS = preserved_nested
    JM_CHARACTER_BASE_SPEEDS = base_speeds
    JM_FINAL_JSON_SCHEMA_STRING = json_schema_str
    JM_TOP_LEVEL_SCHEMA_PROPERTIES = top_level_schema_props

    # Load color pools using config_manager logic if it's just a simple JSON load
    # Or, if config_manager.py is more complex, adapt. For now, direct load:
    try:
        if os.path.exists(color_pools_file_path):
            with open(color_pools_file_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
            if content and content.startswith('{'):
                character_color_pools_jm = json.loads(content)
                print(f"JM: Loaded color pools from {os.path.basename(color_pools_file_path)}")
        else:
            print(f"JM WARN: Color pools file not found: {color_pools_file_path}")
    except Exception as e:
        print(f"JM ERROR loading color pools: {e}")

    print("JM: JSON Manager initialized with paths and configurations.")


# --- Core JSON Processing Logic for a Single Character ---
def process_single_character_json(
    google_api_key_jm, # Renamed to avoid clash
    selected_character,
    raw_filepath,
    selected_model_name,
    progress_callback=None, # Optional callback for GUI updates
    character_index=0, total_characters=1 # For progress reporting
    ):
    """
    Orchestrates the generation/update of a single character's JSON file.
    This function contains the logic previously in generate_single_json_thread.
    Returns a tuple: (success_flag, message_or_data, original_casing_name, output_json_filepath)
    """
    print(f"\nJM: Processing Character: {selected_character} (Model: {selected_model_name})")
    
    # Use JM_ prefixed paths
    json_filename_base = scraper_utils.sanitize_filename(selected_character, extension="") # Use sanitize from scraper_utils
    if not json_filename_base:
        error_msg = f"JM ERROR: Failed to sanitize character name '{selected_character}' for output file."
        print(error_msg)
        return False, error_msg, selected_character, "unknown.json"

    json_filename = f"{json_filename_base}.json"
    json_filepath = os.path.join(JM_CHARACTER_JSON_OUTPUT_DIR, json_filename)
    
    success = False
    error_message_details_jm = None # Renamed
    final_json_data = None
    raw_response_on_error_jm = None # Renamed
    old_json_data = None
    original_casing_name = selected_character # Default, will be updated by AI

    try:
        # --- 0. Load Existing JSON (for preservation) ---
        if os.path.exists(json_filepath):
            try:
                with open(json_filepath, 'r', encoding='utf-8') as f_old:
                    old_json_data = json.load(f_old)
                print(f"JM:  Loaded existing JSON for {selected_character} to preserve edits.")
            except Exception as load_err:
                print(f"JM WARN: Could not load existing JSON for {selected_character}: {load_err}. Will generate fresh.")
                old_json_data = None

        # --- 1. Read and Clean Raw Text ---
        print(f"JM:  Reading Raw Text from: {os.path.basename(raw_filepath)}")
        with open(raw_filepath, 'r', encoding='utf-8') as f: raw_content = f.read()
        # Basic cleaning (can be enhanced or moved to scraper_utils if very complex)
        raw_content = re.sub(r'^===== CONTENT FROM:.*?=====\s*', '', raw_content, flags=re.MULTILINE).strip()
        raw_content = re.sub(r'\n\n={20,}\s*CONTENT FROM:.*?={20,}\s*\n\n', '\n\n---\n\n', raw_content, flags=re.DOTALL)
        raw_content = re.sub(r'\s*\[\s*edit\s*\]\s*', '', raw_content, flags=re.IGNORECASE)
        raw_content = re.sub(r'^\s*See\s*also\s*:.*?\n', '', raw_content, flags=re.MULTILINE | re.IGNORECASE)
        raw_content = re.sub(r'\n{3,}', '\n\n', raw_content).strip()
        print(f"JM:  Raw text read and cleaned for {selected_character}.")

        # --- 2. Call AI for Core JSON Structure (Base Generation) ---
        print(f"JM:  Calling AI for Base JSON structure for {selected_character}...")
        # Ensure ai_processor.generate_json_from_raw expects these args or adjust
        base_ai_result = ai_processor.generate_json_from_raw(
            google_api_key_jm, raw_content, selected_character, selected_model_name, JM_FINAL_JSON_SCHEMA_STRING
        )

        # --- 3. Process Base AI Result ---
        if not isinstance(base_ai_result, dict):
            error_message_details_jm = "JM: Base AI function returned unexpected data type."
            raw_response_on_error_jm = str(base_ai_result)
            raise TypeError(error_message_details_jm)

        if 'error' in base_ai_result:
            error_detail = base_ai_result.get('error', 'Unknown Base AI Error')
            details = base_ai_result.get('details', '')
            raw_response_on_error_jm = base_ai_result.get('raw_response')
            error_message_details_jm = f"JM: Base AI JSON generation failed ({selected_model_name}). Error: {error_detail}. Details: {details}"
            raise Exception(error_message_details_jm) # Let the main try-except catch this

        generated_data = base_ai_result
        print(f"JM:  Base AI returned parsable JSON data for {selected_character}.")

        # --- 4. Enforce Schema Keys on Generated Data ---
        print(f"JM:  Ensuring generated data for {selected_character} adheres to schema keys...")
        if JM_TOP_LEVEL_SCHEMA_PROPERTIES: # Check if schema structure is available
            # scraper_utils.ensure_schema_keys is not correct, it should be a local or imported utility
            # Assuming ensure_schema_keys is defined within this module or imported properly
            generated_data = scraper_utils.ensure_schema_keys(generated_data, JM_TOP_LEVEL_SCHEMA_PROPERTIES) # Corrected: use scraper_utils
            print(f"JM:  Generated data schema key enforcement complete for {selected_character}.")
        else:
             print(f"JM WARN: Top-level schema properties not available for {selected_character}, skipping key enforcement.")

        # --- 5. Initialize Final Data ---
        if old_json_data:
            final_json_data = copy.deepcopy(old_json_data)
            print(f"JM:  Initialized final data for {selected_character} from existing JSON.")
        else:
            final_json_data = generated_data
            print(f"JM:  Initialized final data for {selected_character} from new AI JSON.")

        # --- 6. Apply Name Correction ---
        proper_char_name_from_gen = generated_data.get("name", selected_character)
        original_casing_name = proper_char_name_from_gen # Update with AI's version
        # Apply specific casing rules
        if proper_char_name_from_gen == "HULK": original_casing_name = "Hulk"
        # ... (add other name corrections as before) ...
        elif proper_char_name_from_gen == "GROOT": original_casing_name = "Groot"
        elif proper_char_name_from_gen == "CLOAK & DAGGER": original_casing_name = "Cloak & Dagger"
        elif proper_char_name_from_gen == "PUNISHER": original_casing_name = "Punisher"
        elif proper_char_name_from_gen == "MISTER FANTASTIC": original_casing_name = "Mister Fantastic"

        final_json_data["name"] = original_casing_name
        print(f"JM:  Ensured final character name for {selected_character} is: '{original_casing_name}'")

        # --- 7. Merge CORE Generated Data into Final Data ---
        print(f"JM:  Merging core generated fields for {original_casing_name}...")
        core_merged_count = 0
        for key in JM_CORE_GENERATED_KEYS:
            if key in generated_data:
                # (Selective merge logic for stats, gameplay, lore_details as before)
                if key == "stats" and isinstance(generated_data[key], dict) and isinstance(final_json_data.get(key), dict):
                    # ... (stats merge) ...
                    final_stats = final_json_data[key]; gen_stats = generated_data[key]
                    for stat_key, stat_value in gen_stats.items():
                        if stat_key not in ["speed", "color_theme", "color_theme_secondary"] or stat_key not in final_stats: final_stats[stat_key] = stat_value
                    core_merged_count +=1
                elif key == "gameplay" and isinstance(generated_data[key], dict) and isinstance(final_json_data.get(key), dict):
                    # ... (gameplay merge with PRESERVED_NESTED_FIELDS check) ...
                    final_gameplay = final_json_data.setdefault(key, {}); gen_gameplay = generated_data[key]
                    for gameplay_key, gameplay_value in gen_gameplay.items():
                        if f"{key}.{gameplay_key}" not in JM_PRESERVED_NESTED_FIELDS: final_gameplay[gameplay_key] = gameplay_value
                    core_merged_count +=1
                elif key == "lore_details" and isinstance(generated_data[key], dict) and isinstance(final_json_data.get(key), dict):
                    # ... (lore_details merge with PRESERVED_NESTED_FIELDS check) ...
                    final_lore = final_json_data.setdefault(key, {}); gen_lore = generated_data[key]
                    for lore_key, lore_value in gen_lore.items():
                        if f"{key}.{lore_key}" not in JM_PRESERVED_NESTED_FIELDS: final_lore[lore_key] = lore_value
                    core_merged_count +=1
                elif key != "name": # Avoid overwriting already corrected name
                    final_json_data[key] = generated_data[key]
                    core_merged_count += 1
        print(f"JM:  Merged {core_merged_count} core generated sections/fields for {original_casing_name}.")

        # --- 8. Apply Patch Updates ---
        print(f"JM:  Attempting patch updates for {original_casing_name}...")
        patch_applied = False
        patch_file_path_jm = os.path.join(JM_INFO_OUTPUT_DIR, "balance_post.txt") # Use JM_ path
        if os.path.exists(patch_file_path_jm):
            try:
                with open(patch_file_path_jm, 'r', encoding='utf-8') as f_patch:
                    full_patch_text = f_patch.read()
                patch_section = scraper_utils.extract_patch_section(original_casing_name, full_patch_text) # Use scraper_utils
                if patch_section:
                    base_json_str_for_prompt = json.dumps(final_json_data, indent=2)
                    patch_update_result = ai_processor.interpret_patch_with_ai(
                        google_api_key_jm, base_json_str_for_prompt, patch_section, original_casing_name, selected_model_name
                    )
                    if isinstance(patch_update_result, dict) and 'error' not in patch_update_result:
                        if patch_update_result: # If not empty
                            final_json_data = scraper_utils.merge_updates(final_json_data, patch_update_result) # Use scraper_utils for merge
                            patch_applied = True
                            print(f"JM:  Patch updates successfully merged for {original_casing_name}.")
                        else: print(f"JM:  Patch AI indicated no changes for {original_casing_name}.")
                    elif isinstance(patch_update_result, dict): print(f"JM WARN: Patch AI failed for {original_casing_name}: {patch_update_result.get('error')}")
                    else: print(f"JM WARN: Patch AI returned unexpected data for {original_casing_name}.")
                else: print(f"JM:  No patch section found for {original_casing_name}.")
            except Exception as patch_e:
                print(f"JM ERROR reading/processing patch for {original_casing_name}: {patch_e}")
        else: print(f"JM WARN: Balance patch file not found at {patch_file_path_jm}. Skipping patch for {original_casing_name}.")

        # --- 9. Inject Static Data & Reddit Link ---
        print(f"JM:  Injecting static data for {original_casing_name}...")
        # Colors
        color_pool = character_color_pools_jm.get(original_casing_name, [])
        primary_color, secondary_color = None, None
        if color_pool and isinstance(color_pool, list):
            try:
                if len(color_pool) >= 2: primary_color, secondary_color = random.sample(color_pool, 2)
                elif len(color_pool) == 1: primary_color = secondary_color = color_pool[0]
            except ValueError: pass
        final_json_data.setdefault('stats', {})
        if final_json_data['stats'] is None: final_json_data['stats'] = {}
        final_json_data['stats']['color_theme'] = primary_color
        final_json_data['stats']['color_theme_secondary'] = secondary_color
        # Speed
        final_json_data['stats']['speed'] = JM_CHARACTER_BASE_SPEEDS.get(original_casing_name)
        # Reddit Link (ensure misc exists)
        final_json_data.setdefault("misc", {})
        if final_json_data['misc'] is None: final_json_data['misc'] = {}
        if scraper_utils.get_nested_value(final_json_data, "misc.community_buzz") is None: # Use scraper_utils
            char_name_for_link = final_json_data.get("name", original_casing_name)
            encoded_char_name = urllib.parse.quote_plus(f'"{char_name_for_link}"')
            reddit_url = f"https://www.reddit.com/r/marvelrivals/search/?q={encoded_char_name}&type=posts&t=month"
            scraper_utils.set_nested_value(final_json_data, "misc.community_buzz", reddit_url) # Use scraper_utils
            print(f"JM:    Generated Reddit search link for {original_casing_name}.")
        print(f"JM:  Static data injection complete for {original_casing_name}.")

        # --- 10. Final Preservation Pass ---
        if old_json_data:
            # ... (Preservation logic using JM_PRESERVED_NESTED_FIELDS and scraper_utils.get/set_nested_value)
            print(f"JM:  Final check/restore of preserved nested fields for {original_casing_name}...")
            nested_preserved_count = 0
            for field_path in JM_PRESERVED_NESTED_FIELDS:
                preserved_value = scraper_utils.get_nested_value(old_json_data, field_path)
                current_value = scraper_utils.get_nested_value(final_json_data, field_path)
                if preserved_value is not None and preserved_value != current_value:
                    if scraper_utils.set_nested_value(final_json_data, field_path, preserved_value):
                        nested_preserved_count +=1
            if nested_preserved_count > 0: print(f"JM:    Restored {nested_preserved_count} specific nested field(s) for {original_casing_name}.")


        # --- 11. Save Final JSON ---
        os.makedirs(JM_CHARACTER_JSON_OUTPUT_DIR, exist_ok=True)
        print(f"JM:  Saving final JSON for {original_casing_name} to: {os.path.basename(json_filepath)}")
        with open(json_filepath, 'w', encoding='utf-8') as f:
            json.dump(final_json_data, f, indent=2, ensure_ascii=False)
        success_msg = f"JM:  SUCCESS: Saved final JSON for {original_casing_name}.{' (Patch applied)' if patch_applied else ''}"
        print(success_msg)
        success = True
        # Update last update file (use config_manager)
        config_manager.update_last_update_file("last_json_gen", datetime.datetime.now().isoformat())
        return success, success_msg, original_casing_name, json_filepath

    except FileNotFoundError as fnf_e: # Specifically for raw file
        error_message_details_jm = f"JM ERROR: Raw Text file not found at: {raw_filepath}. Details: {fnf_e}"
        print(error_message_details_jm)
        return False, error_message_details_jm, original_casing_name, json_filepath
    except Exception as e:
        error_msg_exc = f"JM ERROR: Pipeline failed for {selected_character}: {e}" # Renamed
        print(error_msg_exc)
        if not error_message_details_jm: error_message_details_jm = str(e)
        import traceback; traceback.print_exc(file=sys.stderr)
        # Save error file if it was a Base AI failure
        if raw_response_on_error_jm and "Base AI Error" in (error_message_details_jm or ""):
            error_file_path = os.path.join(JM_FAILED_JSON_DIR, f"{json_filename_base}.json.api_error.txt")
            try:
                os.makedirs(JM_FAILED_JSON_DIR, exist_ok=True)
                if not os.path.exists(error_file_path):
                     with open(error_file_path, "w", encoding="utf-8") as err_f:
                         err_f.write(f"-- BASE AI Gen Error [{selected_model_name}] for {selected_character} --\n")
                         err_f.write(f"Error: {error_message_details_jm}\n")
                         err_f.write(f"-- Faulty Extracted String/Raw Response --\n{raw_response_on_error_jm}\n")
                     print(f"JM:    Saved base AI error details to: {error_file_path}")
            except Exception as file_e:
                 print(f"JM WARN: Failed saving base AI error file '{error_file_path}': {file_e}")
        return False, error_msg_exc, original_casing_name, json_filepath


# --- Orchestration for "Generate All JSON" ---
def process_all_characters_json_generation(
    google_api_key_jm,
    character_names_list,
    selected_model_name,
    stop_flag_event, # Pass the threading.Event for cancellation
    progress_callback_gui # Function from GUI to call for progress updates
    ):
    """
    Orchestrates JSON generation for a list of characters.
    This is the target function for the "Generate All JSON" thread.
    Returns (processed_count, success_count, error_count, was_stopped_flag)
    """
    if not character_names_list:
        print("JM: No characters provided for 'Generate All JSON'.")
        return 0, 0, 0, False

    total_files = len(character_names_list)
    print(f"JM: === Starting Generate ALL JSON ({total_files} files, Model: {selected_model_name}) ===")
    
    processed_count = 0
    success_count = 0
    error_count = 0
    
    # Ensure JM_RAW_TEXT_DIR is initialized
    if not JM_RAW_TEXT_DIR:
        print("JM CRITICAL ERROR: JM_RAW_TEXT_DIR not initialized in json_manager. Call init_json_manager_paths_and_config.")
        # Call progress_callback_gui with an error state if possible
        if progress_callback_gui and callable(progress_callback_gui):
            progress_callback_gui(0, total_files, "Error: Paths not set", is_final=True, errors=total_files)
        return 0, 0, total_files, False # Indicate all failed due to config error

    sorted_character_names = sorted(character_names_list)

    for i, character_name in enumerate(sorted_character_names):
        if stop_flag_event.is_set():
            print(f"JM: Generate All JSON cancelled by user before processing {character_name}.")
            break # Exit loop if stop flag is set

        if progress_callback_gui and callable(progress_callback_gui):
            progress_callback_gui(i, total_files, character_name)

        print(f"JM: --- Processing {i+1}/{total_files}: {character_name} ---")
        
        raw_filename_base = scraper_utils.sanitize_filename(character_name, extension="")
        if not raw_filename_base:
            print(f"JM ERROR: Sanitize Fail (Raw) for '{character_name}'. Skipping.")
            error_count += 1
            continue
        raw_filepath = os.path.join(JM_RAW_TEXT_DIR, f"{raw_filename_base}_raw.txt")

        if not os.path.exists(raw_filepath):
            print(f"JM SKIP: Raw text file not found for {character_name}: {os.path.basename(raw_filepath)}")
            # Not necessarily an error for "Generate All", just skipping this one
            continue 

        processed_count +=1 # Count as processed if raw file exists and we attempt it.

        # Call the single character processing function
        success_flag, message, _, _ = process_single_character_json(
            google_api_key_jm,
            character_name,
            raw_filepath,
            selected_model_name,
            # No inner progress callback needed here as we manage it per character
        )

        if success_flag:
            success_count += 1
        else:
            error_count += 1
            print(f"JM ERROR processing {character_name}: {message}") # Log the error message

        # API Call Delay if not stopping and not the last character
        if not stop_flag_event.is_set() and i < total_files - 1:
            # API_CALL_DELAY_SECONDS should be accessible, e.g., passed to init or defined in this module
            # For now, let's assume a default or it's passed via a config object later
            delay_seconds = 1.5 # Fallback, ideally from config
            if 'API_CALL_DELAY_SECONDS' in globals(): # Check if it was set by init
                delay_seconds = API_CALL_DELAY_SECONDS
            print(f"JM: --- Delaying {delay_seconds}s before next character ---")
            import time; time.sleep(delay_seconds)
            
    was_stopped = stop_flag_event.is_set()
    final_status_msg = f"Generate ALL {'STOPPED' if was_stopped else 'COMPLETE'}. Processed: {processed_count}. Success: {success_count}, Errors: {error_count}."
    print(f"JM: === {final_status_msg} ===")

    if progress_callback_gui and callable(progress_callback_gui):
        progress_callback_gui(total_files if not was_stopped else i, total_files, "Finished", is_final=True, errors=error_count, stopped=was_stopped)

    return processed_count, success_count, error_count, was_stopped


# --- Meta Stats Update Logic ---
def update_all_character_meta_stats(scraped_tracker_data, progress_callback_gui=None):
    """
    Updates the 'meta_stats' section in all character JSON files.
    Returns (processed, updated, errors)
    """
    print("JM: --- Updating JSON files with scraped Tracker data ---")
    if not scraped_tracker_data:
        print("JM: Skipping meta stats update: No tracker data provided.")
        return 0, 0, 0

    files_processed = 0; files_updated = 0; update_errors = 0
    files_in_dir = []
    try:
        if not JM_CHARACTER_JSON_OUTPUT_DIR: raise ValueError("JM_CHARACTER_JSON_OUTPUT_DIR not initialized.")
        files_in_dir = [f for f in os.listdir(JM_CHARACTER_JSON_OUTPUT_DIR)
                        if f.lower().endswith('.json') and os.path.isfile(os.path.join(JM_CHARACTER_JSON_OUTPUT_DIR, f))]
    except Exception as e:
        print(f"JM ERROR: Cannot list files in {JM_CHARACTER_JSON_OUTPUT_DIR}: {e}")
        return 0, 0, 1

    total_files = len(files_in_dir)
    print(f"JM:  Found {total_files} JSON files to check for meta stats update.")
    tracker_names_lower = {name.lower(): name for name in scraped_tracker_data.keys()}

    for i, filename in enumerate(files_in_dir):
        if progress_callback_gui and callable(progress_callback_gui):
            progress_callback_gui(i, total_files, filename)

        filepath = os.path.join(JM_CHARACTER_JSON_OUTPUT_DIR, filename)
        files_processed += 1
        try:
            with open(filepath, 'r', encoding='utf-8') as f: char_data = json.load(f)
            json_char_name = char_data.get("name")
            if not json_char_name:
                print(f"JM WARN: Skipping '{filename}': Missing 'name' field."); update_errors += 1; continue

            matched_tracker_name = None
            local_name_lower = scraper_utils.normalize_for_comparison(json_char_name) # Use normalize

            if local_name_lower in tracker_names_lower:
                matched_tracker_name = tracker_names_lower[local_name_lower]
            # Add more sophisticated matching if needed, e.g., checking variations
            # For now, direct normalized match.

            if matched_tracker_name:
                tracker_stats = scraped_tracker_data.get(matched_tracker_name)
                if tracker_stats:
                    char_data.setdefault("meta_stats", {})
                    if not isinstance(char_data["meta_stats"], dict):
                        char_data["meta_stats"] = {} # Reset if not a dict
                    
                    # Assuming meta_stats schema keys are: tier, win_rate, wr_change, pick_rate, pr_change, ban_rate, matches
                    # And tracker_stats keys are the same.
                    # If there's a schema definition for meta_stats, use it.
                    # For now, direct update.
                    # Example: char_data["meta_stats"] = tracker_stats # Complete overwrite
                    # Or selective update:
                    changes_made = False
                    for key, value in tracker_stats.items():
                        if char_data["meta_stats"].get(key) != value : # Update only if different
                            char_data["meta_stats"][key] = value
                            changes_made = True
                    
                    if changes_made:
                        with open(filepath, 'w', encoding='utf-8') as f_out:
                            json.dump(char_data, f_out, indent=2, ensure_ascii=False)
                        files_updated += 1
                # else: print(f"JM INFO: Matched name '{matched_tracker_name}' but no stats object.")
            # else: print(f"JM INFO: No matching tracker stats for '{json_char_name}' ('{filename}').")
        except json.JSONDecodeError: print(f"JM ERROR: Invalid JSON in '{filename}'."); update_errors += 1
        except Exception as e: print(f"JM ERROR: Failed to process '{filename}' for meta stats: {e}"); update_errors += 1
    
    print(f"JM: --- Finished meta stats update. Processed: {files_processed}, Updated: {files_updated}, Errors: {update_errors} ---")
    if progress_callback_gui and callable(progress_callback_gui):
        progress_callback_gui(total_files, total_files, "Meta Stats Update Finished", is_final=True, errors=update_errors)
    return files_processed, files_updated, update_errors


# --- Team-Up Update Logic ---
def update_all_characters_with_teamups(parsed_wiki_teamups, active_char_list_raw, progress_callback_gui=None):
    """
    Updates the 'teamups' section in all character JSON files based on parsed wiki data.
    Returns (processed, updated, errors)
    """
    print("JM: --- Updating JSON files with Team-Up data ---")
    if not parsed_wiki_teamups:
        print("JM: Skipping team-up update: No parsed team-up data provided.")
        return 0, 0, 0
    if not active_char_list_raw:
        print("JM ERROR: Active character list not provided for team-up update.")
        return 0,0,1

    files_processed = 0; files_updated = 0; update_errors = 0
    
    # Normalize active character list once for matching participant names
    # This assumes normalize_for_comparison is available (e.g., in scraper_utils)
    normalized_active_json_names = {scraper_utils.normalize_for_comparison(name): name for name in active_char_list_raw}

    all_json_files = []
    try:
        if not JM_CHARACTER_JSON_OUTPUT_DIR: raise ValueError("JM_CHARACTER_JSON_OUTPUT_DIR not initialized.")
        all_json_files = [f for f in os.listdir(JM_CHARACTER_JSON_OUTPUT_DIR)
                          if f.lower().endswith('.json') and os.path.isfile(os.path.join(JM_CHARACTER_JSON_OUTPUT_DIR, f))]
    except Exception as e:
        print(f"JM ERROR: Cannot list character JSON files: {e}")
        return 0,0,1
    
    total_files_to_check = len(all_json_files)

    for i, filename in enumerate(all_json_files):
        if progress_callback_gui and callable(progress_callback_gui):
            progress_callback_gui(i, total_files_to_check, filename)
        
        filepath = os.path.join(JM_CHARACTER_JSON_OUTPUT_DIR, filename)
        files_processed += 1
        try:
            with open(filepath, 'r', encoding='utf-8') as f_json: char_data = json.load(f_json)
            
            json_internal_name_raw = char_data.get("name")
            if not json_internal_name_raw:
                print(f"JM WARN: Skipping '{filename}' for teamups: Missing 'name' field."); update_errors += 1; continue
            
            normalized_json_char_name = scraper_utils.normalize_for_comparison(json_internal_name_raw)
            if not normalized_json_char_name:
                print(f"JM WARN: Skipping '{filename}' for teamups: Could not normalize name '{json_internal_name_raw}'."); update_errors += 1; continue

            character_specific_teamups_for_json = []
            for wiki_teamup_data in parsed_wiki_teamups:
                teamup_name = wiki_teamup_data.get("name")
                participants = wiki_teamup_data.get("participants", [])
                if not teamup_name or not participants: continue

                my_participant_data = None; partners = []
                is_this_char_in_teamup = False
                for p_data in participants:
                    hero_name_wiki_raw = p_data.get("hero") # This is already original casing from parser
                    if hero_name_wiki_raw:
                        # Match based on the name stored in the JSON file
                        if scraper_utils.normalize_for_comparison(hero_name_wiki_raw) == normalized_json_char_name:
                            my_participant_data = p_data
                            is_this_char_in_teamup = True
                        else: # This is a partner
                            # Ensure partner name is one of the known active characters for consistency
                            norm_partner_wiki = scraper_utils.normalize_for_comparison(hero_name_wiki_raw)
                            if norm_partner_wiki in normalized_active_json_names:
                                partners.append(normalized_active_json_names[norm_partner_wiki]) # Store original casing
                            # else: print(f"JM Debug: Teamup partner '{hero_name_wiki_raw}' not in active list, not adding.")


                if is_this_char_in_teamup and my_participant_data:
                    json_teamup_entry = {"name": teamup_name}
                    json_teamup_entry["partner"] = sorted(list(set(partners))) if partners else None # Unique sorted partners
                    
                    effect_desc = my_participant_data.get("description")
                    json_teamup_entry["effect"] = effect_desc if (effect_desc and effect_desc not in ["(No description text)", "(See Stats/Special Effect)"]) else None
                    
                    participant_stats = {k.lower().replace(' ', '_'): v for k, v in my_participant_data.get("stats", {}).items()}
                    json_teamup_entry["keybind"] = participant_stats.get("key") # Assumes key is "Key" or "key"
                    json_teamup_entry["teamup_bonus"] = participant_stats.get("team_up_bonus")
                    json_teamup_entry["duration"] = participant_stats.get("duration")
                    json_teamup_entry["cooldown"] = participant_stats.get("cooldown")
                    json_teamup_entry["range_target"] = participant_stats.get("range") or participant_stats.get("prompt_range")

                    special_notes_parts = []
                    if my_participant_data.get("is_anchor"): special_notes_parts.append("Role: Anchor")
                    participant_ability_name = my_participant_data.get("ability_name")
                    if participant_ability_name: special_notes_parts.append(f"Ability: {participant_ability_name}")
                    json_teamup_entry["special_notes"] = " | ".join(special_notes_parts) if special_notes_parts else None
                    
                    # Store remaining stats in 'details'
                    explicit_keys_handled = {"key", "team_up_bonus", "duration", "cooldown", "range", "prompt_range"}
                    remaining_stats_lines = []
                    for stat_key, stat_value in participant_stats.items():
                        if stat_key not in explicit_keys_handled:
                            display_key = stat_key.replace('_', ' ').title()
                            remaining_stats_lines.append(f"{display_key}: {stat_value}")
                    json_teamup_entry["details"] = "<br/>".join(remaining_stats_lines) if remaining_stats_lines else None
                    
                    character_specific_teamups_for_json.append(json_teamup_entry)

            character_specific_teamups_for_json.sort(key=lambda x: x.get("name", ""))
            
            # Compare with existing teamups to see if an update is needed
            current_teamups_list = char_data.get("teamups", [])
            # Simplified comparison: convert both to sorted JSON strings
            try:
                current_teamups_str = json.dumps(sorted([t for t in current_teamups_list if isinstance(t, dict)], key=lambda x: x.get("name","")), sort_keys=True)
                new_teamups_str = json.dumps(character_specific_teamups_for_json, sort_keys=True) # Already sorted by name
            except Exception as dump_err:
                print(f"JM WARN: Error serializing teamups for comparison in {filename}: {dump_err}. Forcing update.")
                current_teamups_str = f"Error_{random.randint(1000,9999)}" # Force mismatch
                new_teamups_str = ""


            if current_teamups_str != new_teamups_str:
                print(f"JM:  Updating teamups for: {json_internal_name_raw} in '{filename}'")
                char_data["teamups"] = character_specific_teamups_for_json
                with open(filepath, 'w', encoding='utf-8') as f_out:
                    json.dump(char_data, f_out, indent=2, ensure_ascii=False)
                files_updated += 1
            # else: print(f"JM:  No teamup changes for: {json_internal_name_raw}")

        except json.JSONDecodeError: print(f"JM ERROR: Invalid JSON in '{filename}'."); update_errors += 1
        except Exception as e: print(f"JM ERROR: Failed to process '{filename}' for teamups: {e}"); update_errors += 1

    print(f"JM: --- Finished Team-Up update. Processed: {files_processed}, Updated: {files_updated}, Errors: {update_errors} ---")
    if progress_callback_gui and callable(progress_callback_gui):
        progress_callback_gui(total_files_to_check, total_files_to_check, "Team-Up Update Finished", is_final=True, errors=update_errors)
    return files_processed, files_updated, update_errors


if __name__ == '__main__':
    print("Testing json_manager.py (requires other modules and config)...")
    # This module is harder to test standalone as it depends on initialized paths
    # and other modules. Basic structure check.
    print("json_manager.py basic load complete.")