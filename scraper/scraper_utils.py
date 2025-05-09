# File: scraper_utils.py
import requests
from bs4 import BeautifulSoup, Tag, NavigableString
import re
import os
import time
import datetime
import urllib.parse
import sys # For sys.modules check in parse_teamup_stats_from_small_tag
import functools # For get_nested_value
import random  # <-- Add this import for sanitize_filename

# --- Constants that might be needed by this module ---
USER_AGENT = 'RivalsUpdater/3.0 (Modular; Learning Project)'
TEAMUP_WIKI_URL_SU = "https://marvelrivals.fandom.com/wiki/Team-Ups"

# ==============================================================================
# == TEXT & DATA UTILITY FUNCTIONS (Moved from main script) ==
# ==============================================================================

def sanitize_filename(name, extension=".txt"): # Already here, ensure it's the latest version
    if not name or not isinstance(name, str):
        result = f"invalid_character_name_{random.randint(1000,9999)}{extension}"
        print(f"SU WARN: sanitize_filename received invalid input '{name}'. Placeholder: '{result}'")
        return result
    original_name = name
    name = name.replace('&', 'and').replace(':', '-').replace('/', '-').replace('\\', '-')
    name = name.replace('*', '-').replace('?', '').replace('"', '').replace('<', '').replace('>', '').replace('|', '')
    name = re.sub(r'\s+', '_', name)
    name = name.strip('._ ')
    if not name:
        result = f"invalid_character_name_{random.randint(1000,9999)}{extension}"
        print(f"SU WARN: sanitize_filename for '{original_name}' became empty. Placeholder: '{result}'")
        return result
    else:
        result = f"{name}{extension}"
        return result

def normalize_for_comparison(name):
    """Normalizes a name for comparison against filename-derived list."""
    if not name or not isinstance(name, str): return ""
    norm_name = name.lower()
    if norm_name == "the punisher": norm_name = "punisher"
    if norm_name == "mr. fantastic": norm_name = "mister_fantastic"
    norm_name = norm_name.replace(' & ', '_and_').replace('&', '_and_').replace('-', '_')
    norm_name = norm_name.replace(' ', '_')
    if norm_name.startswith("the_"): norm_name = norm_name[4:]
    norm_name = norm_name.replace("'", "").replace(".", "")
    norm_name = norm_name.strip('_')
    return norm_name

def get_nested_value(data, key_path, default=None):
    """Safely gets a value from a nested dict using dot notation."""
    if not isinstance(data, dict) or not isinstance(key_path, str) or not key_path: return default
    keys = key_path.split('.')
    try:
        value = functools.reduce(lambda d, key: d.get(key) if isinstance(d, dict) else None, keys, data)
        return value if value is not None else default
    except TypeError: return default
    except Exception: return default

def set_nested_value(data, key_path, value):
    """Safely sets a value in a nested dict using dot notation, creating keys if needed."""
    if not isinstance(data, dict) or not isinstance(key_path, str) or not key_path:
        print(f"SU WARN (set_nested_value): Invalid input data type ({type(data)}) or key_path ('{key_path}').")
        return False
    keys = key_path.split('.')
    d = data
    try:
        for i, key_segment in enumerate(keys[:-1]): # Changed key to key_segment to avoid clash
            if key_segment not in d or not isinstance(d.get(key_segment), dict):
                d[key_segment] = {}
            d = d[key_segment]
        if keys:
            final_key = keys[-1]
            d[final_key] = value
            return True
        else:
            print(f"SU WARN (set_nested_value): key_path ('{key_path}') resulted in empty keys list.")
            return False
    except TypeError as e:
        print(f"SU ERROR (set_nested_value): TypeError setting '{key_path}'. Path conflict? Details: {e}")
        return False
    except Exception as e:
        print(f"SU ERROR (set_nested_value): Unexpected error setting '{key_path}': {e}")
        return False

