# -*- coding: utf-8 -*-
import sys
import json
import os
import re
import subprocess
import shutil
import urllib.parse
import argparse
import requests 
import threading
from pathlib import Path 

# --- Ensure QTextBrowser is imported, QDesktopServices/QUrl not needed for this approach ---
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QScrollArea, QGroupBox, QTextEdit, QSizePolicy, QApplication, 
    QPushButton, QLineEdit, QComboBox, QSpacerItem, QDialog, QFrame, QMessageBox,
    QStyleOptionGroupBox, QStyle, QLayout, QFileDialog, QTextBrowser, QDialogButtonBox
)
from PySide6.QtGui import (
    QPixmap, QPalette, QColor, QFont, QFontDatabase, QWheelEvent, QKeyEvent,
    QScreen, QTextOption, QIcon, QTextDocument, QMouseEvent, QPainter, QFontMetrics,
    QTextCursor, QTextCharFormat, QDesktopServices 
)
from PySide6.QtCore import (
    Qt, QRect, QSize, Signal, Slot, QPoint, QStandardPaths, QTimer, QMargins, QUrl, QThread 
  
)
# --- End Import Changes ---

# --- FlowLayout Implementation ---
class FlowLayout(QLayout):
    def __init__(self, parent=None, margin=-1, hSpacing=-1, vSpacing=-1):
        super(FlowLayout, self).__init__(parent)
        self._hSpacing = hSpacing
        self._vSpacing = vSpacing
        self._items = []
        if margin != -1:
            self.setContentsMargins(margin, margin, margin, margin)

    def __del__(self):
        while self.count():
            item = self.takeAt(0)
            if item:
                widget = item.widget()
                if widget:
                    widget.deleteLater()

    def addItem(self, item):
        self._items.append(item)

    def horizontalSpacing(self):
        if self._hSpacing >= 0:
            return self._hSpacing
        else:
            return self.smartSpacing(QStyle.PixelMetric.PM_LayoutHorizontalSpacing)

    def verticalSpacing(self):
        if self._vSpacing >= 0:
            return self._vSpacing
        else:
            return self.smartSpacing(QStyle.PixelMetric.PM_LayoutVerticalSpacing)

    def count(self):
        return len(self._items)

    def itemAt(self, index):
        if 0 <= index < len(self._items):
            return self._items[index]
        return None

    def takeAt(self, index):
        if 0 <= index < len(self._items):
            return self._items.pop(index)
        return None

    def expandingDirections(self):
        # This layout doesn't expand
        return Qt.Orientation(0)

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        height = self._doLayout(QRect(0, 0, width, 0), True)
        return height

    def setGeometry(self, rect):
        super(FlowLayout, self).setGeometry(rect)
        self._doLayout(rect, False)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        size = QSize()
        for item in self._items:
            size = size.expandedTo(item.minimumSize())

        margins = self.contentsMargins()
        size += QSize(margins.left() + margins.right(), margins.top() + margins.bottom())
        return size

    def _doLayout(self, rect, testOnly):
        margins = self.contentsMargins()
        effectiveRect = rect.adjusted(+margins.left(), +margins.top(), -margins.right(), -margins.bottom())
        x = effectiveRect.x()
        y = effectiveRect.y()
        lineHeight = 0
        # Use style from parentWidget or application
        style = self.parentWidget().style() if self.parentWidget() else QApplication.style()

        for item in self._items:
            widget = item.widget()
            spaceX = self.horizontalSpacing()
            if spaceX == -1:
                spaceX = style.layoutSpacing(QSizePolicy.ControlType.PushButton, QSizePolicy.ControlType.PushButton, Qt.Orientation.Horizontal)
            spaceY = self.verticalSpacing()
            if spaceY == -1:
                spaceY = style.layoutSpacing(QSizePolicy.ControlType.PushButton, QSizePolicy.ControlType.PushButton, Qt.Orientation.Vertical)

            nextX = x + item.sizeHint().width() + spaceX
            if nextX - spaceX > effectiveRect.right() and lineHeight > 0:
                x = effectiveRect.x()
                y = y + lineHeight + spaceY
                nextX = x + item.sizeHint().width() + spaceX
                lineHeight = 0

            if not testOnly:
                item.setGeometry(QRect(QPoint(x, y), item.sizeHint()))

            x = nextX
            lineHeight = max(lineHeight, item.sizeHint().height())

        return y + lineHeight - rect.y() + margins.bottom()

    def smartSpacing(self, pm):
        parent = self.parent()
        if not parent:
            return -1
        elif parent.isWidgetType():
            return parent.style().pixelMetric(pm, None, parent)
        else:
            # If parent is another layout, try getting spacing from application style
            style = QApplication.style()
            return style.pixelMetric(pm) if style else 5 # Default fallback


# --- Helper Function for Resource Paths ---
def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except AttributeError:
        # sys._MEIPASS not found, running in normal Python environment
        base_path = os.path.abspath(os.path.dirname(__file__))
    return os.path.normpath(os.path.join(base_path, relative_path))

# --- Configuration Paths ---
CHARACTER_DATA_FOLDER = resource_path('characters')
IMAGE_FOLDER = resource_path('images')
INFO_FOLDER = resource_path('info')
CONFIG_FOLDER = resource_path('config')
STYLES_FOLDER = resource_path('styles')
FONT_FOLDER = resource_path('styles/font') # <<< CHANGED PATH HERE

# --- AppData/Favorites Path ---
app_data_path = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)
if not app_data_path:
    app_data_path = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.GenericDataLocation)
app_data_root = os.path.dirname(app_data_path) if app_data_path else None
if app_data_root and not os.path.exists(app_data_root):
    try:
        os.makedirs(app_data_root)
        print(f"Created app data root directory: {app_data_root}")
    except OSError as e:
        print(f"Warning: Could not create app data root directory {app_data_root}: {e}")
        app_data_path = None
if app_data_path and not os.path.exists(app_data_path):
    try:
        os.makedirs(app_data_path)
        print(f"Created app data directory: {app_data_path}")
    except OSError as e:
        print(f"Warning: Could not create app data directory {app_data_path}: {e}")
        app_data_path = None
if app_data_path:
    FAVORITES_FILE = os.path.join(app_data_path, 'rivals_dashboard_favorites.json')
    print(f"Using favorites path: {FAVORITES_FILE}")
else:
    FAVORITES_FILE = resource_path('rivals_dashboard_favorites.json')
    print(f"Warning: Could not get/create standard app data path. Using fallback: {FAVORITES_FILE}")

# --- Font Configuration ---
SYSTEM_FONT_FAMILY_NAME = "Segoe UI" # Default fallback
CUSTOM_FONT_FAMILY_NAME = "Refrigerator Deluxe" # Initial guess, will be updated
CURRENT_FONT_FAMILY_NAME = SYSTEM_FONT_FAMILY_NAME # Start with system/fallback
CUSTOM_FONT_LOADED = False
FONT_FILES = {
    "Regular": "Refrigerator Deluxe.otf",
    "Bold": "Refrigerator Deluxe Bold.otf",
    "Heavy": "Refrigerator Deluxe Heavy.otf",
    "Light": "Refrigerator Deluxe Light.otf"
}

# --- Constants ---
# --- Debug Mode Toggle ---
# Set to True to see detailed debug messages in the console, False to hide them
DEBUG_MODE = False # <--- EDIT THIS LINE (True/False) TO TOGGLE DEBUG OUTPUT
print(f"CONFIRMATION: DEBUG_MODE is currently set to: {DEBUG_MODE}")


DEFAULT_THEME_COLOR = "#888888"
DEFAULT_SECONDARY_THEME_COLOR = "#CCCCCC"
BASE_FONT_SIZE = 13
CURRENT_GLOBAL_FONT_SIZE_PT = float(BASE_FONT_SIZE)
HEADER_FONT_SIZE = BASE_FONT_SIZE + 4
GROUP_TITLE_FONT_SIZE = BASE_FONT_SIZE + 4
CHARACTER_NAME_FONT_SIZE = 32
JUMP_BAR_FIXED_ICON_SIZE = 46
JUMP_BAR_FIXED_SPACING = 4
DETAILS_COLOR = "#B8B8B8"
LORE_COLOR = "#C8C8C8"
ABILITY_TITLE_STYLE_TEMPLATE = f"font-size: 1.1em; font-weight: {QFont.Weight.Bold}; color: {{color}};"
SECTION_TITLE_STYLE_TEMPLATE = f"font-size: 1.05em; font-weight: {QFont.Weight.Bold}; color: {{color}};"
FIELD_LABEL_STYLE = f"font-weight: {QFont.Weight.Bold}; color: #D0D0D0;"
FIELD_VALUE_STYLE = f"font-weight: {QFont.Weight.Normal}; color: #E5E5E5;"
LIST_ITEM_STYLE = f"margin-left: 15px; margin-top: 1px; margin-bottom: 1px; font-weight: {QFont.Weight.Normal};"
QUOTE_STYLE = f"font-style: italic; color: {LORE_COLOR}; border-left: 3px solid {LORE_COLOR}; padding-left: 10px; margin-top: 4px; margin-bottom: 4px; font-weight: {QFont.Weight.Normal};"
H1_COLOR = "#FBBF2C"
H2_COLOR = "#60A5FA"
H3_COLOR = "#F87171"
LIST_STYLE = "margin-left: 20px; margin-top: 3px; margin-bottom: 3px;"
INFO_POPUP_UNDERLINE_COLOR = "#FBBF2C"
BOLD_UNDERLINE_STYLE_TEMPLATE_POPUP = f"font-weight: bold; text-decoration: underline; color: {INFO_POPUP_UNDERLINE_COLOR};"
SCROLL_PADDING_TOP = 10
MIN_SEARCH_LENGTH = 3
SEARCH_SEASON_STRING = "Season 2" # <<< UPDATE THIS MANUALLY (e.g., "Patch 2.1", "Season 2.5")




# --- Configuration Dictionaries (Loaded Later) ---
CHARACTER_IMAGE_MAP = {}
CHARACTER_ICON_MAP = {}
INFO_FILES = {}

# --- Helper Functions ---
def load_json_config(filename, default_value={}):
    """Loads configuration data from a JSON file, ignoring comments."""
    filepath = os.path.join(CONFIG_FOLDER, filename)
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            # Read lines and filter out comments starting with //
            content = "".join(line for line in f if not line.strip().startswith("//"))
        return json.loads(content) # Parse the cleaned content
    except FileNotFoundError:
        print(f"ERROR: Config file not found: {filepath}")
        return default_value
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON in config file: {filepath} - {e}")
        return default_value
    except Exception as e:
        print(f"ERROR: Failed to load config file: {filepath} - {e}")
        return default_value

def load_character_data(data_folder=CHARACTER_DATA_FOLDER):
    """Loads all character JSON data from the specified folder, ignoring comments."""
    all_character_data = {}
    loaded_count = 0
    error_files = []
    if not os.path.isdir(data_folder):
        print(f"Error: Character data folder not found at '{data_folder}'")
        return None

    print(f"Loading character data from folder: {data_folder}")
    for filename in os.listdir(data_folder):
        if filename.lower().endswith(".json"):
            file_path = os.path.join(data_folder, filename)
            char_data = None
            try:
                # Try reading with UTF-8-SIG first (handles BOM)
                with open(file_path, 'r', encoding='utf-8-sig') as f:
                    content = "".join(line for line in f if not line.strip().startswith("//"))
                    char_data = json.loads(content)
            except UnicodeDecodeError:
                 # Fallback to plain UTF-8 if SIG fails
                 try:
                     with open(file_path, 'r', encoding='utf-8') as f:
                         content = "".join(line for line in f if not line.strip().startswith("//"))
                         char_data = json.loads(content)
                 except Exception as e_inner:
                    error_files.append(f"{filename} (Encoding/Read Error: {e_inner})")
                    print(f"Error reading file '{filename}' with multiple encodings: {e_inner}")
                    continue # Skip this file
            except json.JSONDecodeError as e:
                error_files.append(f"{filename} (JSON Error)")
                print(f"Error loading '{filename}': Invalid JSON - {e}")
                continue # Skip this file
            except Exception as e:
                error_files.append(f"{filename} (Load Error)")
                print(f"Error processing file '{filename}': {e}")
                continue # Skip this file

            # Process successfully loaded data
            if char_data is not None:
                if not isinstance(char_data, dict):
                    error_files.append(f"{filename} (Not object)")
                    continue
                char_name = char_data.get("name")
                if not char_name or not isinstance(char_name, str):
                    error_files.append(f"{filename} (No/Bad name)")
                    continue

                # Apply name corrections
                if char_name == "Namor McKenzie": char_name = "Namor"; char_data["name"] = "Namor"
                if char_name == "The Punisher": char_name = "Punisher"; char_data["name"] = "Punisher"
                if char_name == "Cloak and Dagger": char_name = "Cloak & Dagger"; char_data["name"] = "Cloak & Dagger"

                is_new = char_name not in all_character_data
                if not is_new:
                    # Log overwrites but don't add to error list
                    print(f"Warning: Duplicate character data found for '{char_name}' in '{filename}'. Overwriting previous entry.")
                all_character_data[char_name] = char_data
                if is_new:
                    loaded_count += 1

    if error_files:
        print("\n--- Issues loading character JSON files ---")
        for err in error_files:
            print(f"- {err}")
        print("-----------------------------------------\n")

    if all_character_data: # Check if dictionary is not empty
        print(f"Successfully loaded data for {len(all_character_data)} unique characters.")
        return all_character_data
    else:
        print("Error: No valid character data files were loaded.")
        return None
    # --- Add this Helper Function ---
def get_config_value_flexible(config_map, key):
    """
    Tries to get value from a dictionary using the original key,
    then common sanitized versions, and performs case-insensitive checks
    if direct matches fail.
    """
    if not isinstance(key, str) or not isinstance(config_map, dict): # Basic checks
        return None

    # --- Case-Sensitive Checks First ---
    value = config_map.get(key)
    if value is not None: return value
    key_sanitized_common = key.replace(' ', '_').replace('&', 'and')
    value = config_map.get(key_sanitized_common)
    if value is not None: return value
    key_sanitized_space = key.replace(' ', '_')
    if key_sanitized_space != key and key_sanitized_space != key_sanitized_common:
        value = config_map.get(key_sanitized_space)
        if value is not None: return value
    key_sanitized_amp = key.replace('&', 'and')
    if key_sanitized_amp != key and key_sanitized_amp != key_sanitized_common:
        value = config_map.get(key_sanitized_amp)
        if value is not None: return value

    # --- Case-Insensitive Checks ---
    key_lower = key.lower()
    key_sanitized_common_lower = key_sanitized_common.lower()
    key_sanitized_space_lower = key_sanitized_space.lower()
    key_sanitized_amp_lower = key_sanitized_amp.lower()

    for config_key, config_value in config_map.items():
        if not isinstance(config_key, str): continue
        config_key_lower = config_key.lower()
        if config_key_lower == key_lower: return config_value
        if config_key_lower == key_sanitized_common_lower: return config_value
        if config_key_lower == key_sanitized_space_lower: return config_value
        if config_key_lower == key_sanitized_amp_lower: return config_value

    if DEBUG_MODE and key: # Only print warning if key was actually provided
         print(f"WARN: Config lookup failed for key '{key}' after checking multiple variations.")
    return None # Return None if all checks fail
# --- End Helper Function ---


def load_favorites(filename=FAVORITES_FILE):
    """Loads the set of favorite character names."""
    if not os.path.exists(filename):
        return set()
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            data = json.load(f)
        # Check structure before accessing keys
        if isinstance(data, dict) and "favorites" in data and isinstance(data["favorites"], list):
            # Ensure items in the list are strings
            return set(item for item in data["favorites"] if isinstance(item, str))
        else:
            print(f"Warning: Favorites file '{filename}' has incorrect format.")
            return set()
    except json.JSONDecodeError as e:
        print(f"Warning: Invalid JSON in favorites file '{filename}'. Error: {e}")
        return set()
    except Exception as e:
        print(f"Warning: Could not load favorites '{filename}'. Error: {e}")
        return set()

def save_favorites(favorites_set, filename=FAVORITES_FILE):
    """Saves the set of favorite character names."""
    try:
        fav_dir = os.path.dirname(filename)
        if fav_dir and not os.path.exists(fav_dir):
            try:
                os.makedirs(fav_dir)
                print(f"Created directory for favorites: {fav_dir}")
            except OSError as e:
                print(f"Error creating directory for favorites '{fav_dir}'. Error: {e}")
                return # Cannot save if directory fails
        # Convert set to sorted list for consistent saving
        favorites_list = sorted(list(favorites_set))
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump({"favorites": favorites_list}, f, indent=2)
    except Exception as e:
        print(f"Error saving favorites to '{filename}'. Error: {e}")

def get_stylesheet():
    """Loads the stylesheet directly from the file."""
    qss_path = os.path.join(STYLES_FOLDER, 'dark_theme.qss')
    stylesheet = ""
    try:
        with open(qss_path, 'r', encoding='utf-8') as f:
            stylesheet = f.read()
    except FileNotFoundError:
        print(f"ERROR: Stylesheet file not found: {qss_path}")
        QMessageBox.warning(None, "Style Error", f"Stylesheet file missing:\n{qss_path}")
    except Exception as e:
        print(f"ERROR: Failed to load stylesheet: {qss_path} - {e}")
        QMessageBox.warning(None, "Style Error", f"Failed to load stylesheet:\n{qss_path}\n\n{e}")
    return stylesheet

