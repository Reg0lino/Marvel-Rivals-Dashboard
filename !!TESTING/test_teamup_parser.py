# test_teamup_parser.py (v7 - Added Retired Parsing Logic)
import requests
from bs4 import BeautifulSoup, NavigableString, Tag
import re
import os
import datetime

# --- Configuration ---
TEAMUP_URL = "https://marvelrivals.fandom.com/wiki/Team-Ups"
OUTPUT_FILENAME = "parsed_teamups_test.txt"
# Be a good citizen - identify your bot/script
USER_AGENT = "RivalsTeamupParser/1.6 (Testing; contact: YOUR_EMAIL_OR_GITHUB)" # Update version & contact

# --- Helper Functions ---

def fetch_page(url):
    """Fetches the HTML content of a given URL."""
    print(f"Fetching HTML from: {url} ...")
    headers = {'User-Agent': USER_AGENT}
    try:
        response = requests.get(url, headers=headers, timeout=20)
        response.raise_for_status()
        print("Successfully fetched page content.")
        return response.text
    except requests.exceptions.RequestException as e:
        print(f"ERROR fetching page {url}: {e}")
        return None

def parse_stats_from_small_tag(small_tag):
    """Parses key-value pairs from the <small> tag content by iterating tags."""
    stats = {}
    if not small_tag: return stats
    temp_tag = BeautifulSoup(str(small_tag), 'html.parser').find('small')
    if not temp_tag: return stats

    current_key = None; current_value_parts = []
    for element in temp_tag.contents:
        if isinstance(element, Tag):
            if element.name == 'b':
                if current_key and current_value_parts: stats[current_key] = " ".join(current_value_parts).strip()
                key_text = element.get_text(strip=True); key_text = key_text[:-1].strip() if key_text.endswith(':') else key_text
                current_key = key_text.upper().replace(' ', '_').replace('-', '_'); current_value_parts = []
            elif element.name == 'br': pass # Handled by string nodes mostly
            elif current_key: # Append text from other nested tags like <a> or <span>
                 tag_text = element.get_text(strip=True)
                 if tag_text: current_value_parts.append(tag_text)
        elif isinstance(element, NavigableString):
            text = element.strip()
            if current_key and text:
                if text.startswith(':'): text = text[1:].strip()
                if text: current_value_parts.append(text)
    if current_key and current_value_parts: stats[current_key] = " ".join(current_value_parts).strip()
    return stats

def extract_lore_quote(start_element, stop_element):
    """Extracts lore/quote paragraphs between two elements."""
    lore_parts, quote_parts = [], []
    current = start_element.find_next_sibling()
    while current and current != stop_element:
        # Stop if we hit another major heading
        if isinstance(current, Tag) and current.name in ['h2', 'h3', 'h4', 'table']:
            # Allow table only if stop_element is None (end of section)
            if not (current.name == 'table' and stop_element is None):
                break
        if isinstance(current, Tag) and current.name == 'p':
            italic_tag = current.find('i')
            text = italic_tag.get_text(strip=True) if italic_tag else current.get_text(strip=True)
            # Improved quote detection (more flexible)
            if italic_tag and ('"' in text or 'JOURNAL:' in text or text.count(':') == 1): quote_parts.append(text)
            elif text: lore_parts.append(text)
        current = current.find_next_sibling()
    lore = "\n".join(p for p in lore_parts if p).strip()
    quote = "\n".join(p for p in quote_parts if p).strip()
    return lore, quote