def ensure_schema_keys(data_node, schema_properties_arg): # Renamed schema_properties
    """
    Recursively ensures that keys defined in schema_properties_arg exist in data_node.
    Adds missing keys with default values (None, [], {}).
    """
    if not isinstance(data_node, dict): return data_node
    if not isinstance(schema_properties_arg, dict): return data_node

    for key, prop_schema in schema_properties_arg.items():
        expected_type = prop_schema.get("type")
        if key not in data_node:
            default_value = None
            if expected_type == "array": default_value = []
            elif expected_type == "object": default_value = {}
            data_node[key] = default_value
            # print(f"SU:    Added missing key: '{key}' with default: {default_value}") # Verbose
            if expected_type == "object" and "properties" in prop_schema and isinstance(default_value, dict):
                 ensure_schema_keys(default_value, prop_schema["properties"]) # Recursive call
        else: # Key exists
            current_value = data_node[key]
            if expected_type == "object" and "properties" in prop_schema and isinstance(current_value, dict):
                ensure_schema_keys(current_value, prop_schema["properties"]) # Recursive call
            elif expected_type == "array" and "items" in prop_schema and isinstance(current_value, list):
                item_schema = prop_schema.get("items", {})
                item_props = item_schema.get("properties")
                if item_props and item_schema.get("type") == "object":
                     for item in current_value:
                         if isinstance(item, dict):
                             ensure_schema_keys(item, item_props) # Recursive call
    return data_node

def merge_updates(base_dict, updates_dict):
    """
    Recursively merges updates from updates_dict into base_dict.
    Handles nested dictionaries and updates items in 'abilities' list by name.
    """
    if not isinstance(base_dict, dict) or not isinstance(updates_dict, dict):
        print(f"SU WARN (merge_updates): Invalid input types. Skipping merge.")
        return base_dict
    if not updates_dict: return base_dict # No updates to apply
    # print(f"SU:    Merge: Applying updates: {list(updates_dict.keys())}") # Verbose

    for key, value in updates_dict.items():
        if key == "abilities" and isinstance(value, list) and \
           key in base_dict and isinstance(base_dict[key], list):
            # print(f"SU:      Merging '{key}' list...") # Verbose
            base_abilities = base_dict[key]; updates_abilities = value
            for update_ability in updates_abilities:
                if not isinstance(update_ability, dict): continue
                update_name = update_ability.get("name")
                if not update_name: continue
                found_base_ability = next((ba for ba in base_abilities if isinstance(ba, dict) and ba.get("name") == update_name), None)
                if found_base_ability: merge_updates(found_base_ability, update_ability) # Recursive
                # else: print(f"SU WARN: Ability '{update_name}' from patch not in base. Not adding.") # Decide if to add new
        elif key in base_dict and isinstance(base_dict[key], dict) and isinstance(value, dict):
            merge_updates(base_dict[key], value) # Recursive
        else: # Overwrite or add
            base_dict[key] = value
    return base_dict

def extract_patch_section(character_name, full_patch_text):
    """
    Extracts the relevant section for a character from the full balance patch text.
    """
    if not character_name or not full_patch_text: return None
    safe_char_name = re.escape(character_name)
    pattern = re.compile(
        r"^(?:#{2,3}\s*)?" + safe_char_name + r"\s*?\n(.*?)(?=\n^#{2,3}\s*\w|\Z)",
        re.IGNORECASE | re.MULTILINE | re.DOTALL
    )
    match = pattern.search(full_patch_text)
    if match:
        section = match.group(1).strip()
        # print(f"SU:    Found patch section for '{character_name}'. Length: {len(section)}") # Verbose
        return section
    # else: print(f"SU:    No patch section found for '{character_name}'.") # Verbose
    return None


# ==============================================================================
# == WEB SCRAPING FUNCTIONS ==
# ==============================================================================