# --- Replace this entire function ---
def _format_info_text(raw_text):
    """Converts simple markdown-like syntax in info files to HTML, making URLs clickable."""
    if not raw_text:
        return ""

    html_lines = []
    in_list = False

    # Regex to find URLs (handles http, https, www.)
    # Allows various characters in path/query, but stops at whitespace or common terminators like ), <, >
    url_pattern = re.compile(r'(\b(?:https?://|www\.)[^\s<>()"\']+)', re.IGNORECASE)

    def make_links_clickable(line):
        # Use lambda with re.sub to create the <a> tag
        # Ensure www links get http:// prepended for the href
        def replace_url(match):
            url = match.group(1)
            # Sanitize URL minimally for display, keep original for href
            display_url = url.replace('<', '<').replace('>', '>') # Basic HTML entity escaping
            href = url if url.startswith(('http://', 'https://')) else 'http://' + url
            # Style the link blue and underlined
            link_style = "color:#77C4FF; text-decoration: underline;"
            return f'<a href="{href}" style="{link_style}">{display_url}</a>'

        # Escape potential HTML in the rest of the line BEFORE applying links
        # This prevents markdown like **<script>** from becoming literal HTML
        line_escaped = line.replace('&', '&').replace('<', '<').replace('>', '>')
        return url_pattern.sub(replace_url, line_escaped)

    for line in raw_text.splitlines():
        line = line.strip() # Strip leading/trailing whitespace first

        if not line: # Handle empty lines
             if in_list: html_lines.append("</ul>"); in_list = False
             # Add an empty paragraph for spacing if desired, otherwise skip
             # html_lines.append("<p> </p>") # Use non-breaking space for visibility
             continue # Skip further processing for empty line

        # Apply markdown conversions first (on the original, unescaped line)
        if line.startswith("### "):
            if in_list: html_lines.append("</ul>"); in_list = False
            content = line[4:].strip()
            # Make URLs clickable *within* the content after escaping other HTML
            content = make_links_clickable(content)
            html_lines.append(f"<h3 style='color:{H3_COLOR}; margin-top: 8px; margin-bottom: 4px;'>{content}</h3>")
        elif line.startswith("## "):
            if in_list: html_lines.append("</ul>"); in_list = False
            content = line[3:].strip()
            content = make_links_clickable(content)
            html_lines.append(f"<h2 style='color:{H2_COLOR}; margin-top: 10px; margin-bottom: 5px;'>{content}</h2>")
        elif line.startswith("> "):
            if in_list: html_lines.append("</ul>"); in_list = False
            content = line[2:].strip()
            content = make_links_clickable(content)
            quote_style_inline = f"font-style: italic; color: {LORE_COLOR}; border-left: 3px solid {LORE_COLOR}; padding-left: 10px; margin-top: 4px; margin-bottom: 4px; display: block; background-color: #333;" # Added subtle background
            html_lines.append(f"<blockquote style='{quote_style_inline}'>{content}</blockquote>")
        elif line.startswith("* "):
            content = line[2:].strip()
            if not in_list:
                html_lines.append(f"<ul style='{LIST_STYLE}'>")
                in_list = True
            content = make_links_clickable(content)
            html_lines.append(f"<li>{content}</li>")
        else: # Plain text line
            if in_list: html_lines.append("</ul>"); in_list = False
            # Basic inline markdown (**bold**, __underline__) - apply *before* link detection/escaping
            formatted_line = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", line) # Use original line here
            formatted_line = re.sub(r"__(.*?)__", r"<u>\1</u>", formatted_line)
            # Now escape HTML and make URLs clickable in the potentially bolded/underlined text
            formatted_line = make_links_clickable(formatted_line)
            html_lines.append(f"<p>{formatted_line}</p>")

    if in_list: # Close list if file ends while in list
        html_lines.append("</ul>")

    # Wrap the whole content in a body tag with default font styles
    final_html = f"<body style='font-family: \"{CURRENT_FONT_FAMILY_NAME}\", sans-serif; font-size: {BASE_FONT_SIZE}pt; color: #E0E0E0;'>"
    final_html += "".join(html_lines)
    final_html += "</body>"
    return final_html


# --- Custom Info Popup Dialog ---
class InfoPopupDialog(QDialog):
    def __init__(self, title, html_content, parent=None):
        super().__init__(parent)
        self.setObjectName("InfoPopupDialog")

        # --- Icon Loading (Fallback Removed) ---
        try:
            icon_filename = "Marvel Rivals Dashboard.ico"
            icon_path = resource_path(os.path.join('images', icon_filename))
            if os.path.exists(icon_path):
                self.setWindowIcon(QIcon(icon_path))
            else:
                # Fallback using absolute path REMOVED/COMMENTED OUT
                # raw_path = r"C:\!CODE\MR_Dash\Marvel Rivals Dashboard.ico"
                # if os.path.exists(raw_path):
                #      self.setWindowIcon(QIcon(raw_path))
                # else:
                # Silently ignore if icon not found for dialog
                pass
        except Exception as e:
             print(f"ERROR setting dialog icon: {e}")
        # --- END Icon Loading ---

        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.WindowTitleHint | Qt.WindowType.WindowCloseButtonHint | Qt.WindowType.WindowSystemMenuHint)
        self.setWindowTitle(title)
        self.setModal(True)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(10, 10, 10, 10)
        self.layout.setSpacing(8)
        self.scroll_area = QScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll_area.setObjectName("PopupScrollArea")
        self.scroll_area.setFrameShape(QFrame.Shape.StyledPanel)
        self.content_widget = ZoomableTextWidget(html_content, base_font_size_pt=BASE_FONT_SIZE, parent=self.scroll_area)
        self.scroll_area.setWidget(self.content_widget)
        self.layout.addWidget(self.scroll_area, 1)
        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        self.button_box.rejected.connect(self.reject)
        self.layout.addWidget(self.button_box)
        self.setMinimumSize(600, 400)
        self.resize(750, 600)
    # --- End of __init__ method ---
    

# --- Zoomable Text Widget ---
class ZoomableTextWidget(QTextBrowser): # <<< Base class
    def __init__(self, initial_html="", base_font_size_pt=BASE_FONT_SIZE, parent=None):
        super().__init__(parent) # <<< Super call
        self._base_font_size_pt = base_font_size_pt # Store the default size
        self._current_font_size_pt = base_font_size_pt # Start at default
        self._font_family_name = CURRENT_FONT_FAMILY_NAME
        self._raw_html_content = "" # For storing raw HTML

        self.setReadOnly(True)
        self.setOpenExternalLinks(True)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setObjectName("ZoomableTextWidget")
        self.document().contentsChanged.connect(self.adjust_height)
        self._original_resizeEvent = self.resizeEvent
        self.resizeEvent = self._custom_resizeEvent
        self._update_font()

        size_policy = self.sizePolicy()
        size_policy.setVerticalPolicy(QSizePolicy.Policy.Preferred)
        size_policy.setHorizontalPolicy(QSizePolicy.Policy.Expanding)
        self.setSizePolicy(size_policy)

        self.setHtmlWithBaseSize(initial_html)

    def _custom_resizeEvent(self, event):
        self._original_resizeEvent(event)
        QTimer.singleShot(0, self.adjust_height)

    def _update_font(self):
        font = self.font()
        font.setFamily(self._font_family_name)
        font.setPointSize(self._current_font_size_pt)
        self.setFont(font)
        QTimer.singleShot(0, self.adjust_height)

    def setHtmlWithBaseSize(self, html_text):
        self._raw_html_content = html_text # Store raw HTML
        self.document().blockSignals(True)
        quoted_font_family = f'"{self._font_family_name}"' if ' ' in self._font_family_name else self._font_family_name
        styled_html = f"""<body style='font-family: {quoted_font_family}, sans-serif; font-size: {self._current_font_size_pt}pt; color: #E0E0E0;'>{html_text}</body>"""
        super().setHtml(styled_html)
        self.document().blockSignals(False)
        QTimer.singleShot(0, self.adjust_height)

    def _reset_zoom(self):
        """Internal logic to reset zoom if needed."""
        # Check if already at base size
        if abs(self._current_font_size_pt - self._base_font_size_pt) < 0.1:
            if DEBUG_MODE: print("DEBUG ResetZoom: Already at base size.")
            return False # Indicate no change was made

        if DEBUG_MODE:
            print(f"DEBUG ResetZoom: Resetting from {self._current_font_size_pt:.1f} to {self._base_font_size_pt:.1f}")

        # Save View State BEFORE changing font
        cursor = self.textCursor()
        position_in_document = cursor.position()
        h_scrollbar = self.horizontalScrollBar()
        h_max = h_scrollbar.maximum()
        h_scroll_ratio = (h_scrollbar.value() / h_max) if h_max > 0 else 0.0
        if DEBUG_MODE:
            print(f"DEBUG ResetZoom: Saved state - CursorPos: {position_in_document}, HScrollRatio: {h_scroll_ratio:.3f} (Max: {h_max})")

        # Update Font Size to Base and Re-render
        self._current_font_size_pt = self._base_font_size_pt
        if hasattr(self, '_raw_html_content'):
            self.setHtmlWithBaseSize(self._raw_html_content)
            # Restore View State AFTER document update (using Timer)
            QTimer.singleShot(0, lambda pos=position_in_document, ratio=h_scroll_ratio: self._restore_view_state(pos, ratio))
            return True # Indicate change was made
        else:
            print("WARN ResetZoom: _raw_html_content not found. Cannot reset.")
            return False

    # --- NEW: Handle Middle Mouse Button Click ---
    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.MiddleButton:
            if self._reset_zoom():
                event.accept() # Consume the event if reset happened
                return
        # If not middle button or reset didn't happen, pass event to base class
        super().mousePressEvent(event)

    # --- NEW: Handle Ctrl+R Key Press ---
    def keyPressEvent(self, event: QKeyEvent):
        # Check for Ctrl+R combination
        if event.modifiers() == Qt.KeyboardModifier.ControlModifier and event.key() == Qt.Key.Key_R:
            if self._reset_zoom():
                event.accept() # Consume the event if reset happened
                return
        # If not Ctrl+R or reset didn't happen, pass event to base class
        super().keyPressEvent(event)

    # --- Existing Wheel Event for Zooming ---
    def wheelEvent(self, event: QWheelEvent):
        if event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            delta = event.angleDelta().y()
            zoom_factor = 1.1 if delta > 0 else 1 / 1.1
            new_font_size = max(6.0, min(72.0, self._current_font_size_pt * zoom_factor))

            if abs(new_font_size - self._current_font_size_pt) > 0.1:
                if DEBUG_MODE:
                    print(f"DEBUG Zoom: Ctrl+Scroll. Delta: {delta}. OldSize: {self._current_font_size_pt:.1f}, NewSize: {new_font_size:.1f}")

                cursor = self.textCursor()
                position_in_document = cursor.position()
                h_scrollbar = self.horizontalScrollBar()
                h_max = h_scrollbar.maximum()
                h_scroll_ratio = (h_scrollbar.value() / h_max) if h_max > 0 else 0.0
                if DEBUG_MODE:
                    print(f"DEBUG Zoom: Saved state - CursorPos: {position_in_document}, HScrollRatio: {h_scroll_ratio:.3f} (Max: {h_max})")

                self._current_font_size_pt = new_font_size
                if hasattr(self, '_raw_html_content'):
                    self.setHtmlWithBaseSize(self._raw_html_content)
                    QTimer.singleShot(0, lambda pos=position_in_document, ratio=h_scroll_ratio: self._restore_view_state(pos, ratio))
                else:
                    print("WARN Zoom: _raw_html_content not found. Updating font directly (may lose view state).")
                    self._update_font()

            event.accept()
        else:
            super().wheelEvent(event)

    # --- Existing View State Restoration ---
    def _restore_view_state(self, position_in_document, h_scroll_ratio):
        # (This method remains unchanged from the previous version that fixed zoom)
        action_type = "Zoom/Reset" # Generic term for logging source
        if DEBUG_MODE:
            print(f"DEBUG {action_type} Restore: Attempting state restore CursorPos:{position_in_document}, HScrollRatio:{h_scroll_ratio:.3f}")
        try:
            if not self or not QApplication.instance():
                if DEBUG_MODE: print(f"DEBUG {action_type} Restore: Widget or App instance is invalid. Aborting.")
                return

            # --- Part 1: Restore Horizontal Scroll ---
            h_scrollbar = self.horizontalScrollBar()
            if h_scrollbar:
                h_min = h_scrollbar.minimum()
                h_max = h_scrollbar.maximum()
                new_h_value = int(h_scroll_ratio * (h_max - h_min) + h_min) if h_max > h_min else h_min
                if DEBUG_MODE:
                    print(f"DEBUG {action_type} Restore: HScroll - Min:{h_min}, Max:{h_max}, TargetRatio:{h_scroll_ratio:.3f}, CalculatedValue:{new_h_value}")
                if h_max > h_min:
                    h_scrollbar.setValue(new_h_value)
                    if DEBUG_MODE: print(f"DEBUG {action_type} Restore: HScroll value set to {new_h_value}")
                elif DEBUG_MODE:
                    print(f"DEBUG {action_type} Restore: HScroll not set (max <= min)")
            elif DEBUG_MODE:
                print(f"DEBUG {action_type} Restore: Horizontal scrollbar not found.")

            # --- Part 2: Restore Cursor Position ---
            cursor = self.textCursor()
            doc_length = self.document().characterCount() - 1
            safe_position = max(0, min(position_in_document, doc_length))
            if safe_position != position_in_document and DEBUG_MODE:
                print(f"DEBUG {action_type} Restore: Clamped cursor position from {position_in_document} to {safe_position} (Doc Length: {doc_length})")
            cursor.setPosition(safe_position)
            self.setTextCursor(cursor)
            if DEBUG_MODE: print(f"DEBUG {action_type} Restore: Cursor position set to {safe_position}")

            # --- Part 3: Ensure Cursor is Visible ---
            self.ensureCursorVisible()
            if DEBUG_MODE: print(f"DEBUG {action_type} Restore: Called ensureCursorVisible().")

        except RuntimeError as e:
            if 'Internal C++ object' in str(e) and 'already deleted' in str(e):
                print(f"WARN {action_type} Restore: Widget was deleted before view state could be restored: {e}")
            else:
                print(f"ERROR {action_type} Restore: Unexpected RuntimeError: {e}")
                raise
        except Exception as e:
             print(f"ERROR during {action_type} view state restore: {e}")
             import traceback
             traceback.print_exc()

    # --- Existing Height Adjustment ---
    @Slot()
    def adjust_height(self):
        calculated_height = self.document().size().height()
        margins = self.contentsMargins()
        padding = 4 * 2 # Example
        border = 1 * 2 # Example
        new_exact_height = int(calculated_height + margins.top() + margins.bottom() + padding + border)

        current_min_height = self.minimumHeight()
        current_max_height = self.maximumHeight()
        if abs(current_min_height - new_exact_height) > 1 or abs(current_max_height - new_exact_height) > 1:
            if DEBUG_MODE:
                print(f"DEBUG AdjustHeight: '{self.objectName()}' changing height from Min:{current_min_height}/Max:{current_max_height} to {new_exact_height} (DocHeight: {calculated_height:.1f})")
            self.setMinimumHeight(new_exact_height)
            self.setMaximumHeight(new_exact_height)
            parent = self.parentWidget()
            if parent:
                parent.updateGeometry()
                if parent.layout():
                    parent.layout().activate()

    def __init__(self, initial_html="", base_font_size_pt=BASE_FONT_SIZE, parent=None):
        super().__init__(parent) # <<< Changed super call
        self._base_font_size_pt = base_font_size_pt
        self._current_font_size_pt = base_font_size_pt
        self._font_family_name = CURRENT_FONT_FAMILY_NAME
        self._raw_html_content = "" # <<< ADDED THIS LINE for storing raw HTML

        self.setReadOnly(True) # Keep read-only
        self.setOpenExternalLinks(True) # <<< IMPORTANT: Tell QTextBrowser to open links!
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        # self.setWordWrapMode(...) # QTextBrowser usually wraps by default

        self.setObjectName("ZoomableTextWidget")

        # --- REMOVE the anchorClicked connection ---
        # self.anchorClicked.connect(self._handle_link_click) # Already removed in your provided code

        self.document().contentsChanged.connect(self.adjust_height)
        self._original_resizeEvent = self.resizeEvent
        self.resizeEvent = self._custom_resizeEvent
        self._update_font()

        size_policy = self.sizePolicy()
        size_policy.setVerticalPolicy(QSizePolicy.Policy.Preferred)
        size_policy.setHorizontalPolicy(QSizePolicy.Policy.Expanding)
        self.setSizePolicy(size_policy)

        self.setHtmlWithBaseSize(initial_html) # This will now store the initial raw html

    # --- Keep _custom_resizeEvent method ---
    def _custom_resizeEvent(self, event):
        self._original_resizeEvent(event)
        # Recalculate height on resize
        QTimer.singleShot(0, self.adjust_height)

    # --- Keep _update_font method ---
    def _update_font(self):
        font = self.font()
        font.setFamily(self._font_family_name)
        font.setPointSize(self._current_font_size_pt)
        self.setFont(font)
        # Font change might affect required height
        QTimer.singleShot(0, self.adjust_height)

    # --- MODIFIED setHtmlWithBaseSize method ---
    def setHtmlWithBaseSize(self, html_text):
        self._raw_html_content = html_text # <<< Store raw HTML
        self.document().blockSignals(True)
        # Ensure the font family is correctly quoted if it contains spaces
        quoted_font_family = f'"{self._font_family_name}"' if ' ' in self._font_family_name else self._font_family_name
        # Construct the styled HTML string including the base font size
        styled_html = f"""<body style='font-family: {quoted_font_family}, sans-serif; font-size: {self._current_font_size_pt}pt; color: #E0E0E0;'>{html_text}</body>"""
        super().setHtml(styled_html) # Use the base class setHtml
        self.document().blockSignals(False)
        # Trigger height adjustment after setting HTML
        QTimer.singleShot(0, self.adjust_height)

    # --- REPLACED wheelEvent method (Zooming) ---
    def wheelEvent(self, event: QWheelEvent):
        # Check if Ctrl key is pressed
        if event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            # --- Zooming Logic ---
            delta = event.angleDelta().y()
            zoom_factor = 1.1 if delta > 0 else 1 / 1.1 # Adjust zoom speed if needed
            # Clamp font size between reasonable limits
            new_font_size = max(6.0, min(72.0, self._current_font_size_pt * zoom_factor))

            # Only proceed if size actually changes significantly to avoid minor fluctuations
            if abs(new_font_size - self._current_font_size_pt) > 0.1:
                if DEBUG_MODE:
                    print(f"DEBUG Zoom: Ctrl+Scroll. Delta: {delta}. OldSize: {self._current_font_size_pt:.1f}, NewSize: {new_font_size:.1f}")

                # --- Save View State BEFORE changing font ---
                cursor = self.textCursor()
                position_in_document = cursor.position()
                h_scrollbar = self.horizontalScrollBar()
                h_max = h_scrollbar.maximum()
                # Calculate ratio robustly, avoiding division by zero
                h_scroll_ratio = (h_scrollbar.value() / h_max) if h_max > 0 else 0.0

                if DEBUG_MODE:
                    print(f"DEBUG Zoom: Saved state - CursorPos: {position_in_document}, HScrollRatio: {h_scroll_ratio:.3f} (Max: {h_max})")

                # --- Update Font Size and Re-render ---
                self._current_font_size_pt = new_font_size

                # Re-set the HTML using the stored raw content and the new base size
                # This automatically triggers _update_font and adjust_height via setHtmlWithBaseSize
                if hasattr(self, '_raw_html_content'):
                    self.setHtmlWithBaseSize(self._raw_html_content)

                    # --- Restore View State AFTER document update (using Timer) ---
                    # Use a timer to allow the document layout to potentially update first
                    QTimer.singleShot(0, lambda pos=position_in_document, ratio=h_scroll_ratio: self._restore_view_state(pos, ratio))
                else:
                    # Fallback: just update the font if raw content wasn't stored somehow
                    print("WARN Zoom: _raw_html_content not found. Updating font directly (may lose view state).")
                    self._update_font() # This won't re-parse HTML styles, less ideal

            # Accept the event to prevent parent (ScrollArea) from scrolling
            event.accept()

        else:
            # --- Normal Scrolling ---
            # Pass event to parent (QScrollArea) for standard vertical scrolling
            super().wheelEvent(event)

    # --- Keep _restore_view_state method (Handles cursor and HScroll) ---
    def _restore_view_state(self, position_in_document, h_scroll_ratio):
        """Restores horizontal scroll and text cursor position."""
        if DEBUG_MODE:
            print(f"DEBUG Zoom Restore: Attempting state restore CursorPos:{position_in_document}, HScrollRatio:{h_scroll_ratio:.3f}")
        try:
            # Check widget validity before proceeding
            if not self or not QApplication.instance():
                if DEBUG_MODE: print("DEBUG Zoom Restore: Widget or App instance is invalid. Aborting.")
                return

            # --- Part 1: Restore Horizontal Scroll Position ---
            h_scrollbar = self.horizontalScrollBar()
            if h_scrollbar: # Check if scrollbar exists
                h_min = h_scrollbar.minimum()
                h_max = h_scrollbar.maximum()
                # Calculate target scroll value based on ratio
                new_h_value = int(h_scroll_ratio * (h_max - h_min) + h_min) if h_max > h_min else h_min

                if DEBUG_MODE:
                    print(f"DEBUG Zoom Restore: HScroll - Min:{h_min}, Max:{h_max}, TargetRatio:{h_scroll_ratio:.3f}, CalculatedValue:{new_h_value}")

                # Only set value if the scrollbar is actually scrollable
                if h_max > h_min:
                    h_scrollbar.setValue(new_h_value)
                    if DEBUG_MODE: print(f"DEBUG Zoom Restore: HScroll value set to {new_h_value}")
                elif DEBUG_MODE:
                    print(f"DEBUG Zoom Restore: HScroll not set (max <= min)")
            elif DEBUG_MODE:
                print("DEBUG Zoom Restore: Horizontal scrollbar not found.")


            # --- Part 2: Restore Cursor Position ---
            cursor = self.textCursor() # Get a fresh cursor object
            doc_length = self.document().characterCount() - 1 # Max valid position index
            # Clamp the desired position to be within the valid document range
            safe_position = max(0, min(position_in_document, doc_length))

            if safe_position != position_in_document and DEBUG_MODE:
                if DEBUG_MODE: print(f"DEBUG Zoom Restore: Clamped cursor position from {position_in_document} to {safe_position} (Doc Length: {doc_length})")

            cursor.setPosition(safe_position)
            self.setTextCursor(cursor) # Apply the cursor to the widget
            if DEBUG_MODE: print(f"DEBUG Zoom Restore: Cursor position set to {safe_position}")


            # --- Part 3: Ensure Cursor is Visible (CRITICAL for scrolling view) ---
            # This tells the QTextBrowser to scroll (vertically and horizontally)
            # if necessary to make the current cursor position visible.
            self.ensureCursorVisible()
            if DEBUG_MODE: print(f"DEBUG Zoom Restore: Called ensureCursorVisible().")

            # Optional: Force a repaint/process events if visual updates lag, but often ensureCursorVisible is enough.
            # self.update()
            # QApplication.processEvents() # Use cautiously, can cause flicker

        except RuntimeError as e:
            # Catch error if the C++ object is deleted (e.g., window closed during timer)
            if 'Internal C++ object' in str(e) and 'already deleted' in str(e):
                print(f"WARN Zoom Restore: Widget was deleted before view state could be restored: {e}")
            else:
                # Re-raise other unexpected runtime errors
                print(f"ERROR Zoom Restore: Unexpected RuntimeError: {e}")
                raise # Re-raise the error if it's not the deleted object issue
        except Exception as e:
             # Catch any other exceptions during the restore process
             print(f"ERROR during view state restore: {e}")
             # Optionally add more error handling here, like logging traceback
             import traceback
             traceback.print_exc()


    # --- Keep adjust_height method (Updates widget height based on document) ---
    @Slot()
    def adjust_height(self):
        # Calculate the ideal height based on the document content
        calculated_height = self.document().size().height()

        # Consider margins, padding, and border (these values might depend on your stylesheet)
        margins = self.contentsMargins() # Get widget margins
        # Estimate padding/border (adjust if your QSS defines them differently)
        padding = 4 * 2 # Example: 4px top/bottom padding
        border = 1 * 2 # Example: 1px top/bottom border

        # Calculate total required height
        # Use ceiling function (int() + 1 if not integer, or math.ceil) if fractional heights cause issues
        new_exact_height = int(calculated_height + margins.top() + margins.bottom() + padding + border)

        # Only update if the height has actually changed to avoid unnecessary layout cycles
        current_min_height = self.minimumHeight()
        current_max_height = self.maximumHeight()

        if abs(current_min_height - new_exact_height) > 1 or abs(current_max_height - new_exact_height) > 1:
            if DEBUG_MODE:
                print(f"DEBUG AdjustHeight: '{self.objectName()}' changing height from Min:{current_min_height}/Max:{current_max_height} to {new_exact_height} (DocHeight: {calculated_height:.1f})")
            self.setMinimumHeight(new_exact_height)
            self.setMaximumHeight(new_exact_height)

            # Inform the parent layout that geometry might have changed
            parent = self.parentWidget()
            if parent:
                parent.updateGeometry()
                # Activate the layout to ensure changes propagate
                if parent.layout():
                    parent.layout().activate()