# --- Main Parsing Function ---
def parse_teamups(html_content):
    """Parses the Team-Ups page HTML to extract active and retired team-up details."""
    if not html_content: return [], {}

    print("Parsing HTML content...")
    soup = BeautifulSoup(html_content, 'html.parser')
    active_teamups = []; retired_abilities = []; fully_retired = []

    content_area = soup.select_one('div.mw-parser-output')
    if not content_area: print("ERROR: Could not find main content area."); return [], {}

    retired_marker = content_area.find('span', id='Retired_Team-Ups')
    retired_marker_parent_h3 = retired_marker.parent if retired_marker and retired_marker.parent.name == 'h3' else None

    # Find all major section headers (h2, h3) to iterate through sections
    section_headers = content_area.find_all(['h2', 'h3'], recursive=False)
    if not section_headers: # Fallback
        section_headers = content_area.find_all(['h2', 'h3'])

    parsing_active = True
    current_retired_section_type = "Unknown"
    active_teamup_found = False
    retired_entry_found = False

    print("Iterating through content sections...")
    for header in section_headers:
        # --- Check if we hit the Retired section ---
        if parsing_active and retired_marker_parent_h3 and header == retired_marker_parent_h3:
            print("\n--- Switching to Retired Section Parsing ---")
            parsing_active = False
            # Determine initial retired section type from this H3
            headline_tag = header.select_one('.mw-headline'); headline_text = headline_tag.get_text(strip=True) if headline_tag else ""
            if "Retired Team-Up Abilities" in headline_text: current_retired_section_type = "Retired Abilities"
            elif "Retired Team-Ups" in headline_text: current_retired_section_type = "Fully Retired"
            else: current_retired_section_type = "Unknown Retired Section"
            print(f" Initial Retired Section Type: {current_retired_section_type}")
            continue # Move to the next header/element

        # ================= PARSE ACTIVE Section (if H2) ==================
        if parsing_active and header.name == 'h2':
            teamup_name_tag = header.select_one('.mw-headline')
            teamup_name = teamup_name_tag.get_text(strip=True) if teamup_name_tag else header.get_text(strip=True)

            teamup_table = None; sibling = header.find_next_sibling(); search_depth = 0
            while sibling and search_depth < 5:
                 if isinstance(sibling, Tag) and sibling.name == 'table' and 'article-table' in sibling.get('class', []): teamup_table = sibling; break
                 if isinstance(sibling, Tag) and sibling.name in ['h2', 'h3']: break
                 if retired_marker_parent_h3 and sibling == retired_marker_parent_h3: break
                 sibling = sibling.find_next_sibling(); search_depth += 1

            if not teamup_table: continue # Skip H2 if no table

            active_teamup_found = True
            print(f"Found Active Team-Up Section: {teamup_name}")
            teamup_data = {"name": teamup_name, "lore": "", "quote": "", "participants": []}
            teamup_data["lore"], teamup_data["quote"] = extract_lore_quote(header, teamup_table)

            print(f"  Parsing table for {teamup_name}...")
            tbody = teamup_table.find('tbody'); rows = tbody.find_all('tr') if tbody else teamup_table.find_all('tr')

            for row in rows[1:]:
                cells = row.find_all('td'); participant = {}
                if len(cells) >= 3:
                    try:
                        ability_name_tag = cells[0].find('b'); participant['ability_name'] = ability_name_tag.get_text(strip=True) if ability_name_tag else cells[0].get_text(strip=True)
                        hero_name_tag = cells[1].find('a', title=True); hero_name_raw = hero_name_tag['title'] if hero_name_tag else cells[1].get_text(strip=True); participant['hero'] = hero_name_raw.strip()
                        description_tag = cells[2]; is_anchor = False; main_description = ""; stats = {}
                        anchor_marker = description_tag.find(lambda tag: tag.name == 'b' and 'TEAM-UP ANCHOR' in tag.get_text(strip=True).upper())
                        if anchor_marker:
                            is_anchor = True; current = anchor_marker; desc_parts = []
                            while getattr(current, 'next_sibling', None):
                                current = current.next_sibling
                                if isinstance(current, NavigableString):
                                    stripped_text = current.strip();
                                    if stripped_text: desc_parts.append(stripped_text)
                                elif isinstance(current, Tag) and current.name == 'small': break
                            main_description = " ".join(desc_parts).strip()
                        else:
                            desc_soup = BeautifulSoup(str(description_tag), 'html.parser'); small_tags_in_desc = desc_soup.find_all('small');
                            for s in small_tags_in_desc: s.decompose()
                            main_description = desc_soup.get_text(strip=True)
                        participant['is_anchor'] = is_anchor; participant['description'] = main_description or "(See Stats/Special Effect)"
                        stats_small_tag = description_tag.select_one('p > small')
                        if not stats_small_tag:
                             all_small = description_tag.find_all('small')
                             if all_small: stats_small_tag = all_small[-1]
                        if stats_small_tag: stats = parse_stats_from_small_tag(stats_small_tag)
                        participant['stats'] = stats
                        teamup_data["participants"].append(participant)
                    except Exception as e: print(f"    ERROR parsing row in active table {teamup_name}: {e}")
                else: print(f"    Skipping row in active {teamup_name} table - cells: {len(cells)}.")
            if teamup_data["participants"]: active_teamups.append(teamup_data)
            else: print(f"  Warning: No participants parsed for '{teamup_name}'. Skipping.")

        # ================= PARSE RETIRED Section (if H3) ==================
        elif not parsing_active and header.name == 'h3':
            # This H3 might define the subsection type if the first one didn't
            headline_tag = header.select_one('.mw-headline'); headline_text = headline_tag.get_text(strip=True) if headline_tag else ""
            if "Retired Team-Up Abilities" in headline_text: current_retired_section_type = "Retired Abilities"
            elif "Retired Team-Ups" in headline_text: current_retired_section_type = "Fully Retired"
            # Ignore other H3s like the Timeline ones for now
            elif "Timeline" in headline_text: current_retired_section_type = "Timeline (Skipped)"
            else: current_retired_section_type = "Unknown Retired Section"
            print(f" Parsing Retired Section Header: {headline_text} (Type: {current_retired_section_type})")

            # --- Now parse elements *within* this retired section until the next H3 ---
            element_after_h3 = header.find_next_sibling()
            while element_after_h3:
                 # Stop if we hit the next H3 (or H2)
                 if isinstance(element_after_h3, Tag) and element_after_h3.name in ['h3', 'h2']:
                      break

                 # --- Look for Retired Entries (using P>B or P>BIG>B structures) ---
                 entry_name = None; affected_hero = None; retired_ability_name = None; entry_node = None

                 # Check for "Retired Ability" structure: <p><b><img/> <a..>Teamup</a> - Ability (Hero)</b></p>
                 if isinstance(element_after_h3, Tag) and element_after_h3.name == 'p':
                     bold_tag = element_after_h3.find('b')
                     if bold_tag:
                         entry_text = bold_tag.get_text(strip=True)
                         # Regex to capture parts: "TeamUp Name - Ability Name (Hero Name)"
                         match = re.match(r"(.+?)\s*-\s*(.+?)\s*\((.+?)\)", entry_text)
                         if match and current_retired_section_type == "Retired Abilities":
                             entry_name = match.group(1).strip() # TeamUp Name Context
                             retired_ability_name = match.group(2).strip()
                             affected_hero = match.group(3).strip()
                             entry_node = element_after_h3 # Found the start node
                             print(f"  Found Retired Ability Entry: {entry_name} - {retired_ability_name} ({affected_hero})")

                 # Check for "Fully Retired" structure: <p><big><b><u>Teamup Name</u></b></big></p>
                 if not entry_node and isinstance(element_after_h3, Tag) and element_after_h3.name == 'p':
                      big_bold_underline = element_after_h3.select_one('big > b > u')
                      if big_bold_underline and current_retired_section_type == "Fully Retired":
                           entry_name = big_bold_underline.get_text(strip=True)
                           entry_node = element_after_h3 # Found the start node
                           print(f"  Found Fully Retired Entry: {entry_name}")

                 # --- If an entry was identified, parse its details ---
                 if entry_node:
                     retired_entry_found = True
                     retired_data = {"name": entry_name, "status": current_retired_section_type, "lore": "", "quote": "", "affected_hero": affected_hero, "retired_ability_name": retired_ability_name, "participants_involved": [], "stats": {}}

                     # Find the table associated with this entry
                     entry_table = None; sibling = entry_node.find_next_sibling(); search_depth = 0
                     while sibling and search_depth < 5:
                         if isinstance(sibling, Tag) and sibling.name == 'table' and 'article-table' in sibling.get('class', []): entry_table = sibling; break
                         if isinstance(sibling, Tag) and sibling.name in ['h4', 'h3', 'h2', 'p']: # Stop if next text/heading starts
                              # Allow <p> only if it doesn't contain the specific bold structures we look for
                              if sibling.name == 'p':
                                   if sibling.find('b') and re.match(r"(.+?)\s*-\s*(.+?)\s*\((.+?)\)", sibling.find('b').get_text(strip=True)): break # Next retired ability
                                   if sibling.select_one('big > b > u'): break # Next fully retired
                              else: # H2, H3, H4 always stop
                                   break
                         sibling = sibling.find_next_sibling(); search_depth += 1

                     # Extract lore/quote between entry node and table (or next relevant node)
                     retired_data["lore"], retired_data["quote"] = extract_lore_quote(entry_node, entry_table or sibling) # Pass sibling if table not found

                     # Parse the table if found
                     if entry_table:
                          tbody = entry_table.find('tbody'); rows = tbody.find_all('tr') if tbody else entry_table.find_all('tr')
                          for row in rows[1:]:
                              cells = row.find_all('td')
                              if len(cells) >= 2:
                                  try:
                                      ability_tag = cells[0].find('b'); ability = ability_tag.get_text(strip=True) if ability_tag else cells[0].get_text(strip=True)
                                      hero_tag = cells[1].find('a', title=True); hero = hero_tag['title'] if hero_tag else cells[1].get_text(strip=True); hero = hero.strip()
                                      if current_retired_section_type == "Fully Retired": retired_data["participants_involved"].append(hero)
                                      # If retired ability, affected hero already known, but we can double check/confirm
                                      elif current_retired_section_type == "Retired Abilities":
                                          if not retired_data["affected_hero"]: retired_data["affected_hero"] = hero # Store if not found from header
                                          if not retired_data["retired_ability_name"]: retired_data["retired_ability_name"] = ability # Store if not found from header
                                      # Parse stats from td[2] if available
                                      if len(cells) >= 3:
                                          stats_small = cells[2].select_one('p > small') or (cells[2].find_all('small')[-1] if cells[2].find_all('small') else None)
                                          if stats_small: retired_data["stats"].update(parse_stats_from_small_tag(stats_small))
                                  except Exception as e: print(f"    ERROR parsing row in retired table {entry_name}: {e}")

                     # Add to correct list
                     if current_retired_section_type == "Retired Abilities": retired_abilities.append(retired_data)
                     elif current_retired_section_type == "Fully Retired":
                          if not retired_data["participants_involved"] and retired_data["lore"]: # Guess from lore
                               known = ["Magneto","Scarlet Witch","Thor","Captain America","Storm","Winter Soldier","Doctor Strange","Psylocke","Namor"]; inv = [h for h in known if h in retired_data["lore"]];
                               if inv: retired_data["participants_involved"] = inv
                          fully_retired.append(retired_data)

                 # Move to the next element after the processed entry or the element we stopped at
                 element_after_h3 = entry_table.find_next_sibling() if entry_table else sibling # Move past table or sibling
                 if not element_after_h3: break # End of section/content

            else: # Move to the next element if not an H3/H4 starting a retired section
                 element_after_h3 = element_after_h3.find_next_sibling()
                 if not element_after_h3: break # End of content

    if not active_teamup_found: print("WARNING: No Active Team-Up H2/Table sections were successfully processed!")
    if not retired_entry_found and retired_marker_parent_h3: print("WARNING: Retired section marker found, but no retired entries parsed!")

    print("Parsing complete.")
    # Construct the final retired data dictionary
    final_retired_data = {"Retired Abilities": retired_abilities, "Fully Retired": fully_retired}
    return active_teamups, final_retired_data