# --- Generic Web Page Fetcher ---
def fetch_page_content(url, user_agent=USER_AGENT, timeout=15):
    # ... (definition as provided in previous step)
    print(f"SU: Fetching: {url[:80]}...")
    headers = {'User-Agent': user_agent}
    try:
        response = requests.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()
        print(f"SU: Successfully fetched {url[:80]}. Status: {response.status_code}")
        return response.text
    except requests.exceptions.Timeout:
        print(f"SU ERROR: Request timed out for {url}")
    except requests.exceptions.HTTPError as e:
        print(f"SU ERROR: HTTP Error {e.response.status_code} for {url}: {e.response.reason}")
    except requests.exceptions.RequestException as e:
        print(f"SU ERROR: Request failed for {url}: {e}")
    except Exception as e:
        print(f"SU ERROR: Unexpected error fetching {url}: {e}")
    return None

# --- Wiki Content Scraping ---
def scrape_wiki_content_from_html(html_content, url_for_log="Unknown URL"):
    # ... (definition as provided in previous step)
    if not html_content: return None
    soup = BeautifulSoup(html_content, 'html.parser')
    raw_text = ""
    content_area = soup.find('div', class_='mw-parser-output') or \
                   soup.find('div', id='mw-content-text') or \
                   soup.find('main', id='content') or \
                   soup.find('div', id='bodyContent') or \
                   soup.find('article')
    extract_method = "Unknown"
    if content_area:
        extract_method = "Targeted Content Area"
        for tag_type_info in [
            (['div', 'table'], r'navbox|sidebar|infobox|metadata|ambox|toccolours', ['toc']),
            (['span'], r'mw-editsection', []),
            (['ul'], r'gallery', []),
            (['div', 'aside'], r'related|community|advert|promo|recommend|noprint|printfooter', [])
        ]:
            tag_names, classes_re_str, ids_to_remove = tag_type_info
            for tag_name in tag_names:
                if classes_re_str:
                    for tag in content_area.find_all(tag_name, class_=re.compile(classes_re_str, re.I)):
                        tag.decompose()
                if ids_to_remove:
                    for an_id in ids_to_remove:
                        for tag_with_id in content_area.find_all(tag_name, id=an_id):
                            tag_with_id.decompose()
        for s_tag in content_area.find_all(['script', 'style']): s_tag.decompose()
        raw_text = content_area.get_text(separator='\n', strip=True)
    # ... (fallback logic as before) ...
    else: # Fallbacks
        body = soup.find('body')
        if body:
            extract_method = "Body Fallback"
            for s_tag in body.find_all(['script', 'style']): s_tag.decompose()
            raw_text = body.get_text(separator='\n', strip=True)
        else:
            extract_method = "Page Fallback"
            for s_tag in soup.find_all(['script', 'style']): s_tag.decompose()
            raw_text = soup.get_text(separator='\n', strip=True)
            print(f"SU WARN: Could not find main content/body for {url_for_log}. Using {extract_method}.")

    if raw_text:
        raw_text = re.sub(r'\s*\[\s*edit\s*\]\s*', '', raw_text, flags=re.IGNORECASE)
        raw_text = re.sub(r'\n{3,}', '\n\n', raw_text).strip()
        # print(f"SU: Extracted text from {url_for_log} using '{extract_method}'. Len: {len(raw_text)}") # Verbose
        return raw_text
    else:
        print(f"SU WARN: No text extracted from {url_for_log} using '{extract_method}'.")
        return None


def scrape_single_wiki_page_to_file(url, filepath, append_mode=False, source_url_for_header=""):
    # ... (definition as provided in previous step)
    html_content = fetch_page_content(url)
    if not html_content: return False
    cleaned_text = scrape_wiki_content_from_html(html_content, url_for_log=url)
    if not cleaned_text: return False
    try:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        file_mode = 'a' if append_mode else 'w'
        with open(filepath, file_mode, encoding='utf-8') as f:
            if append_mode and source_url_for_header:
                f.write("\n\n" + "="*20 + f" APPENDED CONTENT FROM: {source_url_for_header} " + "="*20 + "\n\n")
            elif not append_mode and source_url_for_header :
                f.write(f"===== CONTENT FROM: {source_url_for_header} =====\n\n")
            f.write(cleaned_text)
        print(f"SU: Success - Saved to: {os.path.basename(filepath)}")
        return True
    except Exception as e:
        print(f"SU ERROR: Failed to write to file {filepath}: {e}")
        return False