# --- End of ZoomableTextWidget class ---

# --- Clickable Label for Jump Bar ---
class ClickableLabel(QLabel):
    clicked = Signal(str)
    def __init__(self, tooltip_text="", parent=None):
        super().__init__("", parent)
        self.setObjectName("JumpBarLabel")
        self.setToolTip(tooltip_text)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            if DEBUG_MODE: print(f"DEBUG ClickEvent: '{self.toolTip()}' label pressed. Emitting signal.")
            self.clicked.emit(self.toolTip()) # Emit signal with tooltip (char name)
        super().mousePressEvent(event)

# --- Collapsible Group Box ---
class CollapsibleGroupBox(QGroupBox):
    def __init__(self, title="", parent=None, initially_collapsed=False):
        super().__init__(title, parent)
        self._is_collapsed = initially_collapsed
        self._content_widgets = []

        # Create toggle button
        self.toggle_button = QPushButton(self)
        self.toggle_button.setObjectName("CollapseButton")
        self.toggle_button.setCheckable(True)
        self.toggle_button.setChecked(not self._is_collapsed)
        self.toggle_button.setText(self._get_arrow_char())
        self.toggle_button.setToolTip("Expand/Collapse Section")
        self.toggle_button.clicked.connect(self._toggle_button_clicked)
        # Set property for styling based on state
        self.setProperty("collapsed", self._is_collapsed)
        self.setProperty("hasToggleButton", True)

        # Store original margins
        layout = self.layout()
        if layout:
            lm, tm, rm, bm = layout.getContentsMargins()
            self._original_content_margins = (lm, tm, rm, bm)
        else:
            # If no layout yet, assume Qt defaults (may need adjustment based on style)
            self._original_content_margins = (9, 9, 9, 9) # Common default

        # Apply initial state after event loop starts
        QTimer.singleShot(0, self._apply_initial_state)

    def _apply_initial_state(self):
        # Ensure a layout exists before collecting widgets
        if not self.layout():
            layout = QVBoxLayout()
            self.setLayout(layout)
            # print(f"WARN: CollapsibleGroupBox '{self.title()}' had no layout, created QVBoxLayout.") # Less verbose
            lm, tm, rm, bm = layout.contentsMargins() # Get actual margins
            self._original_content_margins = (lm, tm, rm, bm)

        self._collect_content_widgets()
        self._update_visibility_and_layout(self._is_collapsed)

    def _collect_content_widgets(self):
        self._content_widgets.clear()
        layout = self.layout()
        if layout:
            for i in range(layout.count()):
                item = layout.itemAt(i)
                widget = item.widget()
                # Collect widgets that are not the toggle button itself
                if widget and widget != self.toggle_button:
                    self._content_widgets.append(widget)

    def _get_arrow_char(self):
        return "▶" if self._is_collapsed else "▼"

    def _update_visibility_and_layout(self, is_collapsed):
        if not self._content_widgets:
            self._collect_content_widgets() # Ensure widgets are collected

        visible = not is_collapsed
        layout = self.layout()

        # Show/hide content widgets
        for widget in self._content_widgets:
            widget.setVisible(visible)

        # Adjust layout margins for collapsed state
        if layout:
            lm, tm, rm, bm = self._original_content_margins
            if is_collapsed:
                # Use smaller top/bottom margins when collapsed
                layout.setContentsMargins(lm, 2, rm, 2)
            else:
                layout.setContentsMargins(lm, tm, rm, bm) # Restore original margins

        # Adjust size policy and maximum height
        sp = self.sizePolicy()
        if is_collapsed:
            sp.setVerticalPolicy(QSizePolicy.Policy.Fixed)
            # Set max height to minimum hint to prevent expansion
            self.setMaximumHeight(self.minimumSizeHint().height())
        else:
            sp.setVerticalPolicy(QSizePolicy.Policy.Preferred) # Allow vertical expansion
            self.setMaximumHeight(16777215) # Essentially infinite max height

        self.setSizePolicy(sp)
        self.updateGeometry() # Notify layout system of size hint changes

        # Update parent layout
        parent_layout = self.parentWidget().layout() if self.parentWidget() else None
        if parent_layout:
            parent_layout.activate() # Trigger parent layout update

        # Update property for styling
        self.setProperty("collapsed", is_collapsed)
        self.style().unpolish(self)
        self.style().polish(self)


    @Slot(bool)
    def _toggle_button_clicked(self, checked):
        new_collapsed_state = not checked
        if new_collapsed_state != self._is_collapsed:
            self._is_collapsed = new_collapsed_state
            self.toggle_button.setText(self._get_arrow_char())
            self._update_visibility_and_layout(self._is_collapsed)

    def paintEvent(self, event):
        # Let the original QGroupBox paint itself first
        super().paintEvent(event)
        # Manually position the toggle button relative to the title text
        option = QStyleOptionGroupBox()
        self.initStyleOption(option)
        # Get the rectangle occupied by the title label
        title_rect = self.style().subControlRect(QStyle.ComplexControl.CC_GroupBox, option, QStyle.SubControl.SC_GroupBoxLabel, self)
        # Position button slightly to the left of the title text
        btn_x = title_rect.x() - self.toggle_button.width() - 3 # Adjust horizontal offset as needed
        # Ensure button doesn't go off the left edge
        btn_x = max(5, btn_x)
        # Center button vertically within the title's height
        btn_y = title_rect.y() + (title_rect.height() - self.toggle_button.height()) // 2
        self.toggle_button.move(btn_x, btn_y)
        # Ensure button is drawn on top of the group box frame/title
        self.toggle_button.raise_()

    def minimumSizeHint(self):
        if self._is_collapsed:
            option = QStyleOptionGroupBox()
            self.initStyleOption(option)
            # Calculate height based on title rect and approximate margins/padding
            title_rect = self.style().subControlRect(QStyle.ComplexControl.CC_GroupBox, option, QStyle.SubControl.SC_GroupBoxLabel, self)
            # Use layout spacing or pixel metrics for frame/padding approximation
            frame_margin_approx = self.style().pixelMetric(QStyle.PixelMetric.PM_LayoutVerticalSpacing, option, self) * 2
            # Get actual margins if layout exists, else use defaults stored
            lm, tm, rm, bm = self.layout().getContentsMargins() if self.layout() else self._original_content_margins
            # Calculate collapsed height: Title + Top/Bottom Margins + Frame Approximation + Extra Padding
            collapsed_height = title_rect.height() + tm + bm + frame_margin_approx + 4
            return QSize(150, collapsed_height) # Provide a reasonable minimum width
        else:
            # Return the default minimum size hint when expanded
            return super().minimumSizeHint()

    def sizeHint(self):
        # Size hint should reflect minimum size when collapsed
        return self.minimumSizeHint() if self._is_collapsed else super().sizeHint()


# --- Character Card Widget ---
# --- Inside rivals_dashboard.py ---

class CharacterCard(QWidget):
    favorite_toggled = Signal(str, bool)

    def __init__(self, character_name, character_data, is_favorite):
        super().__init__()
        self.character_name = character_name
        # Ensure data is a dict, handle potential None from loading errors
        self.character_data = character_data if isinstance(character_data, dict) else {}
        self._is_favorite = is_favorite
        self.font_family = CURRENT_FONT_FAMILY_NAME
        self.using_custom_font = CUSTOM_FONT_LOADED

        # Safely get nested stats data
        stats_data = self.character_data.get("stats", {}) if isinstance(self.character_data, dict) else {}
        if not isinstance(stats_data, dict): # Ensure stats_data is a dict
            stats_data = {}

        # Get potential color strings
        raw_primary_color = stats_data.get("color_theme")
        raw_secondary_color = stats_data.get("color_theme_secondary")

        # --- START: Added Color Validation ---
        self.primary_theme_color_str = DEFAULT_THEME_COLOR # Default value
        self.primary_theme_color = QColor(DEFAULT_THEME_COLOR)
        if raw_primary_color and isinstance(raw_primary_color, str):
            try:
                test_color = QColor(raw_primary_color)
                if test_color.isValid(): # Check if Qt recognizes the color string
                    self.primary_theme_color_str = raw_primary_color
                    self.primary_theme_color = test_color
                else:
                    print(f"WARN (Card {self.character_name}): Invalid primary color string '{raw_primary_color}'. Using default.")
            except Exception: # Catch potential errors during QColor creation
                 print(f"WARN (Card {self.character_name}): Error creating QColor from primary '{raw_primary_color}'. Using default.")

        self.secondary_theme_color_str = DEFAULT_SECONDARY_THEME_COLOR # Default value
        self.secondary_theme_color = QColor(DEFAULT_SECONDARY_THEME_COLOR)
        if raw_secondary_color and isinstance(raw_secondary_color, str):
             try:
                test_color = QColor(raw_secondary_color)
                if test_color.isValid():
                    self.secondary_theme_color_str = raw_secondary_color
                    self.secondary_theme_color = test_color
                else:
                     print(f"WARN (Card {self.character_name}): Invalid secondary color string '{raw_secondary_color}'. Using default.")
             except Exception:
                  print(f"WARN (Card {self.character_name}): Error creating QColor from secondary '{raw_secondary_color}'. Using default.")
        # --- END: Added Color Validation ---


        self.setObjectName("CharacterCard")
        # Apply base styling using the *validated* primary color property
        self.setProperty("cardBorderColor", self.primary_theme_color_str)
        self.init_ui()
# --- Replace this method inside the CharacterCard class ---
    @Slot()
    def _open_youtube_search(self):
        """Constructs and opens a YouTube search URL for recent character guides."""
        try:
            # Use the global search season string
            search_season = SEARCH_SEASON_STRING # Get the current value

            # Refined search terms <------------EDIT YOUTUBE LINK PARAMETERS HERE
            query_parts = [
                f'"{self.character_name}"', # Exact Character Name
                '"Marvel Rivals"',
                # Add other optional keywords if desired: Gameplay | Tutorial | Tips
                f'"{search_season}"' # Exact Season/Patch String
            ]
            search_query = " ".join(query_parts)

            # URL encode the query
            encoded_query = urllib.parse.quote_plus(search_query)

            # YouTube search URL base
            base_url = "https://www.youtube.com/results"

            # Add the "Past Month" filter (still unreliable, but we try)
            time_filter_param = "EgIIAw%253D%253D"
            search_url = f"{base_url}?search_query={encoded_query}&sp={time_filter_param}"

            print(f"Constructed YouTube Search URL: {search_url}")
            QDesktopServices.openUrl(QUrl(search_url))

        except Exception as e:
            print(f"Error constructing or opening YouTube URL: {e}")
            QMessageBox.warning(self, "Search Error", f"Could not open YouTube search.\nError: {e}")