# --- Format Output (Unchanged from v5) ---
def format_output(active_teamups, retired_teamups_data):
    """Formats the parsed data into a human-readable string."""
    output_lines = []; timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC"); separator = "#" * 60
    output_lines.append(f"Team-Up Data Parsed from: {TEAMUP_URL}"); output_lines.append(f"Timestamp: {timestamp}"); output_lines.append("\n")
    output_lines.append(separator); output_lines.append("# ACTIVE TEAM-UPS"); output_lines.append(separator); output_lines.append("\n")
    if not active_teamups: output_lines.append("(No active team-ups found or parsed.)")
    else:
        for teamup in active_teamups:
            output_lines.append(f"## Team-Up: {teamup['name']}"); output_lines.append("-" * len(f"## Team-Up: {teamup['name']}"))
            if teamup.get('lore'): output_lines.append("\n[Lore]:"); output_lines.append(teamup['lore'])
            if teamup.get('quote'): output_lines.append("\n[Quote]:"); output_lines.append(teamup['quote'])
            output_lines.append("\n--- Participants ---")
            if not teamup.get('participants'): output_lines.append("(No participant details found in table)")
            else:
                for i, p in enumerate(teamup['participants']):
                    output_lines.append(f"\n[Participant {i+1}]"); output_lines.append(f"  Hero: {p.get('hero', 'N/A')}")
                    output_lines.append(f"  Is Anchor: {'Yes' if p.get('is_anchor') else 'No'}"); output_lines.append(f"  Ability Name: {p.get('ability_name', 'N/A')}")
                    desc = p.get('description', '').strip();
                    if desc and desc != "(See Stats/Special Effect)": output_lines.append(f"  Description: {desc}")
                    if p.get('stats'):
                        output_lines.append("  Stats:"); sorted_stats = sorted(p['stats'].items())
                        if not sorted_stats: output_lines.append("    (None extracted)") # Explicitly state if empty
                        else:
                            for key, value in sorted_stats: output_lines.append(f"    {key.replace('_', ' ').title()}: {value}")
                    else: output_lines.append("  Stats: (None extracted)") # Should not happen if dict exists, but safety
            output_lines.append("\n" + separator + "\n")

    output_lines.append("\n"); output_lines.append(separator); output_lines.append("# RETIRED TEAM-UPS / ABILITIES"); output_lines.append(separator); output_lines.append("\n")
    # Use the structured dictionary now
    retired_abilities_list = retired_teamups_data.get("Retired Abilities", [])
    fully_retired_list = retired_teamups_data.get("Fully Retired", [])
    if not retired_abilities_list and not fully_retired_list: output_lines.append("(No retired team-ups or abilities found or parsed.)")
    else:
        if retired_abilities_list:
             output_lines.append("--- Retired Abilities (Team-Up may still exist) ---")
             for item in retired_abilities_list:
                 # Use item['name'] which should be like "Teamup - Ability (Hero)"
                 output_lines.append(f"\nContext/Name: {item.get('name', 'Unknown')}")
                 output_lines.append(f"  Status: {item.get('status', 'N/A')}")
                 output_lines.append(f"  Retired Ability: {item.get('retired_ability_name', 'N/A')}")
                 output_lines.append(f"  Affected Hero: {item.get('affected_hero', 'N/A')}")
                 if item.get('lore'): output_lines.append(f"  Context/Lore: {item['lore']}")
                 if item.get('quote'): output_lines.append(f"  Quote: {item['quote']}")
                 if item.get('stats'): output_lines.append("  Stats (at time of retirement):"); sorted_stats = sorted(item['stats'].items());
                 if not sorted_stats: output_lines.append("    (None extracted)")
                 else:
                     for key, value in sorted_stats: output_lines.append(f"    {key.replace('_', ' ').title()}: {value}")
             output_lines.append("\n")
        if fully_retired_list:
             output_lines.append("--- Fully Retired Team-Ups ---")
             for item in fully_retired_list:
                 output_lines.append(f"\nRetired Team-Up: {item.get('name', 'Unknown')}") # Name from H4/P tag
                 output_lines.append(f"  Status: {item.get('status', 'N/A')}")
                 involved = item.get('participants_involved', []); output_lines.append(f"  Heroes Involved: {', '.join(involved) if involved else 'N/A'}")
                 if item.get('lore'): output_lines.append(f"  Context/Lore: {item['lore']}")
                 if item.get('quote'): output_lines.append(f"  Quote: {item['quote']}")
                 if item.get('stats'): output_lines.append("  Stats (at time of retirement):"); sorted_stats = sorted(item['stats'].items());
                 if not sorted_stats: output_lines.append("    (None extracted)")
                 else:
                      for key, value in sorted_stats: output_lines.append(f"    {key.replace('_', ' ').title()}: {value}")
             output_lines.append("\n")
    return "\n".join(output_lines)

# --- Save Output (Unchanged) ---
def save_output(output_string, filename):
    """Saves the formatted string to a text file."""
    try:
        with open(filename, 'w', encoding='utf-8') as f: f.write(output_string)
        print(f"Successfully saved parsed data to: {filename}")
        return True
    except IOError as e: print(f"ERROR saving output file {filename}: {e}"); return False

# --- Main Execution (Unchanged) ---
if __name__ == "__main__":
    print("Starting Team-Up Parser Test Script (v7)...")
    html = fetch_page(TEAMUP_URL)
    if html:
        active_data, retired_data = parse_teamups(html)
        if active_data or retired_data["Retired Abilities"] or retired_data["Fully Retired"]:
            formatted_text = format_output(active_data, retired_data)
            save_output(formatted_text, OUTPUT_FILENAME)
        else:
            print("Parsing completed, but NO data was extracted. Check wiki structure and selectors.")
            save_output(f"Parsing failed to extract any team-up data.\nTimestamp: {datetime.datetime.now()}", OUTPUT_FILENAME)
    else: print("Could not fetch page content. Aborting.")
    print("Script finished.")