# --- Official Site News/Info Scraping ---
def scrape_official_site_article_content(article_url):
    # ... (definition as provided in previous step)
    print(f"SU: Scraping Official Article: {article_url}")
    html_content = fetch_page_content(article_url)
    if not html_content: return f"Failed to scrape content from: {article_url}\n"
    soup = BeautifulSoup(html_content, 'html.parser')
    article_body = soup.find('div', class_='art-inner-content')
    content_text = ""
    if article_body:
        content_text = article_body.get_text(separator='\n', strip=True)
        content_text = re.sub(r'\n{3,}', '\n\n', content_text).strip()
        footer_pattern = r"For more information about us, check out and follow our other social channels\.\s+Discord(\s*\|\s*\w+)*\s*$"
        cleaned_text = re.sub(footer_pattern, '', content_text, flags=re.IGNORECASE | re.MULTILINE).strip()
        if len(cleaned_text) < len(content_text):
            content_text = cleaned_text
        if not content_text: content_text = "(Article body found but contained no text after cleanup)\n"
    else: content_text = "(Could not find main article content element on page)\n"
    return content_text

def update_all_info_files_su(info_output_dir_path, info_categories_dict, max_articles_per_category, progress_callback_gui=None):
    """
    Loops through defined categories, scrapes, and updates their respective info files.
    INFO_CATEGORIES is passed as an argument.
    """
    print("SU: --- Updating Info Files from Official Site ---")
    success_count = 0
    error_count = 0
    total_categories = len(info_categories_dict)

    if not os.path.isdir(info_output_dir_path):
        print(f"SU ERROR: Info output directory does not exist: {info_output_dir_path}")
        try:
            os.makedirs(info_output_dir_path, exist_ok=True)
            print(f"SU: Created info output directory: {info_output_dir_path}")
        except Exception as e_mkdir:
            print(f"SU CRITICAL ERROR: Could not create info output directory {info_output_dir_path}: {e_mkdir}")
            if progress_callback_gui and callable(progress_callback_gui):
                progress_callback_gui(0, total_categories, "Error: Info dir missing", is_final=True, errors=total_categories)
            return 0, 0, total_categories

    for i, (category_key, (filename, url)) in enumerate(info_categories_dict.items()):
        if progress_callback_gui and callable(progress_callback_gui):
            progress_callback_gui(i, total_categories, category_key)

        if not url:
            print(f"SU:  Skipping category '{category_key}' (no URL defined).")
            continue

        output_path = os.path.join(info_output_dir_path, filename)
        if _scrape_single_category_info_file_su(category_key, url, output_path, max_articles_per_category):
            success_count += 1
        else:
            error_count += 1
        # Optionally: time.sleep(0.5)

    final_msg = f"SU: --- Finished Updating Info Files. Successful: {success_count}/{total_categories}, Errors: {error_count} ---"
    print(final_msg)
    if progress_callback_gui and callable(progress_callback_gui):
        progress_callback_gui(total_categories, total_categories, "Info File Update Finished", is_final=True, errors=error_count)
    return total_categories, success_count, error_count