# --- End Replace Method ---
    # ... (rest of CharacterCard class, including init_ui) ...
    
    # --- Helper methods (Keep _create_zoomable_widget, _add_widget_if_data, _add_field_label, _add_list_as_bullets, _create_section_group) ---
    def _create_zoomable_widget(self, html_content):
        # Check if content is meaningful (not just whitespace or empty tags)
        has_real_content = bool(html_content and re.search(r"\S", re.sub('<[^>]*>', '', html_content)))
        return ZoomableTextWidget(html_content, base_font_size_pt=BASE_FONT_SIZE) if has_real_content else None

    def _add_widget_if_data(self, layout, widget):
        if widget: layout.addWidget(widget); return True
        return False

    def _add_field_label(self, layout, label_text, value):
        # Check if value is not None and its string representation is not empty/whitespace
        if value is not None and str(value).strip():
            label = QLabel(f"<span style='{FIELD_LABEL_STYLE}'>{label_text}:</span> <span style='{FIELD_VALUE_STYLE}'>{value}</span>")
            label.setTextFormat(Qt.TextFormat.RichText); label.setWordWrap(True)
            label.setFont(QFont(self.font_family, BASE_FONT_SIZE)); layout.addWidget(label); return True
        return False

    def _add_list_as_bullets(self, layout, title, data_list, is_sub_list=False):
        valid_items = [item for item in data_list if item is not None and str(item).strip()] if isinstance(data_list, list) else []
        if valid_items:
            if not is_sub_list:
                 title_label = QLabel(f"<span style='{FIELD_LABEL_STYLE}'>{title}:</span>")
                 title_label.setFont(QFont(self.font_family, BASE_FONT_SIZE)); title_label.setTextFormat(Qt.TextFormat.RichText); layout.addWidget(title_label)
            html = f"<ul style='{LIST_ITEM_STYLE} margin-top: 0px;'>" + "".join(f"<li>{item}</li>" for item in valid_items) + "</ul>"
            widget = self._create_zoomable_widget(html)
            return self._add_widget_if_data(layout, widget)
        return False

    # Inside the CharacterCard class

    def _create_section_group(self, title, collapsible=False, initially_collapsed=False):
        """Creates either a standard QGroupBox or a CollapsibleGroupBox."""

        # --- CORRECTED INSTANTIATION ---
        if collapsible:
            # Create a CollapsibleGroupBox, passing initially_collapsed
            group = CollapsibleGroupBox(title, parent=self, initially_collapsed=initially_collapsed)
        else:
            # Create a standard QGroupBox (doesn't accept initially_collapsed)
            group = QGroupBox(title, parent=self)
        # --- END CORRECTION ---

        # --- Font and Stylesheet (Apply to whichever group was created) ---
        title_font = QFont(self.font_family, GROUP_TITLE_FONT_SIZE)
        title_font.setWeight(QFont.Weight.Bold)
        group.setFont(title_font)

        # Dynamically get the class name for the stylesheet
        group_class_name = group.__class__.__name__
        group.setStyleSheet(f"""
            {group_class_name} {{
                margin-top: 8px;
                border: 1px solid {self.primary_theme_color.darker(120).name()};
                padding-top: 15px;
            }}
            {group_class_name}::title {{
                color: {self.primary_theme_color_str};
                subcontrol-origin: margin;
                subcontrol-position: top left; /* Keep aligned left */
                padding: 0 5px 0 5px; /* Horizontal padding for title */
                margin-left: 5px; /* Offset title slightly */
            }}
        """)

        # --- Layout (Apply to whichever group was created) ---
        layout = QVBoxLayout()
        layout.setSpacing(4)
        # Consistent margins applied to the layout within the group box
        layout.setContentsMargins(6, 10, 6, 6)
        group.setLayout(layout)

        return group, layout
    

    # --- Formatting methods (Keep _format_ability_html, _format_ultimate_html, _format_passive_html, _format_teamup_html, _format_achievement_html, _format_hero_story_html, _format_balance_change_html) ---
    def _format_ability_html(self, ability_dict):
        if not ability_dict or not isinstance(ability_dict, dict): return ""
        html = ""; name = ability_dict.get("name"); keybind = ability_dict.get("keybind"); title_str = name if name else "Unnamed Ability"
        if keybind: title_str += f" ({keybind})"
        html += f"<p><span style='{ABILITY_TITLE_STYLE_TEMPLATE.format(color=self.secondary_theme_color_str)}'>{title_str}</span></p>"
        details_list = []

        # Define fields and process them
        fields_to_process = {
            "Type": ability_dict.get("type"),
            "Description": ability_dict.get("description"), # <-- Potential multi-line
            "Casting": ability_dict.get("casting"),
            "Damage": ability_dict.get("damage"),
            "Damage Falloff": ability_dict.get("damage_falloff"),
            "Fire Rate/Interval": ability_dict.get("fire_rate_interval"),
            "Ammo": ability_dict.get("ammo"),
            "Critical Hit": ability_dict.get("critical_hit"),
            "Cooldown": ability_dict.get("cooldown"),
            "Range": ability_dict.get("range"),
            "Projectile Speed": ability_dict.get("projectile_speed"),
            "Charges": ability_dict.get("charges"),
            "Duration": ability_dict.get("duration"),
            "Movement Boost": ability_dict.get("movement_boost"),
            "Energy Cost": ability_dict.get("energy_cost_details"),
            "Details": ability_dict.get("details") # <-- Potential multi-line
        }

        for label, value in fields_to_process.items():
            if value is not None and str(value).strip():
                # Handle boolean specifically
                if label == "Critical Hit" and isinstance(value, bool):
                    display_value = "Yes" if value else "No"
                else:
                    # Convert to string and replace newlines for all other text
                    display_value = str(value).replace('\n', '<br>') # <<< MODIFIED LINE

                details_list.append(f"<span style='{FIELD_LABEL_STYLE}'>{label}:</span> <span style='{FIELD_VALUE_STYLE}'>{display_value}</span>")

        if details_list: html += "<p style='margin-left: 10px; margin-top: 2px;'>" + "<br/>".join(details_list) + "</p>"
        # Return empty string if only title was present but no details found
        return html if details_list else "" # Adjusted return condition slightly



    def _format_ultimate_html(self, ult_dict):
        if not ult_dict or not isinstance(ult_dict, dict): return ""
        html = ""; name = ult_dict.get("name"); keybind = ult_dict.get("keybind"); title_str = name if name else "Unnamed Ultimate"
        if keybind: title_str += f" ({keybind})"
        html += f"<p><span style='{ABILITY_TITLE_STYLE_TEMPLATE.format(color=self.secondary_theme_color_str)}'>{title_str}</span></p>"
        details_list = []

        # Define fields and process them
        fields_to_process = {
            "Type": ult_dict.get("type"),
            "Description": ult_dict.get("description"), # <-- Potential multi-line
            "Casting": ult_dict.get("casting"),
            "Damage": ult_dict.get("damage"),
            "Range": ult_dict.get("range"),
            "Effect": ult_dict.get("effect"), # <-- Potential multi-line
            "Duration": ult_dict.get("duration"),
            "Health on Revive": ult_dict.get("health_upon_revival"),
            "Slow Rate": ult_dict.get("slow_rate"),
            "Projectile Speed": ult_dict.get("projectile_speed"),
            "Movement Boost": ult_dict.get("movement_boost"), # <-- Potential multi-line
            "Bonus Health": ult_dict.get("bonus_health_details"), # <-- Potential multi-line
            "Energy Cost": ult_dict.get("energy_cost"),
            "Details": ult_dict.get("details") # <-- Potential multi-line
        }

        for label, value in fields_to_process.items():
             if value is not None and str(value).strip():
                # Convert to string and replace newlines
                display_value = str(value).replace('\n', '<br>') # <<< MODIFIED LINE
                details_list.append(f"<span style='{FIELD_LABEL_STYLE}'>{label}:</span> <span style='{FIELD_VALUE_STYLE}'>{display_value}</span>")

        if details_list: html += "<p style='margin-left: 10px; margin-top: 2px;'>" + "<br/>".join(details_list) + "</p>"
        return html if details_list else "" # Adjusted return conditioN


    def _format_passive_html(self, passive_dict):
        if not passive_dict or not isinstance(passive_dict, dict): return ""
        html = ""; name = passive_dict.get("name"); keybind = passive_dict.get("keybind"); title_str = name if name else "Unnamed Passive/Melee"
        if keybind: title_str += f" ({keybind})"
        html += f"<p><span style='{ABILITY_TITLE_STYLE_TEMPLATE.format(color=self.secondary_theme_color_str)}'>{title_str}</span></p>"
        details_list = []

        # Define fields and process them
        fields_to_process = {
            "Type": passive_dict.get("type"),
            "Description": passive_dict.get("description"), # <-- Potential multi-line
            "Cooldown": passive_dict.get("cooldown"),
            "Damage": passive_dict.get("damage"),
            "Range": passive_dict.get("range"),
            "Trigger Condition": passive_dict.get("trigger_condition"), # <-- Potential multi-line
            "Effect/Boost": passive_dict.get("effect_boost"), # <-- Potential multi-line
            "Speed Details": passive_dict.get("speed_details"), # <-- Potential multi-line
            "Details": passive_dict.get("details") # <-- Potential multi-line
        }

        for label, value in fields_to_process.items():
            if value is not None and str(value).strip():
                # Convert to string and replace newlines
                display_value = str(value).replace('\n', '<br>') # <<< MODIFIED LINE
                details_list.append(f"<span style='{FIELD_LABEL_STYLE}'>{label}:</span> <span style='{FIELD_VALUE_STYLE}'>{display_value}</span>")

        if details_list: html += "<p style='margin-left: 10px; margin-top: 2px;'>" + "<br/>".join(details_list) + "</p>"
        return html if details_list else "" # Adjusted return condition
    
    
    def _format_teamup_html(self, teamup_dict):
        if not teamup_dict or not isinstance(teamup_dict, dict): return ""
        html = ""; name = teamup_dict.get("name"); keybind = teamup_dict.get("keybind"); title_str = name if name else "Unnamed Team-Up"
        if keybind: title_str += f" ({keybind})"
        html += f"<p><span style='{ABILITY_TITLE_STYLE_TEMPLATE.format(color=self.secondary_theme_color_str)}'>{title_str}</span></p>"
        details_list = []

        # Handle Partner first
        partner = teamup_dict.get("partner"); partner_str = ""
        if isinstance(partner, list): partner_str = ", ".join(p for p in partner if p)
        elif isinstance(partner, str) and partner: partner_str = partner
        if partner_str: details_list.append(f"<span style='{FIELD_LABEL_STYLE}'>Partner(s):</span> <span style='{FIELD_VALUE_STYLE}'>{partner_str}</span>") # Partner name unlikely multi-line

        # Define other fields
        fields_to_process = {
            "Effect": teamup_dict.get("effect"), # <-- Potential multi-line
            "Team-Up Bonus": teamup_dict.get("teamup_bonus"), # <-- Potential multi-line
            "Duration": teamup_dict.get("duration"),
            "Cooldown": teamup_dict.get("cooldown"),
            "Range/Target": teamup_dict.get("range_target"),
            "Special Notes": teamup_dict.get("special_notes"), # <-- Potential multi-line
            "Details": teamup_dict.get("details") # <-- Potential multi-line
        }

        for label, value in fields_to_process.items():
            if value is not None and str(value).strip():
                 # Convert to string and replace newlines
                display_value = str(value).replace('\n', '<br>') # <<< MODIFIED LINE
                details_list.append(f"<span style='{FIELD_LABEL_STYLE}'>{label}:</span> <span style='{FIELD_VALUE_STYLE}'>{display_value}</span>")

        if details_list: html += "<p style='margin-left: 10px; margin-top: 2px;'>" + "<br/>".join(details_list) + "</p>"
        # Return empty string if only title was present but no details found (incl partner)
        return html if details_list else ""

    

    def _format_achievement_html(self, ach_dict):
         if not ach_dict or not isinstance(ach_dict, dict): return ""
         name = ach_dict.get("name"); desc = ach_dict.get("description"); points = ach_dict.get("points"); html = ""
         if not name and not desc: return "" # Skip if both missing

         if name: # Name unlikely multi-line
             html += f"<p><span style='{FIELD_LABEL_STYLE}'>{name}</span>";
             html += (f" ({points} Pts)" if points is not None else "");
             html += "</p>"
         if desc:
             display_desc = str(desc).replace('\n', '<br>') # <<< MODIFIED LINE
             html += f"<p style='margin-left: 15px; margin-top: 1px; {FIELD_VALUE_STYLE}'>{display_desc}</p>"
         return html



    def _format_hero_story_html(self, story_dict):
         if not story_dict or not isinstance(story_dict, dict): return ""
         title = story_dict.get("title"); content = story_dict.get("content"); status = story_dict.get("status"); html = ""
         if not title and not content: return "" # Skip if both missing

         if title: # Title unlikely multi-line
             html = f"<p><span style='{FIELD_LABEL_STYLE}'>{title}</span></p>"
         if content:
             display_content = str(content).replace('\n', '<br>') # <<< MODIFIED LINE
             # Use div for potential block content, apply style directly
             html += f"<div style='margin-left: 15px; margin-top: 1px; {FIELD_VALUE_STYLE}'>{display_content}</div>"
         if status: # Status unlikely multi-line
             html += f"<p style='margin-left: 15px; font-style: italic; color: {DETAILS_COLOR};'>{status}</p>"
         return html


    def _format_balance_change_html(self, change_dict):
         if not change_dict or not isinstance(change_dict, dict): return ""
         date_version = change_dict.get("date_version"); changes = change_dict.get("changes")
         if not date_version or not changes or not isinstance(changes, list): return ""
         valid_changes = [c for c in changes if c and isinstance(c, str) and c.strip()]
         if not valid_changes: return ""
         html = f"<p><span style='{FIELD_LABEL_STYLE}'>{date_version}:</span></p>"
         html += f"<ul style='{LIST_ITEM_STYLE}'>" + "".join(f"<li>{change}</li>" for change in valid_changes) + "</ul>"
         return html
    
    
    def _make_text_links_clickable(self, raw_text):
        """Finds URLs in plain text and converts them to clickable HTML links."""
        if not raw_text:
            return ""

        # Regex to find URLs (handles http, https, www.) - same as in _format_info_text
        url_pattern = re.compile(r'(\b(?:https?://|www\.)[^\s<>()"\']+)', re.IGNORECASE)

        # Internal function to create the <a> tag for a URL match
        def replace_url(match):
            url = match.group(1)
            # Basic HTML entity escaping for the displayed URL text
            display_url = url.replace('&', '&').replace('<', '<').replace('>', '>')
            # Ensure www links get http:// prepended for the href
            href = url if url.startswith(('http://', 'https://')) else 'http://' + url
            # Style the link blue and underlined (adjust color if needed)
            link_style = "color:#77C4FF; text-decoration: underline;"
            return f'<a href="{href}" style="{link_style}">{display_url}</a>'

        # Escape potential HTML in the text BEFORE applying links
        # This prevents accidental HTML injection if text contains < > &
        text_escaped = raw_text.replace('&', '&').replace('<', '<').replace('>', '>')

        # Substitute found URLs with the replace_url function
        linked_text = url_pattern.sub(replace_url, text_escaped)
        return linked_text