def _scrape_single_category_info_file_su(category_name, category_url, output_filepath, max_articles):
    """
    Internal helper to scrape and save info for a single category.
    """
    print(f"SU:  Scraping Category Index: {category_name} from {category_url}")
    combined_content = f"# {category_name} - Recent Posts (Fetched {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')})\n\n"
    any_article_scraped_successfully = False

    category_html = fetch_page_content(category_url)
    if not category_html:
        combined_content += f"Error: Could not fetch index page for {category_name}.\n"
    else:
        index_soup = BeautifulSoup(category_html, 'html.parser')
        container = index_soup.select_one('div.cont-box')
        if not container:
            print(f"SU ERROR: Could not find container 'div.cont-box' for {category_name}.")
            combined_content += "Error: Could not find article container on index page.\n"
        else:
            article_links = container.select('a.list-item')
            if not article_links:
                print(f"SU WARN: No articles ('a.list-item') found for {category_name}.")
                combined_content += "(No articles found on index page)\n"
            else:
                print(f"SU:    Found {len(article_links)} links for {category_name}. Scraping top {max_articles}...")
                article_count = 0
                for link_tag in article_links[:max_articles]:
                    article_url_path = link_tag.get('href')
                    if not article_url_path: continue
                    article_full_url = urllib.parse.urljoin(category_url, article_url_path)
                    title_tag = link_tag.select_one('h2')
                    title = title_tag.text.strip() if title_tag else f"Article {article_count + 1}"
                    article_text = scrape_official_site_article_content(article_full_url)
                    combined_content += f"## {title}\n\n{article_text}\n\nSource URL: {article_full_url}\n---\n\n"
                    any_article_scraped_successfully = True
                    article_count += 1
                    time.sleep(0.3)
                if not any_article_scraped_successfully and article_links:
                    combined_content += "(Could not process any article links found)\n"
    try:
        with open(output_filepath, 'w', encoding='utf-8') as f:
            f.write(combined_content.strip())
        print(f"SU:    Saved combined content for {category_name} to: {os.path.basename(output_filepath)}")
        return True
    except Exception as e:
        print(f"SU ERROR: Failed to write info file {output_filepath}: {e}")
        return False


# --- RivalsTracker.com Scraping ---
def scrape_all_rivalstracker_heroes(tracker_url="https://rivalstracker.com/heroes"):
    # ... (definition as provided in previous step)
    print(f"SU: Scraping ALL hero stats from: {tracker_url}")
    html_content = fetch_page_content(tracker_url, timeout=20)
    if not html_content: return None
    scraped_data = {}; soup = BeautifulSoup(html_content, 'html.parser')
    table_body = soup.select_one('table tbody'); rows = []
    if not table_body:
        table = soup.find('table')
        if table: rows = table.find_all('tr')
        if rows and rows[0].find_all('th'): rows = rows[1:]
        else: print("SU ERROR (Tracker): Could not find table element."); return None
    else: rows = table_body.find_all('tr')
    if not rows: print("SU ERROR (Tracker): No data rows found."); return None
    expected_cells = 8; processed_count = 0
    for row in rows:
        cells = row.find_all('td')
        if len(cells) < expected_cells: continue
        hero_name_tracker = None; name_cell = cells[0]
        if name_cell:
            name_container = name_cell.select_one('a, div, span')
            if name_container: hero_name_tracker = name_container.text.strip()
            else: hero_name_tracker = name_cell.text.strip()
        if not hero_name_tracker: continue
        try:
            stats = { "tier": cells[1].get_text(strip=True) or None, "win_rate": cells[2].get_text(strip=True) or None,
                      "wr_change": cells[3].get_text(strip=True) or None, "pick_rate": cells[4].get_text(strip=True) or None,
                      "pr_change": cells[5].get_text(strip=True) or None, "ban_rate": cells[6].get_text(strip=True) or None,
                      "matches": cells[7].get_text(strip=True) or None }
            scraped_data[hero_name_tracker] = stats; processed_count += 1
        except Exception as cell_e: print(f"SU WARN (Tracker): Error parsing cells for '{hero_name_tracker}': {cell_e}")
    if not scraped_data: print("SU ERROR (Tracker): Failed to extract any hero stats."); return None
    print(f"SU: Scraped stats for {processed_count} heroes from tracker.")
    return scraped_data


# --- Team-Up Wiki Parsing Functions ---
def fetch_teamup_wiki_page_su(url=TEAMUP_WIKI_URL_SU):
    return fetch_page_content(url)

def parse_teamup_stats_from_small_tag_su(small_tag):
    # ... (definition as provided in previous step, ensure it uses BeautifulSoup, Tag, NavigableString)
    stats = {}
    if not small_tag: return stats
    parser_type = 'lxml' if 'lxml' in sys.modules else 'html.parser'
    temp_tag = BeautifulSoup(str(small_tag), parser_type).find('small')
    if not temp_tag: return stats
    current_key = None; current_value_parts = []
    for element in temp_tag.contents:
        if isinstance(element, Tag):
            if element.name == 'b':
                if current_key and current_value_parts: stats[current_key] = " ".join(current_value_parts).strip()
                key_text = element.get_text(strip=True)
                if key_text.endswith(':'): key_text = key_text[:-1].strip()
                current_key = key_text.upper().replace(' ', '_').replace('-', '_').replace('(', '').replace(')', '') if key_text else None
                current_value_parts = []
            elif element.name == 'br':
                 if current_key and current_value_parts and len(current_value_parts) > 0 and not current_value_parts[-1].endswith(' '):
                      current_value_parts.append(' ')
            elif current_key:
                 value_text = element.get_text(strip=True)
                 if value_text: current_value_parts.append(value_text)
        elif isinstance(element, NavigableString):
            text = element.strip()
            if text:
                 if text.startswith(':'): text = text[1:].strip()
                 if current_key and text: current_value_parts.append(text)
    if current_key and current_value_parts: stats[current_key] = " ".join(current_value_parts).strip()
    stats = {k: v for k, v in stats.items() if k and v}
    return stats


def extract_teamup_lore_quote_su(start_element, stop_element):
    # ... (definition as provided in previous step, ensure it uses BeautifulSoup, Tag, NavigableString)
    lore_parts = []; quote_parts = []; current = start_element.find_next_sibling()
    while current and current != stop_element:
        if isinstance(current, Tag):
            if current.name in ['h2', 'h3', 'h4']: break
            if current.name == 'table' and 'article-table' in current.get('class',[]): break
            if current.name == 'p':
                 next_bold = current.find('b', recursive=False); next_big = current.select_one('big > b > u')
                 if (next_bold and re.match(r"(.+?)\s*-\s*(.+?)\s*\((.+?)\)", next_bold.get_text(strip=True), re.IGNORECASE)) or next_big:
                     break
        if isinstance(current, Tag) and current.name == 'p':
            italic_tag = current.find('i')
            text_content = current.get_text(strip=True)
            if italic_tag:
                 italic_text = italic_tag.get_text(strip=True)
                 if '"' in italic_text or 'JOURNAL:' in italic_text.upper() or (':' in italic_text and len(italic_text.split(':')) == 2):
                      quote_parts.append(italic_text)
                 elif text_content: lore_parts.append(text_content)
            elif text_content: lore_parts.append(text_content)
        current = current.find_next_sibling()
    lore = "\n".join(p for p in lore_parts if p).strip(); quote = "\n".join(p for p in quote_parts if p).strip();
    return lore, quote