# --- END OF NEW METHOD ---

    # --- init_ui - MODIFIED ---
    def init_ui(self):
        main_layout = QVBoxLayout(self); main_layout.setSpacing(12)
        # Base card styling
        self.setStyleSheet(f""" CharacterCard {{ border: 2px solid {self.primary_theme_color_str}; border-radius: 8px; padding: 10px; background-color: #282828; }} """)

        # --- Header ---
        # (Header code remains exactly the same - paste your working version here)
        header_widget = QWidget()
        header_layout = QGridLayout(header_widget)
        header_layout.setSpacing(10)
        header_layout.setContentsMargins(0, 0, 0, 5) # Add bottom margin
        header_layout.setColumnStretch(1, 1) # Allow middle column (name/stats) to stretch

        # Image Label (Column 0)
        img_label = QLabel()
        img_label.setObjectName("CharacterImageLabel")
        img_label.setAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignTop)
        img_filename = get_config_value_flexible(CHARACTER_IMAGE_MAP, self.character_name)
        img_full_path = os.path.join(IMAGE_FOLDER, img_filename) if img_filename else None
        img_found = False
        max_height = 180
        if img_full_path and os.path.exists(img_full_path):
            full_pixmap = QPixmap(img_full_path)
            if not full_pixmap.isNull():
                full_width = full_pixmap.width(); full_height = full_pixmap.height()
                target_crop_width = min(full_width, int(full_width * 0.60)); target_crop_width = max(1, target_crop_width)
                crop_x = max(0, (full_width - target_crop_width) // 2); crop_y = 0
                crop_rect = QRect(crop_x, crop_y, target_crop_width, full_height)
                cropped_pixmap = full_pixmap.copy(crop_rect)
                if not cropped_pixmap.isNull():
                    display_pixmap = cropped_pixmap.scaled(QSize(target_crop_width * 2, max_height), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                    img_label.setPixmap(display_pixmap); img_found = True
                else: # Fallback if crop fails
                    display_pixmap = full_pixmap.scaled(QSize(500, max_height), Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    img_label.setPixmap(display_pixmap); img_found = True
        if not img_found:
            img_label.setText(f"Image Missing:\n{img_filename or 'Not Mapped'}")
            img_label.setObjectName("ImageNotFoundLabel"); img_label.setStyleSheet(f"color: {DETAILS_COLOR}; font-style: italic;")
            img_label.setMinimumHeight(int(max_height * 0.8)); img_label.setMaximumHeight(max_height)
        img_label.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        img_label.setFixedHeight(max_height)
        header_layout.addWidget(img_label, 0, 0, 2, 1, Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)

        # Name and Stats (Column 1)
        name_stats_vbox = QVBoxLayout(); name_stats_vbox.setSpacing(3); name_stats_vbox.setAlignment(Qt.AlignmentFlag.AlignTop)
        name_label = QLabel(self.character_name); name_label.setObjectName("CharacterNameLabel")
        name_font = QFont(self.font_family, CHARACTER_NAME_FONT_SIZE); name_font.setWeight(QFont.Weight.Black)
        name_label.setFont(name_font); name_label.setStyleSheet(f"color: {self.primary_theme_color_str};")
        name_stats_vbox.addWidget(name_label)
        stats_layout = QVBoxLayout(); stats_layout.setSpacing(1); stats_layout.setContentsMargins(5, 0, 0, 0)
        role = self.character_data.get('role')
        if role:
             role_label = QLabel(f"<span style='{FIELD_LABEL_STYLE}'>Role:</span> <span style='{FIELD_VALUE_STYLE}'>{role}</span>")
             role_label.setObjectName("RoleLabel"); role_font = QFont(self.font_family, HEADER_FONT_SIZE)
             role_label.setFont(role_font); role_label.setTextFormat(Qt.TextFormat.RichText); stats_layout.addWidget(role_label)

        # --- Define stat_font EARLY ---
        stat_font = QFont(self.font_family, HEADER_FONT_SIZE)
        # --- END Define stat_font EARLY ---

        # Add Tier from Meta Stats (AFTER Role)
        meta_stats_data = self.character_data.get("meta_stats", {})
        if isinstance(meta_stats_data, dict):
            tier = meta_stats_data.get('tier')
            if tier and str(tier).strip(): # Only add if tier exists and is not empty/whitespace
                tier_label = QLabel(f"<span style='{FIELD_LABEL_STYLE}'>Tier:</span> <span style='{FIELD_VALUE_STYLE}'>{tier}</span>")
            tier_label.setObjectName("StatLabel") # Reuse stat label styling
            tier_label.setFont(stat_font) # Reuse stat font (same as health/difficulty)
            tier_label.setTextFormat(Qt.TextFormat.RichText)
            stats_layout.addWidget(tier_label) # Add to the same layout as role/health

        stats_data = self.character_data.get("stats", {})
        if isinstance(stats_data, dict):
            health = stats_data.get('health'); speed = stats_data.get('speed'); difficulty = stats_data.get('difficulty')
            if health is not None:
             health_label = QLabel(f"<span style='{FIELD_LABEL_STYLE}'>Health:</span> <span style='{FIELD_VALUE_STYLE}'>{health}</span>")
             health_label.setObjectName("StatLabel"); health_label.setFont(stat_font); health_label.setTextFormat(Qt.TextFormat.RichText); stats_layout.addWidget(health_label)
            if difficulty:
             difficulty_label = QLabel(f"<span style='{FIELD_LABEL_STYLE}'>Difficulty:</span> <span style='{FIELD_VALUE_STYLE}'>{difficulty}</span>")
             difficulty_label.setObjectName("StatLabel"); difficulty_label.setFont(stat_font); difficulty_label.setTextFormat(Qt.TextFormat.RichText); stats_layout.addWidget(difficulty_label)
        name_stats_vbox.addLayout(stats_layout); name_stats_vbox.addStretch(1)
        header_layout.addLayout(name_stats_vbox, 0, 1, 2, 1, Qt.AlignmentFlag.AlignTop)

        # Buttons (Column 2)
        buttons_vbox = QVBoxLayout(); buttons_vbox.setSpacing(5); buttons_vbox.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight)
        self.fav_button = QPushButton(); self.fav_button.setObjectName("FavoriteButton"); self.fav_button.setCheckable(True)
        self.fav_button.setFixedSize(QSize(30, 30)); self.fav_button.setToolTip("Toggle Favorite")
        self.fav_button.clicked.connect(self.toggle_favorite_button); self.update_favorite_button_style()
        buttons_vbox.addWidget(self.fav_button)
        self.youtube_button = QPushButton("Video Guides"); self.youtube_button.setObjectName("LinkButton")
        youtube_button_font = QFont(self.font_family, BASE_FONT_SIZE - 1)
        self.youtube_button.setFont(youtube_button_font)
        self.youtube_button.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
        self.youtube_button.setFixedHeight(25)
        self.youtube_button.setToolTip(f"Search YouTube for {SEARCH_SEASON_STRING} guides") # Updated tooltip
        self.youtube_button.clicked.connect(self._open_youtube_search)
        buttons_vbox.addWidget(self.youtube_button)
        buttons_vbox.addStretch(1)
        header_layout.addLayout(buttons_vbox, 0, 2, 2, 1, Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight)

        main_layout.addWidget(header_widget)
        # --- End Header ---

        # --- Sections ---
        # (Abilities, Ultimate, Passives, Teamups, Gameplay, Balance, Lore, Background, Meta, Misc sections remain the same)
        # ... (paste your working versions of ALL previous sections here - omitted for brevity) ...
        # Abilities
        abilities_list = self.character_data.get('abilities', [])
        if abilities_list and isinstance(abilities_list, list):
            ability_group, ability_layout = self._create_section_group("Abilities")
            content_added_flag = False
            for ability in abilities_list:
                widget = self._create_zoomable_widget(self._format_ability_html(ability))
                if self._add_widget_if_data(ability_layout, widget):
                    content_added_flag = True
            if content_added_flag:
                ability_layout.addStretch(1); main_layout.addWidget(ability_group)
            else: ability_group.deleteLater()

        # Ultimate
        ultimate_data = self.character_data.get('ultimate')
        if ultimate_data and isinstance(ultimate_data, dict):
            ultimate_group, ultimate_layout = self._create_section_group("Ultimate")
            widget = self._create_zoomable_widget(self._format_ultimate_html(ultimate_data))
            if self._add_widget_if_data(ultimate_layout, widget): ultimate_layout.addStretch(1); main_layout.addWidget(ultimate_group)
            else: ultimate_group.deleteLater()

        # Passives / Melee
        passives_list = self.character_data.get('passives', [])
        if passives_list and isinstance(passives_list, list):
            passive_group, passive_layout = self._create_section_group("Passives / Melee")
            content_added_flag = False
            for passive in passives_list:
                widget = self._create_zoomable_widget(self._format_passive_html(passive))
                if self._add_widget_if_data(passive_layout, widget):
                    content_added_flag = True
            if content_added_flag:
                passive_layout.addStretch(1); main_layout.addWidget(passive_group)
            else: passive_group.deleteLater()

        # --- This is the problematic block in init_ui ---
        # Teamups
        teamups_list = self.character_data.get('teamups', [])
        if teamups_list and isinstance(teamups_list, list):
            teamup_group, teamup_layout = self._create_section_group("Teamups")
            # !!! PROBLEM AREA: This likely only formats the FIRST item (if any) !!!
            # Example of potential incorrect logic:
            # if teamups_list:
            #    first_teamup = teamups_list[0]
            #    widget = self._create_zoomable_widget(self._format_teamup_html(first_teamup))
            #    if self._add_widget_if_data(teamup_layout, widget):
            #        teamup_layout.addStretch(1)
            #        main_layout.addWidget(teamup_group)
            #    else: teamup_group.deleteLater()

            # --- Replace the above problematic logic with this loop ---
            content_added = False # Track if any teamup adds content
            for teamup_entry in teamups_list: # Loop through ALL teamups
                formatted_html = self._format_teamup_html(teamup_entry) # Format EACH one
                if formatted_html: # Only add if formatting produced something
                    widget = self._create_zoomable_widget(formatted_html)
                    if self._add_widget_if_data(teamup_layout, widget):
                        content_added = True # Mark that we added at least one

            # Add the group box only if content was actually added from the loop
            if content_added:
                teamup_layout.addStretch(1)
                main_layout.addWidget(teamup_group)
            else: # If loop finished but nothing was added (e.g., empty list or all entries formatted to empty string)
                teamup_group.deleteLater() # Clean up the empty group box
        # --- End of Teamups section ---

        # Gameplay Strategy
        gameplay_data = self.character_data.get('gameplay')
        if isinstance(gameplay_data, dict):
            gameplay_group, gameplay_layout = self._create_section_group("Gameplay Strategy", collapsible=True, initially_collapsed=True)
            content_added_flag = False
            overview = gameplay_data.get('strategy_overview')
            if overview: widget = self._create_zoomable_widget(f"<p>{overview}</p>"); content_added_flag = self._add_widget_if_data(gameplay_layout, widget) or content_added_flag
            weaknesses = gameplay_data.get('weaknesses', [])
            content_added_flag = self._add_list_as_bullets(gameplay_layout, "Weaknesses", weaknesses) or content_added_flag
            achievements = gameplay_data.get('achievements', [])
            if achievements and isinstance(achievements, list):
                 ach_html_parts = [html for ach in achievements if (html := self._format_achievement_html(ach))]
                 if ach_html_parts:
                      ach_title_label = QLabel(f"<span style='{SECTION_TITLE_STYLE_TEMPLATE.format(color=self.secondary_theme_color_str)}'>Achievements</span>"); ach_title_label.setFont(QFont(self.font_family, BASE_FONT_SIZE)); ach_title_label.setTextFormat(Qt.TextFormat.RichText); gameplay_layout.addWidget(ach_title_label)
                      widget = self._create_zoomable_widget("".join(ach_html_parts)); content_added_flag = self._add_widget_if_data(gameplay_layout, widget) or content_added_flag
            if content_added_flag: gameplay_layout.addStretch(1); main_layout.addWidget(gameplay_group)
            else: gameplay_group.deleteLater()

        # Balance History
        lore_data_for_balance = self.character_data.get('lore_details', {})
        balance_changes = lore_data_for_balance.get('balance_changes', []) if isinstance(lore_data_for_balance, dict) else []
        if balance_changes and isinstance(balance_changes, list):
             change_html_parts = [html for change in balance_changes if (html := self._format_balance_change_html(change))]
             if change_html_parts:
                 balance_group, balance_layout = self._create_section_group("Balance History", collapsible=True, initially_collapsed=True)
                 widget = self._create_zoomable_widget("".join(change_html_parts))
                 if self._add_widget_if_data(balance_layout, widget):
                     balance_layout.addStretch(1)
                     main_layout.addWidget(balance_group)
                 else:
                     balance_group.deleteLater()

        # Lore & History
        lore_data = self.character_data.get('lore_details')
        if isinstance(lore_data, dict):
             has_other_lore = any(k != 'balance_changes' and v for k, v in lore_data.items())
             if has_other_lore:
                 lore_group, lore_layout = self._create_section_group("Lore & History", collapsible=True, initially_collapsed=True)
                 content_added_flag = False
                 quote = lore_data.get('ingame_bio_quote'); bio = lore_data.get('ingame_bio_text'); story_intro = lore_data.get('ingame_story_intro'); official_quote = lore_data.get('official_quote'); official_desc = lore_data.get('official_description')
                 if quote: widget = self._create_zoomable_widget(f"<div style='{QUOTE_STYLE}'>{quote}</div>"); content_added_flag = self._add_widget_if_data(lore_layout, widget) or content_added_flag
                 if bio: widget = self._create_zoomable_widget(f"<p>{bio}</p>"); content_added_flag = self._add_widget_if_data(lore_layout, widget) or content_added_flag
                 if story_intro: widget = self._create_zoomable_widget(f"<p style='margin-top: 8px;'>{story_intro}</p>"); content_added_flag = self._add_widget_if_data(lore_layout, widget) or content_added_flag
                 hero_stories = lore_data.get('hero_stories', [])
                 if hero_stories and isinstance(hero_stories, list):
                      story_html_parts = [html for story in hero_stories if (html := self._format_hero_story_html(story))]
                      if story_html_parts:
                           story_title_label = QLabel(f"<p style='margin-top:8px;'><span style='{SECTION_TITLE_STYLE_TEMPLATE.format(color=self.secondary_theme_color_str)}'>Hero Stories</span></p>"); story_title_label.setFont(QFont(self.font_family, BASE_FONT_SIZE)); story_title_label.setTextFormat(Qt.TextFormat.RichText); lore_layout.addWidget(story_title_label)
                           widget = self._create_zoomable_widget("".join(story_html_parts)); content_added_flag = self._add_widget_if_data(lore_layout, widget) or content_added_flag
                 if official_quote: widget = self._create_zoomable_widget(f"<div style='{QUOTE_STYLE} margin-top: 8px;'>{official_quote}</div>"); content_added_flag = self._add_widget_if_data(lore_layout, widget) or content_added_flag
                 if official_desc: widget = self._create_zoomable_widget(f"<p style='margin-top: 4px;'>{official_desc}</p>"); content_added_flag = self._add_widget_if_data(lore_layout, widget) or content_added_flag
                 if content_added_flag:
                     lore_layout.addStretch(1); main_layout.addWidget(lore_group)
                 else:
                     lore_group.deleteLater()

        # Background (Comic Lore)
        background_data = self.character_data.get('background')
        if isinstance(background_data, dict) and any(background_data.values()): # Check if dict exists and has content
            bg_group, bg_layout = self._create_section_group("Background (Comic Lore)", collapsible=True, initially_collapsed=True)
            content_added_flag = False
            content_added_flag = self._add_field_label(bg_layout, "Real Name", background_data.get("real_name")) or content_added_flag
            content_added_flag = self._add_list_as_bullets(bg_layout, "Aliases", background_data.get("aliases", [])) or content_added_flag
            content_added_flag = self._add_field_label(bg_layout, "Gender", background_data.get("gender")) or content_added_flag
            content_added_flag = self._add_field_label(bg_layout, "Birthplace", background_data.get("birthplace")) or content_added_flag
            affiliation_val = background_data.get("affiliation")
            if isinstance(affiliation_val, list): content_added_flag = self._add_list_as_bullets(bg_layout, "Affiliation", affiliation_val) or content_added_flag
            elif affiliation_val: content_added_flag = self._add_field_label(bg_layout, "Affiliation", affiliation_val) or content_added_flag
            content_added_flag = self._add_list_as_bullets(bg_layout, "Relatives", background_data.get("relatives", [])) or content_added_flag
            content_added_flag = self._add_field_label(bg_layout, "First Appearance", background_data.get("first_appearance_comic")) or content_added_flag
            content_added_flag = self._add_list_as_bullets(bg_layout, "Powers/Skills", background_data.get("lore_powers_skills", [])) or content_added_flag
            if content_added_flag: bg_layout.addStretch(1); main_layout.addWidget(bg_group)
            else: bg_group.deleteLater()

        # Meta Stats
        # --- Meta Stats Section ---
        meta_stats_data = self.character_data.get('meta_stats', {}) # Default to empty dict
        # Check if the dictionary exists AND contains at least one non-null/non-empty value
        has_meta_content = False
        if isinstance(meta_stats_data, dict):
            has_meta_content = any(v is not None and str(v).strip() for v in meta_stats_data.values())

        if has_meta_content:
            # Create the collapsible group box
            meta_group, meta_layout = self._create_section_group("Meta Stats", collapsible=True, initially_collapsed=True)
            content_added_to_layout = False

            # Define the desired order and display names
            stats_order = [
                ("tier", "Tier"),
                ("win_rate", "Win Rate"),
                ("wr_change", "WR Change"),
                ("pick_rate", "Pick Rate"),
                ("pr_change", "PR Change"),
                ("ban_rate", "Ban Rate"),
                ("matches", "Matches")
            ]
            html_lines = []
            processed_keys = set() # Keep track of keys we've handled

            # Process stats in the defined order
            for key, display_name in stats_order:
                processed_keys.add(key) # Mark key as processed
                value = meta_stats_data.get(key)
                # Check if value exists and is not just whitespace
                if value is not None and str(value).strip():
                    # Format the line with standard styles
                    line = f"<p><span style='{FIELD_LABEL_STYLE}'>{display_name}:</span> <span style='{FIELD_VALUE_STYLE}'>{value}</span></p>"
                    html_lines.append(line)

            # Process any other keys found in meta_stats that weren't in our defined order
            other_keys = {k: v for k, v in meta_stats_data.items() if k not in processed_keys}
            for key, value in other_keys.items():
                 if value is not None and str(value).strip():
                    # Create a display name by replacing underscores and capitalizing
                    display_name = key.replace("_", " ").title()
                    line = f"<p><span style='{FIELD_LABEL_STYLE}'>{display_name}:</span> <span style='{FIELD_VALUE_STYLE}'>{value}</span></p>"
                    html_lines.append(line)

            # Add the combined HTML to a widget if any lines were generated
            if html_lines:
                full_html = "".join(html_lines)
                # Use a zoomable widget to contain the stats
                content_widget = self._create_zoomable_widget(full_html)
                if self._add_widget_if_data(meta_layout, content_widget):
                    meta_layout.addStretch(1) # Push content to top
                    main_layout.addWidget(meta_group) # Add the group to the main card layout
                    content_added_to_layout = True # Mark that we added the group

            # If after all processing, no content was added (e.g., all values were null/empty), delete the group
            if not content_added_to_layout:
                meta_group.deleteLater()
        # --- End Meta Stats Section ---


        # Determine if there's *any* content to show in this section
        # Define misc_data and data_sources from character_data
        misc_data = self.character_data.get('misc', {}) if isinstance(self.character_data, dict) else {}
        data_sources = self.character_data.get('data_sources', {}) if isinstance(self.character_data, dict) else {}

        has_buzz = isinstance(misc_data, dict) and misc_data.get('community_buzz')
        has_helpful = isinstance(misc_data, dict) and misc_data.get('helpful_links')
        has_sources = isinstance(data_sources, dict) and any(bool(v) for v in data_sources.values() if isinstance(v, list))

        # Only create the group if there's at least one piece of relevant info
        if has_buzz or has_helpful or has_sources:
            # Create the collapsible group box, titled "Extras"
            extras_group, extras_layout = self._create_section_group("Extras", collapsible=True, initially_collapsed=True)
            content_added_to_layout = False # Track if anything actually gets added

            # 1. Community Buzz Link
            if has_buzz:
                buzz_text_url = misc_data.get('community_buzz')
                if buzz_text_url and isinstance(buzz_text_url, str) and buzz_text_url.strip():
                    # Create clickable link with character name
                    link_html = f"<a href='{buzz_text_url}' style='color:#77C4FF; text-decoration: none;'>{self.character_name} Reddit Link</a>"
                    # Add a label for "Community Buzz:" followed by the link widget
                    buzz_title_label = QLabel(f"<span style='{FIELD_LABEL_STYLE}'>Community Buzz:</span>")
                    buzz_title_label.setFont(QFont(self.font_family, BASE_FONT_SIZE)); buzz_title_label.setTextFormat(Qt.TextFormat.RichText)
                    extras_layout.addWidget(buzz_title_label)

                    buzz_link_label = QLabel(link_html)
                    buzz_link_label.setTextFormat(Qt.TextFormat.RichText)
                    buzz_link_label.setOpenExternalLinks(True)
                    buzz_link_label.setFont(QFont(self.font_family, BASE_FONT_SIZE))
                    buzz_link_label.setWordWrap(True)
                    # Indent the link slightly under the label
                    buzz_link_label.setStyleSheet("QLabel { margin-left: 10px; }")
                    extras_layout.addWidget(buzz_link_label)
                    content_added_to_layout = True

            # 2. Helpful Links
            if has_helpful:
                helpful_links = misc_data.get('helpful_links', [])
                links_html_parts = []
                if helpful_links and isinstance(helpful_links, list):
                    for link_item in helpful_links:
                        if isinstance(link_item, dict):
                            title = link_item.get('title'); url = link_item.get('url')
                            if title and url and str(title).strip() and str(url).strip():
                                link_text = f"<a href='{url}' style='color: #77C4FF; text-decoration: none;'>{title}</a>"
                                # Replace potential newlines in link titles just in case
                                display_title = str(title).replace('\n', ' ')
                                links_html_parts.append(f"<li>{link_text}</li>")

                if links_html_parts:
                    # Add separator if Buzz was also added
                    if content_added_to_layout:
                         separator = QFrame(); separator.setFrameShape(QFrame.Shape.HLine); separator.setFrameShadow(QFrame.Shadow.Sunken); extras_layout.addWidget(separator)

                    links_title_label = QLabel(f"<span style='{FIELD_LABEL_STYLE}'>Helpful Links:</span>")
                    links_title_label.setFont(QFont(self.font_family, BASE_FONT_SIZE)); links_title_label.setTextFormat(Qt.TextFormat.RichText); extras_layout.addWidget(links_title_label)

                    links_html = f"<ul style='{LIST_ITEM_STYLE} margin-top: 0px;'>{''.join(links_html_parts)}</ul>"
                    links_widget = self._create_zoomable_widget(links_html)
                    if self._add_widget_if_data(extras_layout, links_widget):
                        content_added_to_layout = True

            # 3. Data Sources Links
            if has_sources:
                source_html_lines = []
                source_order = [ # Define preferred order and display names
                    ("wiki", "Game Wiki"),
                    ("tracker", "RivalsTracker"),
                    ("comic_wiki", "Marvel Wiki (Fandom)")
                ]
                processed_keys = set()

                # Process in preferred order
                for key, display_name in source_order:
                    processed_keys.add(key)
                    urls = data_sources.get(key)
                    if urls and isinstance(urls, list):
                        link_parts = [f'<a href="{url}" style="color:#77C4FF; text-decoration: none;">{url}</a>'
                                      for url in urls if url and isinstance(url, str) and url.strip()]
                        if link_parts:
                            # Add label and links for this source
                            source_html_lines.append(f"<p style='margin-bottom: 3px;'><span style='{FIELD_LABEL_STYLE}'>{display_name}:</span><br/><span style='margin-left: 10px;'>" + "<br/>".join(link_parts) + "</span></p>")

                # Process any other keys found in data_sources
                other_sources = {k: v for k, v in data_sources.items() if k not in processed_keys}
                for key, urls in other_sources.items():
                    if urls and isinstance(urls, list):
                        link_parts = [f'<a href="{url}" style="color:#77C4FF; text-decoration: none;">{url}</a>'
                                      for url in urls if url and isinstance(url, str) and url.strip()]
                        if link_parts:
                            display_name = key.replace("_", " ").title() # Generic nice name
                            source_html_lines.append(f"<p style='margin-bottom: 3px;'><span style='{FIELD_LABEL_STYLE}'>{display_name}:</span><br/><span style='margin-left: 10px;'>" + "<br/>".join(link_parts) + "</span></p>")

                # Add the combined source links if any were found
                if source_html_lines:
                     # Add separator if Buzz or Helpful Links were also added
                    if content_added_to_layout:
                         separator = QFrame(); separator.setFrameShape(QFrame.Shape.HLine); separator.setFrameShadow(QFrame.Shadow.Sunken); extras_layout.addWidget(separator)

                    full_source_html = "".join(source_html_lines)
                    source_widget = self._create_zoomable_widget(full_source_html)
                    if self._add_widget_if_data(extras_layout, source_widget):
                        content_added_to_layout = True

            # Finalize the group: Add to main layout only if content was actually added
            if content_added_to_layout:
                extras_layout.addStretch(1)
                main_layout.addWidget(extras_group)
            else:
                # If after all checks, nothing was added, delete the group
                extras_group.deleteLater()
        # --- End Combined "Extras" Section ---

        # Final stretch (This should now be the very last thing)
        main_layout.addStretch(1)

    # ... (rest of CharacterCard methods: _make_text_links_clickable, _format_*, etc.) ...
# (Method provided in previous step, ensure it's present)

    # Favorite button slots (Unchanged)
    @Slot()
    def toggle_favorite_button(self):
        self._is_favorite = not self._is_favorite; self.update_favorite_button_style(); self.favorite_toggled.emit(self.character_name, self._is_favorite)

    def update_favorite_button_style(self):
        self.fav_button.setChecked(self._is_favorite); self.fav_button.setProperty("favorited", self._is_favorite); self.fav_button.setText("★" if self._is_favorite else "☆"); self.fav_button.style().unpolish(self.fav_button); self.fav_button.style().polish(self.fav_button)

class JsonUpdateWorker(QThread):
    """
    Worker thread for downloading character JSON files from GitHub.
    Emits signals for progress updates and completion/error status.
    """
    # Define signals to communicate back to the main thread
    # Signal signature: progress(current_file_index, total_files, filename)
    progress = Signal(int, int, str)
    # Signal signature: finished(success_boolean, message_string)
    finished = Signal(bool, str)

    def __init__(self, repo_url, local_dir, parent=None):
        super().__init__(parent)
        self.repo_api_url = repo_url  # e.g., "https://api.github.com/repos/Reg0lino/Marvel-Rivals-Dashboard/contents/characters?ref=main"
        self.local_char_dir = Path(local_dir) # Use pathlib for easier path joining
        self.is_running = True # Flag to allow interruption (optional for now)

    def run(self):
        """The main logic executed by the thread."""
        print("JsonUpdateWorker: Thread started.")
        total_files_to_download = 0
        files_downloaded = 0
        error_occurred = False
        final_message = ""

        try:
            # --- 1. Get the list of files from GitHub API ---
            print(f"JsonUpdateWorker: Fetching file list from {self.repo_api_url}")
            response = requests.get(self.repo_api_url, timeout=15) # Add timeout
            response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
            repo_files_data = response.json()

            # Filter for JSON files only and get download URLs
            json_files = []
            for item in repo_files_data:
                if item['type'] == 'file' and item['name'].lower().endswith('.json'):
                    # Prefer 'download_url', fallback to constructing raw URL if needed
                    download_url = item.get('download_url')
                    if not download_url:
                         # Construct raw URL (less reliable if structure changes)
                         raw_base = "https://raw.githubusercontent.com/Reg0lino/Marvel-Rivals-Dashboard/main/characters/"
                         download_url = raw_base + item['name']
                         print(f"WARN: No download_url in API response for {item['name']}, using constructed raw URL: {download_url}")

                    json_files.append({'name': item['name'], 'url': download_url})

            total_files_to_download = len(json_files)
            print(f"JsonUpdateWorker: Found {total_files_to_download} JSON files to download.")

            if total_files_to_download == 0:
                 raise ValueError("No JSON files found in the repository directory.")

            # --- 2. Ensure local directory exists ---
            self.local_char_dir.mkdir(parents=True, exist_ok=True)
            print(f"JsonUpdateWorker: Ensured local directory exists: {self.local_char_dir}")

            # --- 3. Download each file ---
            for index, file_info in enumerate(json_files):
                filename = file_info['name']
                download_url = file_info['url']
                local_filepath = self.local_char_dir / filename # Use pathlib's / operator

                # Emit progress signal BEFORE starting download
                self.progress.emit(index, total_files_to_download, filename)
                print(f"JsonUpdateWorker: Downloading ({index + 1}/{total_files_to_download}) '{filename}' from {download_url}...")

                try:
                    file_response = requests.get(download_url, timeout=20) # Longer timeout for file download
                    file_response.raise_for_status()

                    # Save the file content (using binary write mode 'wb' is safer)
                    with open(local_filepath, 'wb') as f:
                        f.write(file_response.content)

                    files_downloaded += 1
                    print(f"JsonUpdateWorker: Successfully saved '{filename}' to {local_filepath}")

                except requests.exceptions.RequestException as e_download:
                     error_occurred = True
                     err_msg = f"Error downloading '{filename}': {e_download}"
                     print(f"ERROR: {err_msg}")
                     final_message += f"\n- Failed: {filename} ({e_download})" # Append specific error
                     # Optionally decide whether to continue or stop on error
                     # break # Uncomment to stop after first error

                # Add a small sleep to yield control (optional, helps UI responsiveness slightly)
                # self.msleep(50) # 50 milliseconds

            # --- 4. Prepare final message ---
            if not error_occurred:
                final_message = f"Successfully downloaded {files_downloaded} character files.\n\nPlease restart the dashboard to apply the updates."
            else:
                # Prepend a summary to the specific error messages
                final_message = f"Update completed with errors.\nDownloaded: {files_downloaded}/{total_files_to_download}\nErrors:{final_message}"
                final_message += "\n\nPlease check console logs and try again later. You may need to restart."

        except requests.exceptions.Timeout:
             error_occurred = True
             err_msg = "Connection timed out while trying to reach GitHub."
             print(f"ERROR: {err_msg}")
             final_message = f"Update Failed: {err_msg}"
        except requests.exceptions.RequestException as e_api:
            error_occurred = True
            err_msg = f"Error communicating with GitHub API: {e_api}"
            print(f"ERROR: {err_msg}")
            final_message = f"Update Failed: {err_msg}"
        except ValueError as e_val: # Catch the "No JSON files found" error
             error_occurred = True
             err_msg = str(e_val)
             print(f"ERROR: {err_msg}")
             final_message = f"Update Failed: {err_msg}"
        except Exception as e_generic:
            error_occurred = True
            err_msg = f"An unexpected error occurred during update: {e_generic}"
            print(f"ERROR: {err_msg}")
            import traceback
            traceback.print_exc() # Print full traceback for debugging
            final_message = f"Update Failed: An unexpected error occurred. Check logs."

        # --- 5. Emit finished signal ---
        # Success is True only if NO errors occurred AND we intended to download files
        success = not error_occurred and total_files_to_download > 0
        self.finished.emit(success, final_message)
        print(f"JsonUpdateWorker: Thread finished. Success: {success}")

    def stop(self):
        """Placeholder for interrupting the thread (not fully implemented)."""
        self.is_running = False
        print("JsonUpdateWorker: Stop requested.")
# --- END OF JsonUpdateWorker CLASS ---

# --- Add this Helper Function ---
def get_config_value_flexible(config_map, key):
    """
    Tries to get value from a dictionary using the original key,
    then tries common sanitized versions if the original key fails.
    """
    if not isinstance(key, str): # Basic check
        return None

    # 1. Try the original key directly
    value = config_map.get(key)
    if value is not None:
        return value

    # 2. Try replacing space with underscore AND '&' with 'and'
    # (Common convention seen in updater sanitization)
    key_sanitized_common = key.replace(' ', '_').replace('&', 'and')
    value = config_map.get(key_sanitized_common)
    if value is not None:
        # Optional: Print a warning if the sanitized key was needed, helps identify config inconsistencies
        print(f"WARN: Config lookup needed sanitized key '{key_sanitized_common}' for original key '{key}'.")
        return value

    # 3. Add more specific variations if needed (Example: Only space replacement)
    key_sanitized_space = key.replace(' ', '_')
    if key_sanitized_space != key and key_sanitized_space != key_sanitized_common:
        value = config_map.get(key_sanitized_space)
        if value is not None:
            print(f"WARN: Config lookup needed space-only sanitized key '{key_sanitized_space}' for original key '{key}'.")
            return value

    # 4. Add more specific variations (Example: Only '&' replacement)
    key_sanitized_amp = key.replace('&', 'and')
    if key_sanitized_amp != key and key_sanitized_amp != key_sanitized_common:
        value = config_map.get(key_sanitized_amp)
        if value is not None:
            print(f"WARN: Config lookup needed ampersand-only sanitized key '{key_sanitized_amp}' for original key '{key}'.")
            return value

    # If all attempts fail, return None
    return None
# --- End Helper Function ---




# --- Main Window (Corrected Indentation) ---
class MainWindow(QMainWindow):

# --- Replace this entire method in MainWindow ---
    def __init__(self):
        super().__init__()
        print("Initializing MainWindow...")
        self.font_family = CURRENT_FONT_FAMILY_NAME
        self.using_custom_font = CUSTOM_FONT_LOADED
        self._load_external_config()
        self.load_character_list()
        self.favorites = load_favorites()
        self.character_cards = {}
        self.jump_bar_labels = {}
        self.jump_bar_flow_layout = None
        self.jump_bar_container = None
        self.json_update_worker = None # <<< ADD THIS LINE to store worker thread instance
        self.setWindowTitle("Marvel Rivals Dashboard")


    def load_character_list(self):
        """
        Loads character names by scanning the characters directory,
        reading the 'name' field from each valid JSON file.
        """
        global ACTIVE_CHARACTER_LIST
        ACTIVE_CHARACTER_LIST = []
        temp_char_names = set()
        target_dir = CHARACTER_DATA_FOLDER

        if not os.path.isdir(target_dir):
            print(f"ERROR: Character data folder not found: {target_dir}")
            # Optionally show a message box here too
            QMessageBox.critical(self, "Startup Error", f"Character data folder missing:\n{target_dir}")
            return # Can't proceed without character data

        print("Loading character list from JSON file contents...")
        file_count = 0
        error_count = 0
        try:
            for filename in os.listdir(target_dir):
                if filename.lower().endswith(".json") and not filename.lower().endswith(".api_error.txt"):
                    filepath = os.path.join(target_dir, filename)
                    if not os.path.isfile(filepath): continue

                    file_count += 1
                    char_data = None
                    try:
                        # Try reading with UTF-8-SIG first (handles BOM)
                        with open(filepath, 'r', encoding='utf-8-sig') as f:
                            char_data = json.load(f)
                    except UnicodeDecodeError:
                        # Fallback to plain UTF-8 if SIG fails
                        try:
                            with open(filepath, 'r', encoding='utf-8') as f:
                                char_data = json.load(f)
                        except Exception as e_inner:
                            print(f"  WARN: Failed read '{filename}' (UTF-8 Fallback): {e_inner}")
                            error_count += 1
                            continue # Skip this file
                    except json.JSONDecodeError as e_json:
                        print(f"  WARN: Invalid JSON in '{filename}': {e_json}")
                        error_count += 1
                        continue # Skip this file
                    except Exception as e_load:
                        print(f"  WARN: Failed load '{filename}': {e_load}")
                        error_count += 1
                        continue # Skip this file

                    # Process successfully loaded data
                    if isinstance(char_data, dict):
                        char_name_from_json = char_data.get("name")
                        if char_name_from_json and isinstance(char_name_from_json, str):
                            normalized_name = char_name_from_json.strip()
                            # Apply specific corrections BEFORE general title casing
                            if normalized_name == "Namor McKenzie": normalized_name = "Namor"
                            elif normalized_name == "The Punisher": normalized_name = "Punisher"
                            elif normalized_name == "Cloak and Dagger": normalized_name = "Cloak & Dagger"
                            elif normalized_name.isupper() and normalized_name != "MODOK":
                                original_name_for_log = normalized_name # Store before changing case
                                normalized_name = normalized_name.title()
                                print(f"  INFO: Normalized ALL CAPS name from '{original_name_for_log}' to '{normalized_name}' in file '{filename}'.")

                            temp_char_names.add(normalized_name)
                        else:
                            print(f"  WARN: No valid 'name' field found in '{filename}'.")
                            error_count += 1
                    else:
                        print(f"  WARN: Data in '{filename}' is not a dictionary (Type: {type(char_data)}).")
                        error_count += 1

            # Sort the unique names found inside the JSON files
            ACTIVE_CHARACTER_LIST = sorted(list(temp_char_names))
            print(f"Dashboard loaded {len(ACTIVE_CHARACTER_LIST)} unique characters from {file_count} JSON files scanned.")
            if error_count > 0:
                print(f"  ({error_count} files encountered errors during loading/parsing)")

        except OSError as e:
            print(f"ERROR reading character folder {target_dir}: {e}")
            QMessageBox.critical(self, "Startup Error", f"Error reading character folder:\n{target_dir}\n\n{e}")
            ACTIVE_CHARACTER_LIST = [] # Ensure list is empty on error
    
# --- Replace this entire method in MainWindow ---
    def _create_unified_top_bar(self):
        """Creates a top bar area with FlowLayout buttons on one row
           and Search/Sort/Filter/etc. on the row below."""

        # --- Main Container Widget for the whole top bar area ---
        top_bar_widget = QWidget()
        # Use a QVBoxLayout to stack the FlowLayout area ABOVE the Search/Right area
        main_top_layout = QVBoxLayout(top_bar_widget)
        main_top_layout.setContentsMargins(0, 5, 0, 5) # Overall vertical margins
        main_top_layout.setSpacing(8) # Space between the two rows

        # --- Row 1: Info/Update Buttons (FlowLayout) ---
        button_flow_container = QWidget()
        button_flow_layout = FlowLayout(button_flow_container, margin=0, hSpacing=6, vSpacing=4)
        sp_buttons = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)
        button_flow_container.setSizePolicy(sp_buttons)

        font_info_buttons = QFont(self.font_family, BASE_FONT_SIZE)
        sorted_info_keys = sorted(INFO_FILES.keys())
        for key in sorted_info_keys:
            button = QPushButton(key)
            button.setObjectName("InfoButton")
            button.setFont(font_info_buttons)
            button.setToolTip(f"Show {key.replace('_', ' ').title()} Info")
            button.clicked.connect(lambda checked=False, k=key: self._show_info_popup(k))
            button_flow_layout.addWidget(button)

        # --- Tracker button ---
        tracker_button = QPushButton("Tracker")
        tracker_button.setObjectName("InfoButton")
        tracker_button.setFont(font_info_buttons)
        tracker_button.setToolTip("Open RivalsTracker Leaderboard (rivalstracker.com)")
        tracker_url = QUrl("https://rivalstracker.com/leaderboard")
        tracker_button.clicked.connect(lambda: QDesktopServices.openUrl(tracker_url))
        button_flow_layout.addWidget(tracker_button)

        # --- "Update Dash" button (Launches External Updater) ---
        # Keeping this button for now, but could be removed for Simple Sync release
        launch_updater_button = QPushButton("Launch Updater")
        launch_updater_button.setObjectName("InfoButton")
        launch_updater_button.setFont(font_info_buttons)
        launch_updater_button.setToolTip("Launch the external data updater tool (updater_v3.py)")
        launch_updater_button.clicked.connect(self._confirm_launch_updater)
        button_flow_layout.addWidget(launch_updater_button)

        # --- NEW: "Check for Updates" Button (JSON Downloader) ---
        self.json_update_button = QPushButton("Check for Data Updates") # <<< NEW BUTTON
        self.json_update_button.setObjectName("UpdateButton") # <<< Use a distinct object name for styling
        self.json_update_button.setFont(font_info_buttons)
        self.json_update_button.setToolTip("Download the latest character data files from GitHub")
        self.json_update_button.clicked.connect(self._start_json_update) # <<< Connect to new method
        button_flow_layout.addWidget(self.json_update_button) # <<< Add to layout

        # Add the FlowLayout container as the FIRST row in the main vertical layout
        main_top_layout.addWidget(button_flow_container)

        # --- Row 2: Search, Sort, Filter, Exit (QHBoxLayout) ---
        search_controls_bar = QWidget()
        search_controls_layout = QHBoxLayout(search_controls_bar)
        search_controls_layout.setContentsMargins(0, 0, 0, 0)
        search_controls_layout.setSpacing(8)

        font_controls = QFont(self.font_family, BASE_FONT_SIZE)
        self.search_input = QLineEdit()
        self.search_input.setFont(font_controls)
        self.search_input.setPlaceholderText("Search Characters...")
        self.search_input.textChanged.connect(self.filter_characters)

        self.sort_combo = QComboBox()
        self.sort_combo.setFont(font_controls)
        self.sort_combo.addItems(["Sort by Name", "Sort by Role", "Favorites First"])
        self.sort_combo.setCurrentText("Favorites First")
        self.sort_combo.currentIndexChanged.connect(self.sort_and_filter_characters)

        self.filter_combo = QComboBox()
        self.filter_combo.setFont(font_controls)
        self.filter_combo.addItems(["Filter by Role: All", "Vanguard", "Duelist", "Strategist"])
        self.filter_combo.currentIndexChanged.connect(self.sort_and_filter_characters)

        search_controls_layout.addWidget(self.search_input, 1)
        search_controls_layout.addWidget(self.sort_combo)
        search_controls_layout.addWidget(self.filter_combo)
        search_controls_layout.addStretch(1)

        self.exit_button = QPushButton("✕")
        self.exit_button.setObjectName("ExitButton")
        self.exit_button.setFixedSize(24, 24)
        self.exit_button.setToolTip("Exit Application")
        app_instance = QApplication.instance()
        if app_instance:
             self.exit_button.clicked.connect(app_instance.quit)
        else:
             print("WARNING: Could not connect Exit button: QApplication instance not found yet.")
        search_controls_layout.addWidget(self.exit_button)

        main_top_layout.addWidget(search_controls_bar)

        return top_bar_widget
    # --- END OF REPLACED METHOD ---

    def _create_jump_bar(self):
        """Creates the Jump to Character group box with clickable icons."""
    # Create the main container GroupBox
        self.jump_bar_container = QGroupBox("Jump to Character")
        title_font = QFont(self.font_family, GROUP_TITLE_FONT_SIZE)
        title_font.setWeight(QFont.Weight.Bold)
        self.jump_bar_container.setFont(title_font)
        self.jump_bar_container.setObjectName("JumpBarGroupBox")
        self.jump_bar_container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        # Create a widget to hold the flow layout
        jump_bar_widget = QWidget(self.jump_bar_container)
        # Create the FlowLayout for the icons (Ensure FlowLayout class is defined)
        self.jump_bar_flow_layout = FlowLayout(jump_bar_widget, margin=0, hSpacing=JUMP_BAR_FIXED_SPACING, vSpacing=JUMP_BAR_FIXED_SPACING)

        # --- ADDED SIZE POLICY FIX ---
        sp_jump = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        jump_bar_widget.setSizePolicy(sp_jump)
        # --- END OF ADDED SIZE POLICY FIX ---

        # Create a layout for the GroupBox itself to hold the jump_bar_widget
        group_content_layout = QVBoxLayout(self.jump_bar_container)
        group_content_layout.setContentsMargins(5, 8, 5, 5) # Top margin accounts for title
        group_content_layout.addWidget(jump_bar_widget)

     # Check if character list is loaded (needs ACTIVE_CHARACTER_LIST global)
        # Ensure ACTIVE_CHARACTER_LIST is defined globally before this call
        if 'ACTIVE_CHARACTER_LIST' not in globals() or not ACTIVE_CHARACTER_LIST:
                print("Jump Bar: No characters loaded to create icons.")
                placeholder_label = QLabel("(No characters found)")
                placeholder_label.setAlignment(Qt.AlignmentFlag.AlignCenter) # Center placeholder
                self.jump_bar_flow_layout.addWidget(placeholder_label)
                # Clear container reference if no characters, so it doesn't get added to layout
                # and avoid adding an empty group box later
                self.jump_bar_container.deleteLater() # Clean up the group box
                self.jump_bar_container = None
                return # Exit if no characters

            # Clear any previous labels (if recreating)
        self.jump_bar_labels.clear()

            # Define font for text fallback icons
        icon_font = QFont(self.font_family, BASE_FONT_SIZE + 1) # Adjusted size slightly
        icon_font.setWeight(QFont.Weight.Bold)

         # Create icon labels for each character
        if DEBUG_MODE: print(f"DEBUG JumpBar Setup: Creating icons for {len(ACTIVE_CHARACTER_LIST)} characters...")
            # Use the global ACTIVE_CHARACTER_LIST populated by load_character_list
        for char_name in ACTIVE_CHARACTER_LIST:
                # Ensure ClickableLabel class is defined earlier
                icon_label = ClickableLabel(tooltip_text=char_name)
                icon_label.setFixedSize(JUMP_BAR_FIXED_ICON_SIZE, JUMP_BAR_FIXED_ICON_SIZE)

            # Use flexible lookup to get the icon filename from the map
            # Needs CHARACTER_ICON_MAP global loaded by _load_external_config
                icon_filename = get_config_value_flexible(CHARACTER_ICON_MAP, char_name)

                if DEBUG_MODE:
                    print(f"DEBUG JumpBar '{char_name}': Lookup result icon_filename = '{icon_filename}'")

                icon_found = False
                if icon_filename:
                    icon_path = os.path.join(IMAGE_FOLDER, icon_filename) # Needs IMAGE_FOLDER global
                    if DEBUG_MODE: print(f"DEBUG JumpBar '{char_name}': Trying icon path '{icon_path}'")

                    if os.path.exists(icon_path):
                        pixmap = QPixmap(icon_path)
                        if not pixmap.isNull():
                            scaled_pixmap = pixmap.scaled(JUMP_BAR_FIXED_ICON_SIZE, JUMP_BAR_FIXED_ICON_SIZE, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                            icon_label.setPixmap(scaled_pixmap)
                            icon_found = True
                    else:
                       if DEBUG_MODE: print(f"ERROR JumpBar '{char_name}': QPixmap is null for '{icon_path}'.")
                else:
                  if DEBUG_MODE:
                      print(f"ERROR JumpBar '{char_name}': Icon file not found: '{icon_path}'")

                if not icon_found:
                    first_letter = char_name[0].upper() if char_name else "?"
                    icon_label.setText(first_letter)
                    icon_label.setFont(icon_font)
                    icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    icon_label.setStyleSheet(f"border: 1px solid #555; border-radius: 3px; color: #DDDDDD; background-color: #444444;")

            # Connect signal AFTER icon_label is fully created
                icon_label.clicked.connect(self.jump_to_character)
            # Debug print to confirm connection
                if DEBUG_MODE: print(f"DEBUG Connect: Connected signal for '{char_name}' icon.")

            # Store reference and add to layout
                self.jump_bar_labels[char_name] = icon_label
                self.jump_bar_flow_layout.addWidget(icon_label)

        if DEBUG_MODE: print(f"DEBUG JumpBar Setup: Finished creating icons.")

        # --- START OF DEFINITIVE _load_external_config METHOD ---
    def _load_external_config(self):
        """Loads static configuration files like image/icon maps and info files."""
        # --- Declare modification of globals AT THE TOP ---
        global CHARACTER_IMAGE_MAP, CHARACTER_ICON_MAP, INFO_FILES

        # --- Load CHARACTER_IMAGE_MAP ---
        if DEBUG_MODE:
            print(f"DEBUG: Attempting to load CHARACTER_IMAGE_MAP.")
        CHARACTER_IMAGE_MAP = load_json_config('character_images.json')
        if DEBUG_MODE:
            print(f"DEBUG: _load_external_config - CHARACTER_IMAGE_MAP loaded? {'Yes' if CHARACTER_IMAGE_MAP else 'No'}")

        # --- Load CHARACTER_ICON_MAP ---
        if DEBUG_MODE:
             print(f"DEBUG: Attempting to load CHARACTER_ICON_MAP.")
        CHARACTER_ICON_MAP = load_json_config('character_icons.json')
        if DEBUG_MODE:
             print(f"DEBUG: _load_external_config - CHARACTER_ICON_MAP loaded? {'Yes' if CHARACTER_ICON_MAP else 'No'}")

        # --- Load INFO_FILES ---
        if DEBUG_MODE:
            print(f"DEBUG: Attempting to load INFO_FILES.")
        INFO_FILES = load_json_config('info_files.json')
        if DEBUG_MODE:
            print(f"DEBUG: _load_external_config - INFO_FILES loaded? {'Yes' if INFO_FILES else 'No'}")

        # --- Optional Debug Prints (Verify content after load attempts) ---
        # Only print if DEBUG_MODE is True to avoid clutter
        if DEBUG_MODE:
            print(f"DEBUG: Final Check - CHARACTER_IMAGE_MAP loaded? {'Yes' if CHARACTER_IMAGE_MAP else 'No'}. Keys sample: {list(CHARACTER_IMAGE_MAP.keys())[:5] if CHARACTER_IMAGE_MAP else 'N/A'}")
            print(f"DEBUG: Final Check - CHARACTER_ICON_MAP loaded? {'Yes' if CHARACTER_ICON_MAP else 'No'}. Keys sample: {list(CHARACTER_ICON_MAP.keys())[:5] if CHARACTER_ICON_MAP else 'N/A'}")
            print(f"DEBUG: Final Check - INFO_FILES loaded? {'Yes' if INFO_FILES else 'No'}. Keys sample: {list(INFO_FILES.keys())[:5] if INFO_FILES else 'N/A'}")

        # --- Critical Check ---
        # Check if the dictionaries are empty or None after attempting to load
        if not CHARACTER_IMAGE_MAP or not CHARACTER_ICON_MAP or not INFO_FILES:
             print("ERROR: Essential configuration files (JSON) missing or invalid. Cannot continue.")
             # Try to show a message box if the app object exists
             app_instance = QApplication.instance()
             if app_instance:
                 QMessageBox.critical(None,"Fatal Error","Essential config files (JSON) missing or invalid. Check paths and JSON format.")
                 app_instance.quit()
             sys.exit(1) # Exit forcefully if app isn't fully up
    # --- END OF DEFINITIVE _load_external_config METHOD ---
        
    # Keep _create_scroll_area (unchanged)
    def _create_scroll_area(self):
        self.scroll_area = QScrollArea(); self.scroll_area.setWidgetResizable(True); self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff); self.scroll_area.setStyleSheet("QScrollArea { padding-top: %dpx; }" % SCROLL_PADDING_TOP); self.scroll_content_widget = QWidget()
    def _create_scroll_area(self):
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setStyleSheet("QScrollArea { padding-top: %dpx; }" % SCROLL_PADDING_TOP)
        self.scroll_content_widget = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_content_widget)
        self.scroll_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.scroll_layout.setSpacing(15)
        self.scroll_area.setWidget(self.scroll_content_widget)
        self.main_layout.addWidget(self.scroll_area)
        """Creates/recreates card widgets based on ACTIVE_CHARACTER_LIST."""
        print("Populating character cards...");
        # Clear existing cards from layout AND cache
        while self.scroll_layout.count():
             item = self.scroll_layout.takeAt(0)
             if item and item.widget(): item.widget().deleteLater()
        self.character_cards.clear()

        if not ACTIVE_CHARACTER_LIST: print("No characters loaded to populate cards."); return

        loaded_count = 0
        for name in ACTIVE_CHARACTER_LIST:
            # Load data ONLY when creating the card
            char_data = self.load_single_character_data(name)
            if char_data is None:
                print(f"  Skipping card for '{name}': Failed to load JSON data.")
                continue # Skip if data fails to load

            is_fav = name in self.favorites
            card = CharacterCard(name, char_data, is_fav) # Pass loaded data
            card.favorite_toggled.connect(self.handle_favorite_toggle)
            self.character_cards[name] = card # Add widget to cache
            self.scroll_layout.addWidget(card)
            card.setVisible(False) # Initially hide until filter step
            loaded_count += 1

        print(f"Created/Recreated {loaded_count} card widgets.")

    def load_single_character_data(self, character_name):
        """Loads JSON data for a single character, handling filename sanitization."""
        # Sanitize name (space to _, & to and)
        safe_filename_base = character_name.replace(' ', '_').replace('&', 'and')
        filename = f"{safe_filename_base}.json"
        if DEBUG_MODE:
            print(f"DEBUG (Dashboard Load): Sanitized filename: {filename}")
        filepath = os.path.join(CHARACTER_DATA_FOLDER, filename)
        if DEBUG_MODE:
            print(f"DEBUG (Dashboard Load): Attempting to load path: {filepath}")

        if not os.path.exists(filepath):
            print(f"ERROR: JSON file not found for '{character_name}' at {filepath}")
            print(f"       (Check if file exists and name matches sanitized version: '{filename}')")
            return None

        data = None
        try:
            # Try reading with UTF-8-SIG first
            with open(filepath, 'r', encoding='utf-8-sig') as f:
                # REMOVED comment stripping - Parse directly
                data = json.load(f)
        except UnicodeDecodeError:
             # Fallback to plain UTF-8
             try:
                 with open(filepath, 'r', encoding='utf-8') as f:
                     # REMOVED comment stripping - Parse directly
                     data = json.load(f)
             except Exception as e_inner:
                print(f"ERROR loading {filepath} (UTF-8 fallback): {e_inner}")
                return None
        except json.JSONDecodeError as e_json:
            # Provide more specific JSON error info
            print(f"ERROR: Invalid JSON in {filepath}: {e_json}")
            print(f"       Error is at line {e_json.lineno}, column {e_json.colno}")
            # Optionally try to read the file content for debugging the JSON error
            try:
                with open(filepath, 'r', encoding='utf-8') as f_err: # Use plain utf-8 for reading raw error content
                    print(f"--- Corrupt JSON Content Snippet ({filename}) ---")
                    print(f_err.read(500)) # Print first 500 chars
                    print(f"--- End Snippet ---")
            except Exception as read_err:
                print(f"(Could not read file to show snippet: {read_err})")
            return None # Return None if JSON is invalid
        except Exception as e: # Catch other file reading errors
            print(f"ERROR loading {filepath}: {e}")
            return None

        # Final check if data is a dictionary
        if isinstance(data, dict):
             # print(f"Successfully loaded and parsed: {filepath}") # Optional success confirmation
            return data
        else:
            print(f"ERROR: Data loaded from {filepath} is not a dictionary (Type: {type(data)}).")
            return None

    def populate_character_cards(self):
        """Creates/recreates card widgets based on ACTIVE_CHARACTER_LIST."""
        print("Populating character cards...")
        # Clear existing cards from layout AND cache
        while self.scroll_layout.count():
             item = self.scroll_layout.takeAt(0)
             if item and item.widget(): item.widget().deleteLater()
        self.character_cards.clear()

        if not ACTIVE_CHARACTER_LIST:
            print("No characters loaded to populate cards.")
            return

        loaded_count = 0
        # Iterates through the list of names (e.g., "Adam Warlock", "Hulk")
        for name in ACTIVE_CHARACTER_LIST:
            # Calls the *modified* load function, passing the original name
            char_data = self.load_single_character_data(name) # This function now handles the underscore conversion internally

            # Checks if loading was successful
            if char_data is None:
                print(f"  Skipping card for '{name}': Failed to load JSON data (check dashboard logs and file path).")
                continue # Skip card creation if data couldn't be loaded

            # Proceeds to create the card if data loaded successfully
            is_fav = name in self.favorites
            card = CharacterCard(name, char_data, is_fav) # Pass original name and loaded data
            card.favorite_toggled.connect(self.handle_favorite_toggle)
            self.character_cards[name] = card # Add card widget to cache
            self.scroll_layout.addWidget(card) # Add card to the scroll layout
            card.setVisible(False) # Initially hide until filter step applies visibility
            loaded_count += 1

        print(f"Created/Recreated {loaded_count} card widgets.")