def parse_active_teamups_from_html_su(html_content, active_character_list_for_norm_tuple):
    # ... (definition as provided in previous step, using active_character_list_for_norm_tuple)
    # ... Ensure it calls the _su suffixed helper functions defined above.
    if not html_content: return []
    
    # Expecting a tuple: (set_of_normalized_names, map_of_norm_to_original)
    if not isinstance(active_character_list_for_norm_tuple, tuple) or len(active_character_list_for_norm_tuple) != 2:
        print("SU ERROR (Team-Up Parser): active_character_list_for_norm_tuple is invalid format.")
        return []
    normalized_active_set, normalized_to_original_map_su = active_character_list_for_norm_tuple

    if not normalized_active_set or not normalized_to_original_map_su:
        print("SU ERROR (Team-Up Parser): Normalized character data missing for validation.")
        return []

    print("SU: Parsing HTML for Active Team-Ups...")
    soup = BeautifulSoup(html_content, 'html.parser')
    active_teamups = []
    content_area = soup.select_one('div.mw-parser-output')
    if not content_area: print("SU ERROR (Team-Up Parser): No 'div.mw-parser-output'."); return []

    retired_marker = content_area.find('span', id='Retired_Team-Ups') # etc. for markers
    retired_heading_marker = None
    if retired_marker:
        current = retired_marker.parent
        while current and current.name != 'h3': current = current.parent
        if current and current.name == 'h3': retired_heading_marker = current

    timeline_marker = content_area.find('span', id='Timeline_of_Team-Up_Changes')
    timeline_heading_marker = None
    if timeline_marker:
        current = timeline_marker.parent
        while current and current.name != 'h2': current = current.parent
        if current and current.name == 'h2': timeline_heading_marker = current
        
    all_headings = content_area.find_all(['h2', 'h3'])
    active_teamup_found_flag = False

    for heading_tag in all_headings:
        if heading_tag.name != 'h2':
            if heading_tag == retired_heading_marker or heading_tag == timeline_heading_marker: break
            continue
        if heading_tag == retired_heading_marker or heading_tag == timeline_heading_marker: break

        teamup_name_tag = heading_tag.select_one('.mw-headline')
        teamup_name = teamup_name_tag.get_text(strip=True) if teamup_name_tag else heading_tag.get_text(strip=True)
        if any(kw in teamup_name for kw in ["Retired Team-Ups", "Timeline of Team-Up Changes", "References", "Contents"]):
            continue

        teamup_table = None
        next_boundary_heading = heading_tag.find_next(['h2', 'h3'])
        stop_nodes = {next_boundary_heading, retired_heading_marker, timeline_heading_marker}; stop_nodes.discard(None)
        current_node = heading_tag.find_next_sibling()
        while current_node:
            if current_node in stop_nodes: break
            if isinstance(current_node, Tag) and current_node.name == 'table' and 'article-table' in current_node.get('class', []):
                teamup_table = current_node; break
            current_node = current_node.find_next_sibling()
        if not teamup_table: continue

        active_teamup_found_flag = True
        teamup_data = {"name": teamup_name, "lore": "", "quote": "", "participants": []}
        teamup_data["lore"], teamup_data["quote"] = extract_teamup_lore_quote_su(heading_tag, teamup_table)

        tbody = teamup_table.find('tbody')
        rows = tbody.find_all('tr', recursive=False) if tbody else teamup_table.find_all('tr', recursive=False)
        if not rows: rows = teamup_table.find_all('tr')

        for row_idx, row in enumerate(rows[1:]):
            cells = row.find_all('td'); participant = {}
            if len(cells) >= 3:
                try:
                    ability_name_tag = cells[0].find('b')
                    participant['ability_name'] = ability_name_tag.get_text(strip=True) if ability_name_tag else cells[0].get_text(strip=True)
                    extracted_hero_name = "PARSE_ERROR"; hero_cell = cells[1]; extracted_via = "Unknown"
                    if hero_cell: # Hero name extraction logic...
                        all_links = hero_cell.find_all('a')
                        if all_links:
                            last_link = all_links[-1]; link_text = last_link.get_text(strip=True)
                            if link_text: extracted_hero_name = link_text; extracted_via = "Last Link Text"
                            else:
                                link_title = last_link.get('title')
                                if link_title: extracted_hero_name = link_title.strip(); extracted_via = "Last Link Title"
                        if extracted_hero_name == "PARSE_ERROR" and len(all_links) == 1:
                             single_link_title = all_links[0].get('title')
                             if single_link_title: extracted_hero_name = single_link_title.strip(); extracted_via = "Single Link Title"
                        if extracted_hero_name == "PARSE_ERROR":
                            cell_text = hero_cell.get_text(strip=True)
                            if cell_text: extracted_hero_name = cell_text; extracted_via = "Cell Full Text"
                    
                    hero_name_to_store = f"PARSE_ERROR: Raw='{extracted_hero_name}'"
                    if extracted_hero_name != "PARSE_ERROR":
                        normalized_extracted_name = normalize_for_comparison(extracted_hero_name) # Uses global normalize
                        if normalized_extracted_name and normalized_extracted_name in normalized_active_set:
                            hero_name_to_store = normalized_to_original_map_su.get(normalized_extracted_name, extracted_hero_name)
                    participant['hero'] = hero_name_to_store
                    
                    description_tag = cells[2]; is_anchor = False; main_description = ""; stats_from_small = {}
                    # ... (description, anchor, stats parsing as before, using parse_teamup_stats_from_small_tag_su) ...
                    anchor_marker = description_tag.find(lambda t: t.name == 'b' and 'TEAM-UP ANCHOR' in t.get_text(strip=True).upper())
                    if anchor_marker: # Anchor logic
                        is_anchor = True; current_desc_node = anchor_marker; desc_parts = []
                        while getattr(current_desc_node, 'next_sibling', None):
                            current_desc_node = current_desc_node.next_sibling
                            if isinstance(current_desc_node, NavigableString): stripped_text = current_desc_node.strip()
                            if stripped_text: desc_parts.append(stripped_text)
                            elif isinstance(current_desc_node, Tag) and current_desc_node.name == 'small': break
                        main_description = " ".join(desc_parts).strip()
                    else: # Non-anchor description
                        desc_soup_temp = BeautifulSoup(str(description_tag), 'html.parser')
                        for s_small_tag in desc_soup_temp.find_all('small'): s_small_tag.decompose()
                        main_description = desc_soup_temp.get_text(strip=True)
                    participant['is_anchor'] = is_anchor
                    participant['description'] = main_description if main_description else "(No description text)"

                    stats_small_tag_found = description_tag.select_one('p > small') # Check specific location first
                    if not stats_small_tag_found: # Fallback to last small tag
                         all_small_tags_in_cell = description_tag.find_all('small')
                         if all_small_tags_in_cell: stats_small_tag_found = all_small_tags_in_cell[-1]
                    if stats_small_tag_found:
                        stats_from_small = parse_teamup_stats_from_small_tag_su(stats_small_tag_found)
                    participant['stats'] = stats_from_small


                    if not participant['hero'].startswith("PARSE_ERROR"):
                        teamup_data["participants"].append(participant)
                except Exception as e_row: print(f"SU ERROR parsing teamup row in '{teamup_name}': {e_row}")
        if teamup_data["participants"]: active_teamups.append(teamup_data)
    if not active_teamup_found_flag: print("SU WARNING: No Active Team-Up sections processed.")
    print("SU: Active Team-Up Parsing Complete.")
    return active_teamups


if __name__ == '__main__':
    print("Testing scraper_utils.py (now includes more utilities)...")
    # ... (existing test placeholders) ...
    test_dict = {"a": 1, "b": {"c": 2, "d": None}}
    print(f"get_nested_value(test_dict, 'b.c'): {get_nested_value(test_dict, 'b.c')}") # Expected: 2
    print(f"get_nested_value(test_dict, 'b.d', 'default'): {get_nested_value(test_dict, 'b.d', 'default')}") # Expected: default
    print(f"get_nested_value(test_dict, 'b.e', 'default'): {get_nested_value(test_dict, 'b.e', 'default')}") # Expected: default
    set_nested_value(test_dict, "b.e.f", 3)
    print(f"test_dict after set_nested_value('b.e.f', 3): {test_dict}") # Expected: {'a': 1, 'b': {'c': 2, 'd': None, 'e': {'f': 3}}}
    print("Scraper utils testing placeholders complete.")