# Inside MainWindow class in rivals_dashboard.py

# --- Inside MainWindow class in rivals_dashboard.py ---

    @Slot(str)
    def jump_to_character(self, character_name):
        if DEBUG_MODE:print(f"\nDEBUG Jump: Clicked on '{character_name}'") # From ClickEvent debug
        card_widget = self.character_cards.get(character_name)
        if DEBUG_MODE: print(f"DEBUG Jump: Card widget found in dict? {'Yes' if card_widget else 'No'}")

        if card_widget:
            # --- Force layout update before checking visibility/position ---
            # Ensure the scroll content widget and its layout update sizes
            self.scroll_content_widget.layout().activate()
            self.scroll_content_widget.adjustSize()
            QApplication.processEvents() # Allow GUI to process the updates
            # --- End force layout update ---

            is_visible = card_widget.isVisible()
            if DEBUG_MODE: print(f"DEBUG Jump: Card widget is visible? {is_visible}")

            if is_visible:
                v_scroll_bar = self.scroll_area.verticalScrollBar()
                # --- Add check for scroll bar range ---
                scrollbar_min = v_scroll_bar.minimum()
                scrollbar_max = v_scroll_bar.maximum()
                if DEBUG_MODE: print(f"DEBUG Jump: Scrollbar range before scroll: min={scrollbar_min}, max={scrollbar_max}, current={v_scroll_bar.value()}")
                # --- End check for scroll bar range ---

                # --- Get position *after* potential layout updates ---
                target_y = card_widget.pos().y()
                offset = SCROLL_PADDING_TOP # Use defined constant
                # Ensure max is at least min before calculating range
                if scrollbar_max < scrollbar_min:
                     print(f"WARN Jump: Scrollbar max ({scrollbar_max}) is less than min ({scrollbar_min}). Clamping max.")
                     scrollbar_max = scrollbar_min # Prevent errors in calculation below

                # Calculate target scroll position, clamping within valid range
                scroll_to_y = max(scrollbar_min, min(target_y - offset, scrollbar_max))

                if DEBUG_MODE: print(f"DEBUG Jump: Card pos().y = {target_y}, Offset = {offset}, Calculated ScrollTo = {scroll_to_y}")

                # Check if calculated value is different from current
                if scroll_to_y == v_scroll_bar.value():
                    if DEBUG_MODE: print(f"DEBUG Jump: Calculated scroll position ({scroll_to_y}) is same as current. No scroll needed?")
                    # If it's already at the target, maybe nothing happens visually.

                # Set the value
                v_scroll_bar.setValue(scroll_to_y)
                QApplication.processEvents() # Process events again AFTER setting value
                if DEBUG_MODE: print(f"DEBUG Jump: Scrollbar value AFTER set attempt = {v_scroll_bar.value()}")

            else:
                print(f"Cannot jump to '{character_name}', card widget exists but is not visible (check filters).")
        else:
             if DEBUG_MODE:print(f"Cannot jump to '{character_name}', card widget not found in self.character_cards dictionary.")
        if DEBUG_MODE:print(f"\nDEBUG Jump: Clicked on '{character_name}'")
        card_widget = self.character_cards.get(character_name)
        if DEBUG_MODE: print(f"DEBUG Jump: Card widget found in dict? {'Yes' if card_widget else 'No'}")

        if card_widget:
            # --- Force layout update before checking visibility/position ---
            # Ensure the scroll content widget and its layout update sizes
            self.scroll_content_widget.layout().activate()
            self.scroll_content_widget.adjustSize()
            QApplication.processEvents() # Allow GUI to process the updates
            # --- End force layout update ---

            is_visible = card_widget.isVisible()
            if DEBUG_MODE: print(f"DEBUG Jump: Card widget is visible? {is_visible}")

            if is_visible:
                v_scroll_bar = self.scroll_area.verticalScrollBar()
                # --- Add check for scroll bar range ---
                scrollbar_min = v_scroll_bar.minimum()
                scrollbar_max = v_scroll_bar.maximum()
                if DEBUG_MODE: print(f"DEBUG Jump: Scrollbar range before scroll: min={scrollbar_min}, max={scrollbar_max}, current={v_scroll_bar.value()}")
                # --- End check for scroll bar range ---

                # --- Get position *after* potential layout updates ---
                target_y = card_widget.pos().y()
                offset = SCROLL_PADDING_TOP
                # Ensure max is at least min before calculating range
                if scrollbar_max < scrollbar_min:
                     print(f"WARN Jump: Scrollbar max ({scrollbar_max}) is less than min ({scrollbar_min}). Clamping max.")
                     scrollbar_max = scrollbar_min # Prevent errors in calculation below

                # Calculate target scroll position, clamping within valid range
                scroll_to_y = max(scrollbar_min, min(target_y - offset, scrollbar_max))

                if DEBUG_MODE: print(f"DEBUG Jump: Card pos().y = {target_y}, Offset = {offset}, Calculated ScrollTo = {scroll_to_y}")

                # Check if calculated value is different from current
                if scroll_to_y == v_scroll_bar.value():
                    if DEBUG_MODE: print(f"DEBUG Jump: Calculated scroll position ({scroll_to_y}) is same as current. No scroll needed?")
                    # If it's already at the target, maybe nothing happens visually.
                    # Could add a small visual "bump" if needed for feedback, but let's see if scrolling works first.

                # Set the value
                v_scroll_bar.setValue(scroll_to_y)
                QApplication.processEvents() # Process events again AFTER setting value
                if DEBUG_MODE: print(f"DEBUG Jump: Scrollbar value AFTER set attempt = {v_scroll_bar.value()}")

            else:
                if DEBUG_MODE: print(f"Cannot jump to '{character_name}', card widget exists but is not visible (check filters).")
        else:
             if DEBUG_MODE: print(f"Cannot jump to '{character_name}', card widget not found in self.character_cards dictionary.")


    @Slot(str, bool)
    def handle_favorite_toggle(self, character_name, is_favorite):
        if is_favorite: self.favorites.add(character_name); print(f"Added '{character_name}' to favorites.")
        else: self.favorites.discard(character_name); print(f"Removed '{character_name}' from favorites.")
        save_favorites(self.favorites)
        if self.sort_combo.currentText() == "Favorites First": self.sort_and_filter_characters() # Resort if needed

    # --- Replace this entire method in MainWindow ---
    def filter_characters(self):
        # Get the current search term and role filter
        search_term = self.search_input.text().lower().strip()
        selected_role_filter = self.filter_combo.currentText().split(": ")[-1]

        # Determine if filters are active
        # Only search if term is long enough (or empty to show all matching role filter)
        search_active = len(search_term) >= MIN_SEARCH_LENGTH
        role_filter_active = selected_role_filter != "All"

        visible_count = 0
        # Iterate through all character cards stored in the dictionary
        for name, card in self.character_cards.items():
            show_card = True # Assume card is visible initially

            # Apply Role Filter first
            if role_filter_active:
                 # Access character data stored within the card object
                 char_data = card.character_data
                 # Safely get the role, default to empty string if missing or data invalid
                 char_role = char_data.get('role', '').lower() if isinstance(char_data, dict) else ''
                 # Hide card if role doesn't match the selected filter
                 if selected_role_filter.lower() != char_role:
                     show_card = False

            # Apply Search Filter (only if card hasn't been hidden by role filter)
            # --- MODIFIED SEARCH LOGIC ---
            if show_card and search_term: # Check if search term is not empty
                # Compare the search term ONLY against the character's name (case-insensitive)
                match = search_term in name.lower() # 'name' is the key in self.character_cards
                if not match:
                    show_card = False # Hide card if name doesn't contain the search term
            # --- END MODIFIED SEARCH LOGIC ---


            # Set the card's visibility based on the filter results
            card.setVisible(show_card)
            if show_card:
                visible_count += 1 # Increment count if card is visible

        # Optional Debug Print
        if DEBUG_MODE:
            print(f"DEBUG Filter: Search='{search_term}', Role='{selected_role_filter}'. Visible={visible_count}/{len(self.character_cards)}")

    def sort_and_filter_characters(self):
        print("Sorting and filtering cards..."); sort_key = self.sort_combo.currentText(); widgets_to_sort = []
        # Detach all card widgets currently in the layout
        items_to_readd = []
        while self.scroll_layout.count():
             item = self.scroll_layout.takeAt(0)
             if item and item.widget() and isinstance(item.widget(), CharacterCard):
                 widget = item.widget(); widget.setParent(None); widgets_to_sort.append(widget)
             elif item: items_to_readd.append(item) # Keep non-card items

        # Define sort key functions
        def get_name(widget): return widget.character_name
        def get_role(widget): return widget.character_data.get('role', 'ZZZ') if isinstance(widget.character_data, dict) else 'ZZZ' # Handle non-dict data
        def get_favorite_then_name(widget): return (0 if widget.character_name in self.favorites else 1, widget.character_name)

        # Sort the detached widgets
        if sort_key == "Sort by Name": widgets_to_sort.sort(key=get_name)
        elif sort_key == "Sort by Role": widgets_to_sort.sort(key=lambda w: (get_role(w), get_name(w)))
        elif sort_key == "Favorites First": widgets_to_sort.sort(key=get_favorite_then_name)

        # Re-add sorted widgets to the layout
        for widget in widgets_to_sort: self.scroll_layout.addWidget(widget)
        # Re-add any non-card items
        for item in items_to_readd: self.scroll_layout.addItem(item)

        self.filter_characters(); # Apply filtering after sorting
        print("Sorting and filtering complete.")

    # Keep _show_info_popup (unchanged)
    @Slot(str)
    def _show_info_popup(self, info_key):
        print(f"Showing info popup for '{info_key}'"); info_filename = INFO_FILES.get(info_key)
        if not info_filename: QMessageBox.warning(self, "Info", f"No file defined for '{info_key}'."); return
        info_filepath = os.path.join(INFO_FOLDER, info_filename); formatted_content = ""
        try:
            if os.path.exists(info_filepath):
                with open(info_filepath, 'r', encoding='utf-8') as f: raw_content = f.read()
                formatted_content = _format_info_text(raw_content)
            else: formatted_content = f"<p style='color: red;'>Info file not found:\n{info_filepath}</p>"
        except Exception as e: error_msg = f"Error reading info file:\n{info_filepath}\n\n{e}"; print(error_msg); formatted_content = f"<p style='color: red;'>{error_msg}</p>"
        dialog_title = info_key; dialog = InfoPopupDialog(dialog_title, formatted_content, self); dialog.exec()

    # Keep _confirm_launch_updater (MODIFIED to launch updater_v3.py)
    @Slot()
    def _confirm_launch_updater(self):
        reply = QMessageBox.question(self, "Launch Updater?", "This will close the dashboard and open the Updater tool (updater_v3.py).\n\nAre you sure?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            print("User confirmed. Launching updater_v3.py...")
            try:
                script_dir = os.path.dirname(__file__); # Dir of dashboard
                updater_script_path = os.path.normpath(os.path.join(script_dir, 'scraper', 'updater_v3.py')) # Path relative to dashboard

                if os.path.exists(updater_script_path):
                    print(f"Found updater script at: {updater_script_path}")
                    # Use sys.executable to ensure it runs with the same Python interpreter
                    subprocess.Popen([sys.executable, updater_script_path])
                    QApplication.instance().quit() # Close dashboard
                else:
                    error_msg = f"Updater script not found at:\n{updater_script_path}"; print(f"ERROR: {error_msg}"); QMessageBox.critical(self, "Error", error_msg)
            except Exception as e: error_msg = f"Failed to launch updater: {e}"; print(f"ERROR: {error_msg}"); QMessageBox.critical(self, "Launch Error", error_msg)
    @Slot()
    def _start_json_update(self):
        """Starts the JSON update process in a background thread."""
        print("JSON Update: Button clicked.")

        # Prevent starting multiple updates simultaneously
        if self.json_update_worker and self.json_update_worker.isRunning():
            print("JSON Update: Update process already running.")
            QMessageBox.information(self, "Update in Progress", "An update check is already running.")
            return

        # Disable the button during update
        self.json_update_button.setEnabled(False)
        self.json_update_button.setText("Checking...") # Provide visual feedback

        # --- Define GitHub API URL and Local Directory ---
        # Make sure CHARACTER_DATA_FOLDER is defined correctly globally
        local_dir = CHARACTER_DATA_FOLDER
        repo_api_url = "https://api.github.com/repos/Reg0lino/Marvel-Rivals-Dashboard/contents/characters?ref=main" # Use 'main' branch

        print(f"JSON Update: Starting worker. Repo: {repo_api_url}, Local Dir: {local_dir}")

        # Create and configure the worker thread
        self.json_update_worker = JsonUpdateWorker(repo_api_url, local_dir)

        # Connect worker signals to MainWindow slots
        self.json_update_worker.progress.connect(self._handle_update_progress)
        self.json_update_worker.finished.connect(self._handle_update_finished)

        # Start the thread execution (calls the worker's run() method)
        self.json_update_worker.start()
        print("JSON Update: Worker thread started.")

    # --- ADD this new method ---
    @Slot(int, int, str)
    def _handle_update_progress(self, current_file, total_files, filename):
        """Updates the button text to show download progress."""
        # Basic progress update on the button itself
        progress_text = f"Downloading {current_file + 1}/{total_files}..."
        self.json_update_button.setText(progress_text)
        # Optional: print to console as well
        # print(f"Progress: {progress_text} ({filename})")

    # --- ADD this new method ---
    @Slot(bool, str)
    def _handle_update_finished(self, success, message):
        """Handles the completion signal from the worker thread."""
        print(f"JSON Update: Worker finished. Success: {success}, Message: {message}")

        # Re-enable the button and reset text
        self.json_update_button.setEnabled(True)
        self.json_update_button.setText("Check for Data Updates")

        # Show appropriate message box
        if success:
            QMessageBox.information(self, "Update Complete", message)
        else:
            QMessageBox.warning(self, "Update Failed", message)

        # Clean up the worker thread reference
        self.json_update_worker = None
        print("JSON Update: Worker reference cleaned up.")

# --- Main Execution ---
if __name__ == "__main__":
    # --- Argument Parsing ---
    # Setup parser first, BEFORE QApplication instance
    parser = argparse.ArgumentParser(description="Marvel Rivals Dashboard")
    parser.add_argument('--debug', action='store_true', help='Enable detailed console logging.')
    parser.add_argument('--screen', type=str, default=None, help='Name of the target screen to launch on.')
    parser.add_argument('--fullscreen', action='store_true', help='Start in fullscreen mode.')
    # Parse arguments passed from launcher (or command line)
    args = parser.parse_args()

    # --- Set Global DEBUG_MODE ---
    # This MUST be done before any code that uses DEBUG_MODE
    DEBUG_MODE = args.debug
    print(f"Executing rivals_dashboard.py... DEBUG_MODE={'ON' if DEBUG_MODE else 'OFF'}")
    # --- End Global DEBUG_MODE Setting ---

    # --- Basic App setup ---
    try:
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)
    except AttributeError: pass
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)

    app = QApplication(sys.argv) # Create App instance AFTER parsing

    # --- Font Loading ---
    # (Keep your existing font loading logic here)
    SYSTEM_FONT_FAMILY_NAME = QApplication.font().family(); CURRENT_FONT_FAMILY_NAME = SYSTEM_FONT_FAMILY_NAME; CUSTOM_FONT_LOADED = False; CUSTOM_FONT_FAMILY_NAME = "Refrigerator Deluxe"
    print(f"Attempting to load custom fonts from: {FONT_FOLDER}")
    if os.path.isdir(FONT_FOLDER):
        loaded_font_id = -1; regular_font_file = FONT_FILES.get("Regular")
        if regular_font_file:
            font_path = os.path.join(FONT_FOLDER, regular_font_file)
            if os.path.exists(font_path):
                loaded_font_id = QFontDatabase.addApplicationFont(font_path)
                if loaded_font_id != -1: families = QFontDatabase.applicationFontFamilies(loaded_font_id); detected_family_name = families[0] if families else None; print(f"Loaded '{regular_font_file}'. Family: '{detected_family_name}'") if detected_family_name else print(f"ERROR: Could not get family name for font: {font_path}"); CUSTOM_FONT_FAMILY_NAME = detected_family_name or CUSTOM_FONT_FAMILY_NAME; CURRENT_FONT_FAMILY_NAME = CUSTOM_FONT_FAMILY_NAME; CUSTOM_FONT_LOADED = True
                else: print(f"ERROR: Failed to load font: {font_path}")
            else: print(f"ERROR: Font file not found: {font_path}")
        if CUSTOM_FONT_LOADED:
            for style, filename in FONT_FILES.items():
                if style != "Regular":
                     font_path = os.path.join(FONT_FOLDER, filename)
                     if os.path.exists(font_path): font_id = QFontDatabase.addApplicationFont(font_path); print(f"Loaded variant: {filename}") if font_id != -1 else print(f"ERROR loading variant: {font_path}")
                     else: print(f"ERROR font file not found: {font_path}")
    else: print(f"WARNING: Custom font folder not found: {FONT_FOLDER}")
    if CUSTOM_FONT_LOADED: print(f"Using custom font: '{CURRENT_FONT_FAMILY_NAME}'")
    else: print(f"WARNING: Using system default font '{SYSTEM_FONT_FAMILY_NAME}' as custom font failed to load.")
    # --- End Font Loading ---

    # Load JSON Config
    CHARACTER_IMAGE_MAP = load_json_config('character_images.json')
    CHARACTER_ICON_MAP = load_json_config('character_icons.json')
    INFO_FILES = load_json_config('info_files.json')

    app.setStyleSheet(get_stylesheet()) # Apply stylesheet

    try:
        window = MainWindow() # Instantiate main window

        # --- Screen and Fullscreen Handling ---
        target_screen = None
        primary_screen = QApplication.primaryScreen() # Get primary screen reference

        if args.screen: # If screen name was passed by launcher
            available_screens = QApplication.screens()
            screen_found = False
            # Compare screen names carefully, handle potential None names
            for screen in available_screens:
                current_screen_name = screen.name() if screen.name() else f"Unknown_{available_screens.index(screen)}"
                if current_screen_name == args.screen:
                    target_screen = screen
                    print(f"Dashboard: Using target screen specified by launcher: {args.screen}")
                    screen_found = True
                    break
            if not screen_found:
                print(f"Dashboard Warning: Screen '{args.screen}' passed by launcher not found. Using primary screen.")
                target_screen = primary_screen
        else: # Default to primary screen if none specified
            print("Dashboard: No screen specified by launcher. Using primary screen.")
            target_screen = primary_screen

        # Fallback if target_screen is still somehow None (shouldn't happen if primary exists)
        if not target_screen:
            print("Dashboard Error: Could not determine target screen! Showing on first available.")
            target_screen = QApplication.screens()[0] if QApplication.screens() else None

        if target_screen:
            screen_geometry = target_screen.geometry() # Use full geometry for fullscreen basis
            available_geometry = target_screen.availableGeometry() # Use available for windowed centering

            if args.fullscreen:
                print("Dashboard: Setting fullscreen mode.")
                # Set geometry to the full screen dimensions BEFORE showing fullscreen
                window.setGeometry(screen_geometry)
                window.showFullScreen()
            else: # Windowed mode positioning
                print("Dashboard: Setting windowed mode.")
                # --- Explicitly set desired size ---
                desired_width = 1000
                desired_height = 950
                print(f"Dashboard: Attempting to set initial size to {desired_width}x{desired_height}")

                # Clamp desired size to AVAILABLE screen geometry to prevent oversized windows
                safe_width = min(desired_width, available_geometry.width())
                safe_height = min(desired_height, available_geometry.height())
                if safe_width != desired_width or safe_height != desired_height:
                    print(f"Dashboard Warning: Clamped window size to {safe_width}x{safe_height} to fit screen.")

                window.resize(safe_width, safe_height)
                # --- End explicit size setting ---

                # Center on target screen's AVAILABLE geometry
                print(f"Dashboard: Centering window on screen '{target_screen.name()}'.")
                center_point = available_geometry.center()
                window_geo = window.frameGeometry() # Get geometry *after* resize
                window_geo.moveCenter(center_point)

                # Clamp position to stay within available geometry
                final_pos = window_geo.topLeft()
                final_pos.setX(max(available_geometry.left(), min(final_pos.x(), available_geometry.right() - window_geo.width())))
                final_pos.setY(max(available_geometry.top(), min(final_pos.y(), available_geometry.bottom() - window_geo.height())))
                window.move(final_pos)

                window.show() # Show windowed AFTER setting size and position
        else:
            # This case should be extremely rare if Qt detects any screens
            print("Dashboard Error: No target screen could be determined. Showing with default size/position.")
            window.resize(1020, 1000) # Set default size as fallback
            window.show()
        # --- End Screen and Fullscreen Handling ---

        sys.exit(app.exec()) # Start the dashboard's event loop

    except RuntimeError as e: print(f"Dashboard halted during init: {e}"); sys.exit(1)
    except Exception as e: import traceback; traceback.print_exc(); QMessageBox.critical(None, "Fatal Startup Error", f"An unexpected error occurred:\n{e}\n\nSee console for details."); sys.exit(1)
    # --- Argument Parsing for Debug Mode ---
    parser = argparse.ArgumentParser(description="Marvel Rivals Dashboard")
    parser.add_argument('--debug', action='store_true', help='Enable detailed console logging.')
    # Add other arguments if needed later (like screen/fullscreen if not handled internally)
    # parser.add_argument('--screen', type=str, help='Target screen name.')
    # parser.add_argument('--fullscreen', action='store_true', help='Start in fullscreen.')
    args = parser.parse_args()

    # --- SET DEBUG_MODE based on argument ---
    # Find the DEBUG_MODE = False line near the top constants and DELETE it.
    # This command-line argument now controls it.
    DEBUG_MODE = args.debug
    print(f"Executing rivals_dashboard.py... DEBUG_MODE={'ON' if DEBUG_MODE else 'OFF'}")
    # --- End Argument Parsing ---

    app = QApplication(sys.argv) # Keep app creation after parsing

    # --- Font Loading (Unchanged) ---
    SYSTEM_FONT_FAMILY_NAME = QApplication.font().family(); CURRENT_FONT_FAMILY_NAME = SYSTEM_FONT_FAMILY_NAME; CUSTOM_FONT_LOADED = False; CUSTOM_FONT_FAMILY_NAME = "Refrigerator Deluxe"
    print(f"Attempting to load custom fonts from: {FONT_FOLDER}")
    if os.path.isdir(FONT_FOLDER):

        # --- Pass parsed args (or handle screen/fullscreen inside MainWindow) ---
        # For now, let's keep screen/fullscreen handling inside MainWindow based on primary screen detection.
        # If you want launcher to dictate, you'd pass args.screen, args.fullscreen here.
            window = MainWindow() # MainWindow now uses dynamic list loading
        # ... (rest of your main block: screen centering, window.show(), app.exec()) ...

    # --- Font Loading (Unchanged) ---
    SYSTEM_FONT_FAMILY_NAME = QApplication.font().family(); CURRENT_FONT_FAMILY_NAME = SYSTEM_FONT_FAMILY_NAME; CUSTOM_FONT_LOADED = False; CUSTOM_FONT_FAMILY_NAME = "Refrigerator Deluxe"
    print(f"Attempting to load custom fonts from: {FONT_FOLDER}")
    if os.path.isdir(FONT_FOLDER):
        loaded_font_id = -1; regular_font_file = FONT_FILES.get("Regular")
        if regular_font_file:
            font_path = os.path.join(FONT_FOLDER, regular_font_file)
            if os.path.exists(font_path):
                loaded_font_id = QFontDatabase.addApplicationFont(font_path)
                if loaded_font_id != -1: families = QFontDatabase.applicationFontFamilies(loaded_font_id); detected_family_name = families[0] if families else None; print(f"Loaded '{regular_font_file}'. Family: '{detected_family_name}'") if detected_family_name else print(f"ERROR: Could not get family name for font: {font_path}"); CUSTOM_FONT_FAMILY_NAME = detected_family_name or CUSTOM_FONT_FAMILY_NAME; CURRENT_FONT_FAMILY_NAME = CUSTOM_FONT_FAMILY_NAME; CUSTOM_FONT_LOADED = True
                else: print(f"ERROR: Failed to load font: {font_path}")
            else: print(f"ERROR: Font file not found: {font_path}")
        if CUSTOM_FONT_LOADED:
            for style, filename in FONT_FILES.items():
                if style != "Regular":
                     font_path = os.path.join(FONT_FOLDER, filename)
                     if os.path.exists(font_path): font_id = QFontDatabase.addApplicationFont(font_path); print(f"Loaded variant: {filename}") if font_id != -1 else print(f"ERROR loading variant: {font_path}")
                     else: print(f"ERROR font file not found: {font_path}")
    else: print(f"WARNING: Custom font folder not found: {FONT_FOLDER}")
    if CUSTOM_FONT_LOADED: print(f"Using custom font: '{CURRENT_FONT_FAMILY_NAME}'")
    else: print(f"WARNING: Using system default font '{SYSTEM_FONT_FAMILY_NAME}' as custom font failed to load.")

    # Load JSON Config (Images, Icons, Info - Unchanged)
    CHARACTER_IMAGE_MAP = load_json_config('character_images.json'); 
    CHARACTER_ICON_MAP = load_json_config('character_icons.json'); 
    INFO_FILES = load_json_config('info_files.json')
    
    app.setStyleSheet(get_stylesheet()) # Apply stylesheet

    try:
        window = MainWindow() # MainWindow now uses dynamic list loading

        # Screen centering (Unchanged)
        try:
            primary_screen = QApplication.primaryScreen()
            if primary_screen: screen_geometry = primary_screen.availableGeometry(); window_size = window.sizeHint(); max_w = screen_geometry.width() * 0.9; max_h = screen_geometry.height() * 0.9; window_size.setWidth(min(window_size.width(), int(max_w))); window_size.setHeight(min(window_size.height(), int(max_h))); x = (screen_geometry.width() - window_size.width()) // 2; y = (screen_geometry.height() - window_size.height()) // 2; x = max(screen_geometry.x(), screen_geometry.x() + x); y = max(screen_geometry.y(), screen_geometry.y() + y); window.move(x, y); print(f"Centering on screen: {primary_screen.name()}")
            else: print("Could not get primary screen information.")
        except Exception as e: print(f"Error during screen positioning: {e}")

        window.show()
        sys.exit(app.exec())

    except RuntimeError as e: print(f"Application halted during init: {e}"); sys.exit(1)
    except Exception as e: import traceback; traceback.print_exc(); QMessageBox.critical(None, "Fatal Startup Error", f"An unexpected error occurred:\n{e}\n\nSee console for details."); sys.exit(1)