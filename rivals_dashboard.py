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

# --- FlowLayout Implementation (Keep As Is) ---
class FlowLayout(QLayout):
    # ... (Keep the existing FlowLayout code exactly as it was) ...
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
        style = self.parentWidget().style() if self.parentWidget() else QApplication.style()
        for item in self._items:
            widget = item.widget()
            spaceX = self.horizontalSpacing()
            if spaceX == -1: spaceX = style.layoutSpacing(QSizePolicy.ControlType.PushButton, QSizePolicy.ControlType.PushButton, Qt.Orientation.Horizontal)
            spaceY = self.verticalSpacing()
            if spaceY == -1: spaceY = style.layoutSpacing(QSizePolicy.ControlType.PushButton, QSizePolicy.ControlType.PushButton, Qt.Orientation.Vertical)
            nextX = x + item.sizeHint().width() + spaceX
            if nextX - spaceX > effectiveRect.right() and lineHeight > 0:
                x = effectiveRect.x()
                y = y + lineHeight + spaceY
                nextX = x + item.sizeHint().width() + spaceX
                lineHeight = 0
            if not testOnly: item.setGeometry(QRect(QPoint(x, y), item.sizeHint()))
            x = nextX
            lineHeight = max(lineHeight, item.sizeHint().height())
        return y + lineHeight - rect.y() + margins.bottom()

    def smartSpacing(self, pm):
        parent = self.parent()
        if not parent: return -1
        elif parent.isWidgetType(): return parent.style().pixelMetric(pm, None, parent)
        else: style = QApplication.style(); return style.pixelMetric(pm) if style else 5

# --- Helper Function for Resource Paths (Keep As Is) ---
def resource_path(relative_path):
    try: base_path = sys._MEIPASS
    except AttributeError: base_path = os.path.abspath(os.path.dirname(__file__))
    return os.path.normpath(os.path.join(base_path, relative_path))

# --- Configuration Paths (Keep As Is) ---
CHARACTER_DATA_FOLDER = resource_path('characters')
IMAGE_FOLDER = resource_path('images')
INFO_FOLDER = resource_path('info')
CONFIG_FOLDER = resource_path('config')
STYLES_FOLDER = resource_path('styles')
FONT_FOLDER = resource_path('styles/font')

# --- AppData/Favorites Path (Keep As Is) ---
app_data_path = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)
if not app_data_path: app_data_path = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.GenericDataLocation)
app_data_root = os.path.dirname(app_data_path) if app_data_path else None
if app_data_root and not os.path.exists(app_data_root):
    try: os.makedirs(app_data_root); print(f"Created app data root directory: {app_data_root}")
    except OSError as e: print(f"Warning: Could not create app data root directory {app_data_root}: {e}"); app_data_path = None
if app_data_path and not os.path.exists(app_data_path):
    try: os.makedirs(app_data_path); print(f"Created app data directory: {app_data_path}")
    except OSError as e: print(f"Warning: Could not create app data directory {app_data_path}: {e}"); app_data_path = None
if app_data_path: FAVORITES_FILE = os.path.join(app_data_path, 'rivals_dashboard_favorites.json'); print(f"Using favorites path: {FAVORITES_FILE}")
else: FAVORITES_FILE = resource_path('rivals_dashboard_favorites.json'); print(f"Warning: Could not get/create standard app data path. Using fallback: {FAVORITES_FILE}")

# --- Font Configuration (Keep As Is) ---
SYSTEM_FONT_FAMILY_NAME = "Segoe UI"; CUSTOM_FONT_FAMILY_NAME = "Refrigerator Deluxe"; CURRENT_FONT_FAMILY_NAME = SYSTEM_FONT_FAMILY_NAME; CUSTOM_FONT_LOADED = False
FONT_FILES = {"Regular": "Refrigerator Deluxe.otf", "Bold": "Refrigerator Deluxe Bold.otf", "Heavy": "Refrigerator Deluxe Heavy.otf", "Light": "Refrigerator Deluxe Light.otf"}

# --- Constants (Keep As Is, including DEBUG_MODE handled by argparse later) ---
DEBUG_MODE = False # Will be overwritten by command-line args if present
# --- Debug Mode Toggle ---
# Set to True to see detailed debug messages in the console, False to hide them
# DEBUG_MODE = False # <--- EDIT THIS LINE (True/False) TO TOGGLE DEBUG OUTPUT - REMOVED, handled by args
# print(f"CONFIRMATION: DEBUG_MODE is currently set to: {DEBUG_MODE}") # Removed, printed in main block
READY_FLAG_FILENAME = "dashboard_ready.flag"
READY_FLAG_FILE = os.path.join(CONFIG_FOLDER, READY_FLAG_FILENAME)

DEFAULT_THEME_COLOR = "#888888"; DEFAULT_SECONDARY_THEME_COLOR = "#CCCCCC"; BASE_FONT_SIZE = 13; CURRENT_GLOBAL_FONT_SIZE_PT = float(BASE_FONT_SIZE); HEADER_FONT_SIZE = BASE_FONT_SIZE + 4
GROUP_TITLE_FONT_SIZE = BASE_FONT_SIZE + 4; CHARACTER_NAME_FONT_SIZE = 32; JUMP_BAR_FIXED_ICON_SIZE = 46; JUMP_BAR_FIXED_SPACING = 4; DETAILS_COLOR = "#B8B8B8"; LORE_COLOR = "#C8C8C8"
ABILITY_TITLE_STYLE_TEMPLATE = f"font-size: 1.1em; font-weight: {QFont.Weight.Bold}; color: {{color}};"
SECTION_TITLE_STYLE_TEMPLATE = f"font-size: 1.05em; font-weight: {QFont.Weight.Bold}; color: {{color}};"
FIELD_LABEL_STYLE = f"font-weight: {QFont.Weight.Bold}; color: #D0D0D0;"; FIELD_VALUE_STYLE = f"font-weight: {QFont.Weight.Normal}; color: #E5E5E5;"; LIST_ITEM_STYLE = f"margin-left: 15px; margin-top: 1px; margin-bottom: 1px; font-weight: {QFont.Weight.Normal};"
QUOTE_STYLE = f"font-style: italic; color: {LORE_COLOR}; border-left: 3px solid {LORE_COLOR}; padding-left: 10px; margin-top: 4px; margin-bottom: 4px; font-weight: {QFont.Weight.Normal};"
H1_COLOR = "#FBBF2C"; H2_COLOR = "#60A5FA"; H3_COLOR = "#F87171"; LIST_STYLE = "margin-left: 20px; margin-top: 3px; margin-bottom: 3px;"; INFO_POPUP_UNDERLINE_COLOR = "#FBBF2C"
BOLD_UNDERLINE_STYLE_TEMPLATE_POPUP = f"font-weight: bold; text-decoration: underline; color: {INFO_POPUP_UNDERLINE_COLOR};"; SCROLL_PADDING_TOP = 10; MIN_SEARCH_LENGTH = 3
SEARCH_SEASON_STRING = "Season 2"

# --- Configuration Dictionaries (Loaded Later) ---
CHARACTER_IMAGE_MAP = {}; CHARACTER_ICON_MAP = {}; INFO_FILES = {}
# --- NEW: For Optimization ---
CHARACTER_SUMMARY_DATA = [] # Will store [{'name': ..., 'role': ..., 'icon_file': ..., 'image_file': ...}]


# --- Helper Functions (Keep load_json_config, load_favorites, save_favorites, get_stylesheet) ---
def load_json_config(filename, default_value={}):
    filepath = os.path.join(CONFIG_FOLDER, filename)
    try:
        with open(filepath, 'r', encoding='utf-8') as f: content = "".join(line for line in f if not line.strip().startswith("//"))
        return json.loads(content)
    except FileNotFoundError: print(f"ERROR: Config file not found: {filepath}"); return default_value
    except json.JSONDecodeError as e: print(f"ERROR: Invalid JSON in config file: {filepath} - {e}"); return default_value
    except Exception as e: print(f"ERROR: Failed to load config file: {filepath} - {e}"); return default_value

# --- REMOVED load_character_data (No longer needed for full data load at startup) ---

# --- NEW: Function to load minimal character summaries ---
def load_character_summaries():
    """
    Scans character JSON files to extract minimal summary data
    (name, role, icon_filename, image_filename) needed for initial display.
    Handles name normalization and potential file errors gracefully.
    """
    global CHARACTER_SUMMARY_DATA, CHARACTER_ICON_MAP, CHARACTER_IMAGE_MAP
    summaries = []
    target_dir = CHARACTER_DATA_FOLDER
    favorites = load_favorites() # Load favorites to include is_fav flag

    if not os.path.isdir(target_dir):
        print(f"ERROR: Character data folder not found: {target_dir}")
        QMessageBox.critical(None, "Startup Error", f"Character data folder missing:\n{target_dir}")
        CHARACTER_SUMMARY_DATA = []
        return # Stop if directory missing

    print("Loading character summaries...")
    file_count = 0
    error_count = 0
    processed_names = set() # Track names to avoid duplicates from different files

    try:
        for filename in os.listdir(target_dir):
            if not (filename.lower().endswith(".json") and not filename.lower().endswith(".api_error.txt")):
                continue # Skip non-JSON or error files

            filepath = os.path.join(target_dir, filename)
            if not os.path.isfile(filepath): continue

            file_count += 1
            char_data = None
            try:
                # Try UTF-8-SIG first
                with open(filepath, 'r', encoding='utf-8-sig') as f:
                    content = "".join(line for line in f if not line.strip().startswith("//"))
                    char_data = json.loads(content)
            except UnicodeDecodeError:
                # Fallback to plain UTF-8
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = "".join(line for line in f if not line.strip().startswith("//"))
                        char_data = json.loads(content)
                except Exception as e_inner:
                    print(f"  WARN: Failed read summary '{filename}' (UTF-8 Fallback): {e_inner}")
                    error_count += 1; continue
            except json.JSONDecodeError as e_json:
                print(f"  WARN: Invalid JSON for summary in '{filename}': {e_json}")
                error_count += 1; continue
            except Exception as e_load:
                print(f"  WARN: Failed load summary '{filename}': {e_load}")
                error_count += 1; continue

            # Process successfully loaded data
            if isinstance(char_data, dict):
                char_name_from_json = char_data.get("name")
                char_role = char_data.get("role")

                if char_name_from_json and isinstance(char_name_from_json, str):
                    normalized_name = char_name_from_json.strip()
                    # Apply specific corrections
                    if normalized_name == "Namor McKenzie": normalized_name = "Namor"
                    elif normalized_name == "The Punisher": normalized_name = "Punisher"
                    elif normalized_name == "Cloak and Dagger": normalized_name = "Cloak & Dagger"
                    elif normalized_name.isupper() and normalized_name != "MODOK":
                        normalized_name = normalized_name.title()

                    # Avoid adding duplicates if multiple files have the same name
                    if normalized_name in processed_names:
                        # print(f"  INFO: Skipping duplicate name '{normalized_name}' from file '{filename}'.")
                        continue
                    processed_names.add(normalized_name)

                    # Get icon/image filenames using flexible lookup
                    icon_file = get_config_value_flexible(CHARACTER_ICON_MAP, normalized_name)
                    image_file = get_config_value_flexible(CHARACTER_IMAGE_MAP, normalized_name)

                    summaries.append({
                        'name': normalized_name,
                        'role': char_role if isinstance(char_role, str) else None, # Ensure role is string or None
                        'icon_file': icon_file,
                        'image_file': image_file,
                        'is_fav': normalized_name in favorites # Check if favorite
                    })
                else:
                    print(f"  WARN: No valid 'name' field in '{filename}' for summary.")
                    error_count += 1
            else:
                print(f"  WARN: Data in '{filename}' is not a dictionary (Type: {type(char_data)}) for summary.")
                error_count += 1

        # Sort the final list of unique summaries by name
        CHARACTER_SUMMARY_DATA = sorted(summaries, key=lambda x: x['name'])
        print(f"Loaded summaries for {len(CHARACTER_SUMMARY_DATA)} unique characters from {file_count} JSON files scanned.")
        if error_count > 0:
            print(f"  ({error_count} files encountered errors during summary loading/parsing)")

    except OSError as e:
        print(f"ERROR reading character folder for summaries {target_dir}: {e}")
        QMessageBox.critical(None, "Startup Error", f"Error reading character folder:\n{target_dir}\n\n{e}")
        CHARACTER_SUMMARY_DATA = [] # Ensure list is empty on error

# Keep get_config_value_flexible
def get_config_value_flexible(config_map, key):
    if not isinstance(key, str) or not isinstance(config_map, dict): return None
    value = config_map.get(key);
    if value is not None: return value
    key_sanitized_common = key.replace(' ', '_').replace('&', 'and')
    value = config_map.get(key_sanitized_common);
    if value is not None: return value
    key_sanitized_space = key.replace(' ', '_')
    if key_sanitized_space != key and key_sanitized_space != key_sanitized_common:
        value = config_map.get(key_sanitized_space);
        if value is not None: return value
    key_sanitized_amp = key.replace('&', 'and')
    if key_sanitized_amp != key and key_sanitized_amp != key_sanitized_common:
        value = config_map.get(key_sanitized_amp);
        if value is not None: return value
    key_lower = key.lower(); key_sanitized_common_lower = key_sanitized_common.lower()
    key_sanitized_space_lower = key_sanitized_space.lower(); key_sanitized_amp_lower = key_sanitized_amp.lower()
    for config_key, config_value in config_map.items():
        if not isinstance(config_key, str): continue
        config_key_lower = config_key.lower()
        if config_key_lower == key_lower: return config_value
        if config_key_lower == key_sanitized_common_lower: return config_value
        if config_key_lower == key_sanitized_space_lower: return config_value
        if config_key_lower == key_sanitized_amp_lower: return config_value
    if DEBUG_MODE and key: print(f"WARN: Config lookup failed for key '{key}' after checking multiple variations.")
    return None

# Keep load_favorites, save_favorites, get_stylesheet
def load_favorites(filename=FAVORITES_FILE):
    if not os.path.exists(filename): return set()
    try:
        with open(filename, 'r', encoding='utf-8') as f: data = json.load(f)
        if isinstance(data, dict) and "favorites" in data and isinstance(data["favorites"], list):
            return set(item for item in data["favorites"] if isinstance(item, str))
        else: print(f"Warning: Favorites file '{filename}' has incorrect format."); return set()
    except json.JSONDecodeError as e: print(f"Warning: Invalid JSON in favorites file '{filename}'. Error: {e}"); return set()
    except Exception as e: print(f"Warning: Could not load favorites '{filename}'. Error: {e}"); return set()

def save_favorites(favorites_set, filename=FAVORITES_FILE):
    try:
        fav_dir = os.path.dirname(filename)
        if fav_dir and not os.path.exists(fav_dir):
            try: os.makedirs(fav_dir); print(f"Created directory for favorites: {fav_dir}")
            except OSError as e: print(f"Error creating directory for favorites '{fav_dir}'. Error: {e}"); return
        favorites_list = sorted(list(favorites_set))
        with open(filename, 'w', encoding='utf-8') as f: json.dump({"favorites": favorites_list}, f, indent=2)
    except Exception as e: print(f"Error saving favorites to '{filename}'. Error: {e}")

def get_stylesheet():
    qss_path = os.path.join(STYLES_FOLDER, 'dark_theme.qss'); stylesheet = ""
    try:
        with open(qss_path, 'r', encoding='utf-8') as f: stylesheet = f.read()
    except FileNotFoundError: print(f"ERROR: Stylesheet file not found: {qss_path}"); QMessageBox.warning(None, "Style Error", f"Stylesheet file missing:\n{qss_path}")
    except Exception as e: print(f"ERROR: Failed to load stylesheet: {qss_path} - {e}"); QMessageBox.warning(None, "Style Error", f"Failed to load stylesheet:\n{qss_path}\n\n{e}")
    return stylesheet

# Keep _format_info_text
# --- Helper Function for Info Popups (Corrected Logic) ---
def _format_info_text(raw_text):
    """Converts simple markdown-like syntax in info files to HTML, making URLs clickable."""
    if not raw_text:
        return ""

    html_lines = []
    in_list = False  # Initialize list state tracker

    # Regex to find URLs (handles http, https, www.)
    url_pattern = re.compile(r'(\b(?:https?://|www\.)[^\s<>()"\']+)', re.IGNORECASE)

    # Inner function to create clickable links
    def make_links_clickable(line):
        def replace_url(match):
            url = match.group(1)
            display_url = url.replace('&', '&').replace('<', '<').replace('>', '>') # More robust escaping for display
            href = url if url.startswith(('http://', 'https://')) else 'http://' + url
            link_style = "color:#77C4FF; text-decoration: underline;"
            return f'<a href="{href}" style="{link_style}">{display_url}</a>'
        # Escape the line first, then make links
        line_escaped = line.replace('&', '&').replace('<', '<').replace('>', '>')
        return url_pattern.sub(replace_url, line_escaped)

    # Process lines
    for line in raw_text.splitlines():
        line = line.strip() # Strip leading/trailing whitespace

        # --- Logic Restructured ---
        # 1. Check if the current line type means we should close an existing list
        #    (i.e., we were in a list, but this line is not a list item or is empty)
        should_close_list = in_list and not line.startswith("* ")

        if should_close_list:
            html_lines.append("</ul>")
            in_list = False # Update state: no longer in list

        # 2. Process the actual content of the line
        if not line:
            # Empty line - list closing handled above, just skip
            continue

        elif line.startswith("### "):
            content = line[4:].strip()
            content_linked = make_links_clickable(content) # Make links within the content
            html_lines.append(f"<h3 style='color:{H3_COLOR}; margin-top: 8px; margin-bottom: 4px;'>{content_linked}</h3>")
        elif line.startswith("## "):
            content = line[3:].strip()
            content_linked = make_links_clickable(content)
            html_lines.append(f"<h2 style='color:{H2_COLOR}; margin-top: 10px; margin-bottom: 5px;'>{content_linked}</h2>")
        elif line.startswith("> "):
            content = line[2:].strip()
            content_linked = make_links_clickable(content)
            quote_style_inline = f"font-style: italic; color: {LORE_COLOR}; border-left: 3px solid {LORE_COLOR}; padding-left: 10px; margin-top: 4px; margin-bottom: 4px; display: block; background-color: #333;"
            html_lines.append(f"<blockquote style='{quote_style_inline}'>{content_linked}</blockquote>")
        elif line.startswith("* "):
            content = line[2:].strip()
            # Check if we need to OPEN a list
            if not in_list:
                html_lines.append(f"<ul style='{LIST_STYLE}'>")
                in_list = True # Update state: now in list
            content_linked = make_links_clickable(content)
            html_lines.append(f"<li>{content_linked}</li>")
        else: # Plain text line
            # Basic inline markdown (**bold**, __underline__) - apply *before* link detection/escaping
            formatted_line = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", line) # Use original line here
            formatted_line = re.sub(r"__(.*?)__", r"<u>\1</u>", formatted_line)
            # Now escape potential HTML and make URLs clickable in the potentially bolded/underlined text
            formatted_line_linked = make_links_clickable(formatted_line)
            html_lines.append(f"<p>{formatted_line_linked}</p>")

    # --- Final Check ---
    # If the loop finished while still inside a list, close it
    if in_list:
        html_lines.append("</ul>")

    # Wrap the whole content in a body tag with default font styles
    final_html = f"<body style='font-family: \"{CURRENT_FONT_FAMILY_NAME}\", sans-serif; font-size: {BASE_FONT_SIZE}pt; color: #E0E0E0;'>"
    final_html += "".join(html_lines)
    final_html += "</body>"
    return final_html
# Keep InfoPopupDialog (Unchanged)
class InfoPopupDialog(QDialog):
    def __init__(self, title, html_content, parent=None):
        super().__init__(parent); self.setObjectName("InfoPopupDialog")
        try:
            icon_filename = "Marvel Rivals Dashboard.ico"; icon_path = resource_path(os.path.join('images', icon_filename))
            if os.path.exists(icon_path): self.setWindowIcon(QIcon(icon_path))
        except Exception as e: print(f"ERROR setting dialog icon: {e}")
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.WindowTitleHint | Qt.WindowType.WindowCloseButtonHint | Qt.WindowType.WindowSystemMenuHint)
        self.setWindowTitle(title); self.setModal(True); self.layout = QVBoxLayout(self); self.layout.setContentsMargins(10, 10, 10, 10); self.layout.setSpacing(8)
        self.scroll_area = QScrollArea(self); self.scroll_area.setWidgetResizable(True); self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll_area.setObjectName("PopupScrollArea"); self.scroll_area.setFrameShape(QFrame.Shape.StyledPanel)
        self.content_widget = ZoomableTextWidget(html_content, base_font_size_pt=BASE_FONT_SIZE, parent=self.scroll_area)
        self.scroll_area.setWidget(self.content_widget); self.layout.addWidget(self.scroll_area, 1)
        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close); self.button_box.rejected.connect(self.reject)
        self.layout.addWidget(self.button_box); self.setMinimumSize(600, 400); self.resize(750, 600)

# Keep ZoomableTextWidget (Unchanged)
class ZoomableTextWidget(QTextBrowser):
    # ... (Keep the existing ZoomableTextWidget code exactly as it was) ...
    def __init__(self, initial_html="", base_font_size_pt=BASE_FONT_SIZE, parent=None):
        super().__init__(parent)
        self._base_font_size_pt = base_font_size_pt
        self._current_font_size_pt = base_font_size_pt
        self._font_family_name = CURRENT_FONT_FAMILY_NAME
        self._raw_html_content = ""
        self.setReadOnly(True); self.setOpenExternalLinks(True); self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff); self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setObjectName("ZoomableTextWidget"); self.document().contentsChanged.connect(self.adjust_height)
        self._original_resizeEvent = self.resizeEvent; self.resizeEvent = self._custom_resizeEvent; self._update_font()
        size_policy = self.sizePolicy(); size_policy.setVerticalPolicy(QSizePolicy.Policy.Preferred); size_policy.setHorizontalPolicy(QSizePolicy.Policy.Expanding); self.setSizePolicy(size_policy)
        self.setHtmlWithBaseSize(initial_html)

    def _custom_resizeEvent(self, event): self._original_resizeEvent(event); QTimer.singleShot(0, self.adjust_height)
    def _update_font(self): font = self.font(); font.setFamily(self._font_family_name); font.setPointSize(self._current_font_size_pt); self.setFont(font); QTimer.singleShot(0, self.adjust_height)
    def setHtmlWithBaseSize(self, html_text):
        self._raw_html_content = html_text; self.document().blockSignals(True)
        quoted_font_family = f'"{self._font_family_name}"' if ' ' in self._font_family_name else self._font_family_name
        styled_html = f"""<body style='font-family: {quoted_font_family}, sans-serif; font-size: {self._current_font_size_pt}pt; color: #E0E0E0;'>{html_text}</body>"""
        super().setHtml(styled_html); self.document().blockSignals(False); QTimer.singleShot(0, self.adjust_height)
    def _reset_zoom(self):
        if abs(self._current_font_size_pt - self._base_font_size_pt) < 0.1: return False
        if DEBUG_MODE: print(f"DEBUG ResetZoom: Resetting from {self._current_font_size_pt:.1f} to {self._base_font_size_pt:.1f}")
        cursor = self.textCursor(); position_in_document = cursor.position(); h_scrollbar = self.horizontalScrollBar()
        h_max = h_scrollbar.maximum(); h_scroll_ratio = (h_scrollbar.value() / h_max) if h_max > 0 else 0.0
        self._current_font_size_pt = self._base_font_size_pt
        if hasattr(self, '_raw_html_content'):
            self.setHtmlWithBaseSize(self._raw_html_content)
            QTimer.singleShot(0, lambda pos=position_in_document, ratio=h_scroll_ratio: self._restore_view_state(pos, ratio)); return True
        else: print("WARN ResetZoom: _raw_html_content not found."); return False
    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.MiddleButton:
            if self._reset_zoom(): event.accept(); return
        super().mousePressEvent(event)
    def keyPressEvent(self, event: QKeyEvent):
        if event.modifiers() == Qt.KeyboardModifier.ControlModifier and event.key() == Qt.Key.Key_R:
            if self._reset_zoom(): event.accept(); return
        super().keyPressEvent(event)
    def wheelEvent(self, event: QWheelEvent):
        if event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            delta = event.angleDelta().y(); zoom_factor = 1.1 if delta > 0 else 1 / 1.1
            new_font_size = max(6.0, min(72.0, self._current_font_size_pt * zoom_factor))
            if abs(new_font_size - self._current_font_size_pt) > 0.1:
                if DEBUG_MODE: print(f"DEBUG Zoom: Ctrl+Scroll. OldSize: {self._current_font_size_pt:.1f}, NewSize: {new_font_size:.1f}")
                cursor = self.textCursor(); position_in_document = cursor.position(); h_scrollbar = self.horizontalScrollBar()
                h_max = h_scrollbar.maximum(); h_scroll_ratio = (h_scrollbar.value() / h_max) if h_max > 0 else 0.0
                self._current_font_size_pt = new_font_size
                if hasattr(self, '_raw_html_content'):
                    self.setHtmlWithBaseSize(self._raw_html_content)
                    QTimer.singleShot(0, lambda pos=position_in_document, ratio=h_scroll_ratio: self._restore_view_state(pos, ratio))
                else: print("WARN Zoom: _raw_html_content not found."); self._update_font()
            event.accept()
        else: super().wheelEvent(event)
    def _restore_view_state(self, position_in_document, h_scroll_ratio):
        action_type = "Zoom/Reset"
        if DEBUG_MODE: print(f"DEBUG {action_type} Restore: Pos:{position_in_document}, HScrollRatio:{h_scroll_ratio:.3f}")
        try:
            if not self or not QApplication.instance(): return
            h_scrollbar = self.horizontalScrollBar()
            if h_scrollbar:
                h_min = h_scrollbar.minimum(); h_max = h_scrollbar.maximum()
                new_h_value = int(h_scroll_ratio * (h_max - h_min) + h_min) if h_max > h_min else h_min
                if h_max > h_min: h_scrollbar.setValue(new_h_value)
            cursor = self.textCursor(); doc_length = self.document().characterCount() - 1
            safe_position = max(0, min(position_in_document, doc_length))
            cursor.setPosition(safe_position); self.setTextCursor(cursor); self.ensureCursorVisible()
        except RuntimeError as e:
            if 'Internal C++ object' in str(e) and 'already deleted' in str(e): print(f"WARN {action_type} Restore: Widget deleted: {e}")
            else: print(f"ERROR {action_type} Restore: Unexpected RuntimeError: {e}"); raise
        except Exception as e: print(f"ERROR during {action_type} view state restore: {e}"); import traceback; traceback.print_exc()
    @Slot()
    def adjust_height(self):
        calculated_height = self.document().size().height(); margins = self.contentsMargins(); padding = 4 * 2; border = 1 * 2
        new_exact_height = int(calculated_height + margins.top() + margins.bottom() + padding + border)
        current_min_height = self.minimumHeight(); current_max_height = self.maximumHeight()
        if abs(current_min_height - new_exact_height) > 1 or abs(current_max_height - new_exact_height) > 1:
            if DEBUG_MODE: print(f"DEBUG AdjustHeight: '{self.objectName()}' changing height to {new_exact_height}")
            self.setMinimumHeight(new_exact_height); self.setMaximumHeight(new_exact_height)
            parent = self.parentWidget()
            if parent: parent.updateGeometry();
            if parent and parent.layout(): parent.layout().activate()


# Keep ClickableLabel (Unchanged)
class ClickableLabel(QLabel):
    clicked = Signal(str)
    def __init__(self, tooltip_text="", parent=None):
        super().__init__("", parent); self.setObjectName("JumpBarLabel"); self.setToolTip(tooltip_text); self.setAlignment(Qt.AlignmentFlag.AlignCenter)
    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            if DEBUG_MODE: print(f"DEBUG ClickEvent: '{self.toolTip()}' label pressed. Emitting signal.")
            self.clicked.emit(self.toolTip())
        super().mousePressEvent(event)

# Keep CollapsibleGroupBox (Unchanged)
class CollapsibleGroupBox(QGroupBox):
    # ... (Keep the existing CollapsibleGroupBox code exactly as it was) ...
    def __init__(self, title="", parent=None, initially_collapsed=False):
        super().__init__(title, parent); self._is_collapsed = initially_collapsed; self._content_widgets = []
        self.toggle_button = QPushButton(self); self.toggle_button.setObjectName("CollapseButton"); self.toggle_button.setCheckable(True)
        self.toggle_button.setChecked(not self._is_collapsed); self.toggle_button.setText(self._get_arrow_char()); self.toggle_button.setToolTip("Expand/Collapse Section")
        self.toggle_button.clicked.connect(self._toggle_button_clicked); self.setProperty("collapsed", self._is_collapsed); self.setProperty("hasToggleButton", True)
        layout = self.layout(); self._original_content_margins = (9, 9, 9, 9) # Default
        if layout: lm, tm, rm, bm = layout.getContentsMargins(); self._original_content_margins = (lm, tm, rm, bm)
        QTimer.singleShot(0, self._apply_initial_state)
    def _apply_initial_state(self):
        if not self.layout(): layout = QVBoxLayout(); self.setLayout(layout); lm, tm, rm, bm = layout.contentsMargins(); self._original_content_margins = (lm, tm, rm, bm)
        self._collect_content_widgets(); self._update_visibility_and_layout(self._is_collapsed)
    def _collect_content_widgets(self):
        self._content_widgets.clear(); layout = self.layout()
        if layout:
            for i in range(layout.count()):
                item = layout.itemAt(i); widget = item.widget()
                if widget and widget != self.toggle_button: self._content_widgets.append(widget)
    def _get_arrow_char(self): return "▶" if self._is_collapsed else "▼"
    def _update_visibility_and_layout(self, is_collapsed):
        if not self._content_widgets: self._collect_content_widgets()
        visible = not is_collapsed; layout = self.layout()
        for widget in self._content_widgets: widget.setVisible(visible)
        if layout:
            lm, tm, rm, bm = self._original_content_margins
            if is_collapsed: layout.setContentsMargins(lm, 2, rm, 2)
            else: layout.setContentsMargins(lm, tm, rm, bm)
        sp = self.sizePolicy()
        if is_collapsed: sp.setVerticalPolicy(QSizePolicy.Policy.Fixed); self.setMaximumHeight(self.minimumSizeHint().height())
        else: sp.setVerticalPolicy(QSizePolicy.Policy.Preferred); self.setMaximumHeight(16777215)
        self.setSizePolicy(sp); self.updateGeometry()
        parent_layout = self.parentWidget().layout() if self.parentWidget() else None
        if parent_layout: parent_layout.activate()
        self.setProperty("collapsed", is_collapsed); self.style().unpolish(self); self.style().polish(self)
    @Slot(bool)
    def _toggle_button_clicked(self, checked):
        new_collapsed_state = not checked
        if new_collapsed_state != self._is_collapsed:
            self._is_collapsed = new_collapsed_state; self.toggle_button.setText(self._get_arrow_char()); self._update_visibility_and_layout(self._is_collapsed)
    def paintEvent(self, event):
        super().paintEvent(event); option = QStyleOptionGroupBox(); self.initStyleOption(option)
        title_rect = self.style().subControlRect(QStyle.ComplexControl.CC_GroupBox, option, QStyle.SubControl.SC_GroupBoxLabel, self)
        btn_x = title_rect.x() - self.toggle_button.width() - 3; btn_x = max(5, btn_x)
        btn_y = title_rect.y() + (title_rect.height() - self.toggle_button.height()) // 2
        self.toggle_button.move(btn_x, btn_y); self.toggle_button.raise_()
    def minimumSizeHint(self):
        if self._is_collapsed:
            option = QStyleOptionGroupBox(); self.initStyleOption(option)
            title_rect = self.style().subControlRect(QStyle.ComplexControl.CC_GroupBox, option, QStyle.SubControl.SC_GroupBoxLabel, self)
            frame_margin_approx = self.style().pixelMetric(QStyle.PixelMetric.PM_LayoutVerticalSpacing, option, self) * 2
            lm, tm, rm, bm = self.layout().getContentsMargins() if self.layout() else self._original_content_margins
            collapsed_height = title_rect.height() + tm + bm + frame_margin_approx + 4
            return QSize(150, collapsed_height)
        else: return super().minimumSizeHint()
    def sizeHint(self): return self.minimumSizeHint() if self._is_collapsed else super().sizeHint()


# --- Character Card Widget ---
# --- Character Card Widget (Reverted to Full Pre-load) ---
class CharacterCard(QWidget):
    favorite_toggled = Signal(str, bool)
    # --- REMOVED request_full_load signal ---

    # --- REVERTED __init__ signature ---
    def __init__(self, character_name, character_data, is_favorite):
        super().__init__()
        # --- REMOVED main_window_ref ---
        self.character_name = character_name
        # --- Store full data directly ---
        self.character_data = character_data if isinstance(character_data, dict) else {}
        self._is_favorite = is_favorite
        self.font_family = CURRENT_FONT_FAMILY_NAME
        self.using_custom_font = CUSTOM_FONT_LOADED

        # --- REMOVED load state flags ---
        # self._full_data_loaded = False ... etc.

        # --- Theme colors - Set based on provided data ---
        self._update_theme_colors() # Update colors right away

        self.setObjectName("CharacterCard")
        self.setProperty("cardBorderColor", self.primary_theme_color_str)

        # --- Build FULL UI immediately ---
        self.init_ui() # <<< Call original full UI build method

        # --- Set Preferred policy from start ---
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)


    # --- NEW: Update theme colors (called from __init__) ---
    def _update_theme_colors(self):
        """Updates theme colors based on loaded character_data."""
        # Default values
        self.primary_theme_color_str = DEFAULT_THEME_COLOR
        self.primary_theme_color = QColor(DEFAULT_THEME_COLOR)
        self.secondary_theme_color_str = DEFAULT_SECONDARY_THEME_COLOR
        self.secondary_theme_color = QColor(DEFAULT_SECONDARY_THEME_COLOR)

        # Try to get from data
        stats_data = self.character_data.get("stats", {})
        if not isinstance(stats_data, dict): stats_data = {}

        raw_primary_color = stats_data.get("color_theme")
        raw_secondary_color = stats_data.get("color_theme_secondary")

        # --- Corrected Primary Color Block ---
        if raw_primary_color and isinstance(raw_primary_color, str):
            try:
                test_color = QColor(raw_primary_color)
                # This 'if' and assignment should be inside the 'try'
                if test_color.isValid():
                    self.primary_theme_color_str = raw_primary_color
                    self.primary_theme_color = test_color
            except Exception:
                # Ignore errors, keep default
                pass

        # --- Corrected Secondary Color Block ---
        if raw_secondary_color and isinstance(raw_secondary_color, str):
            try:
                test_color = QColor(raw_secondary_color)
                # This 'if' and assignment should be inside the 'try'
                if test_color.isValid():
                    self.secondary_theme_color_str = raw_secondary_color
                    self.secondary_theme_color = test_color
            except Exception:
                # Ignore errors, keep default
                pass

        # Note: Stylesheet using these colors will be applied in init_ui

    # --- REVERTED init_ui (Builds Everything) ---
    def init_ui(self):
        self.main_layout = QVBoxLayout(self); self.main_layout.setSpacing(12)
        # Apply styling using the already set theme colors
        self.setStyleSheet(f""" CharacterCard {{ border: 2px solid {self.primary_theme_color_str}; border-radius: 8px; padding: 10px; background-color: #282828; }} """)

        # --- Header (Builds using self.character_data) ---
        header_widget = QWidget(); header_layout = QGridLayout(header_widget); header_layout.setSpacing(10); header_layout.setContentsMargins(0, 0, 0, 5); header_layout.setColumnStretch(1, 1)
        # Image Label
        img_label = QLabel(); img_label.setObjectName("CharacterImageLabel"); img_label.setAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignTop)
        # Look up image file using name and map
        img_filename = get_config_value_flexible(CHARACTER_IMAGE_MAP, self.character_name) # <<< Use lookup
        img_full_path = os.path.join(IMAGE_FOLDER, img_filename) if img_filename else None; img_found = False; max_height = 180
        if img_full_path and os.path.exists(img_full_path):
            full_pixmap = QPixmap(img_full_path)
            if not full_pixmap.isNull():
                full_width = full_pixmap.width(); full_height = full_pixmap.height(); target_crop_width = min(full_width, int(full_width * 0.60)); target_crop_width = max(1, target_crop_width); crop_x = max(0, (full_width - target_crop_width) // 2); crop_y = 0; crop_rect = QRect(crop_x, crop_y, target_crop_width, full_height); cropped_pixmap = full_pixmap.copy(crop_rect)
                if not cropped_pixmap.isNull(): display_pixmap = cropped_pixmap.scaled(QSize(target_crop_width * 2, max_height), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation); img_label.setPixmap(display_pixmap); img_found = True
                else: display_pixmap = full_pixmap.scaled(QSize(500, max_height), Qt.KeepAspectRatio, Qt.SmoothTransformation); img_label.setPixmap(display_pixmap); img_found = True
        if not img_found: img_label.setText(f"Image Missing:\n{img_filename or 'Not Mapped'}"); img_label.setObjectName("ImageNotFoundLabel"); img_label.setStyleSheet(f"color: {DETAILS_COLOR}; font-style: italic;"); img_label.setMinimumHeight(int(max_height * 0.8)); img_label.setMaximumHeight(max_height)
        img_label.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed); img_label.setFixedHeight(max_height); header_layout.addWidget(img_label, 0, 0, 2, 1, Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
        # Name and Stats
        name_stats_vbox = QVBoxLayout(); name_stats_vbox.setSpacing(3); name_stats_vbox.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.name_label = QLabel(self.character_name); self.name_label.setObjectName("CharacterNameLabel"); name_font = QFont(self.font_family, CHARACTER_NAME_FONT_SIZE); name_font.setWeight(QFont.Weight.Black); self.name_label.setFont(name_font); self.name_label.setStyleSheet(f"color: {self.primary_theme_color_str};") # Use updated color
        name_stats_vbox.addWidget(self.name_label)
        # Add Role, Health, Difficulty, Tier from self.character_data
        stats_layout = QVBoxLayout(); stats_layout.setSpacing(1); stats_layout.setContentsMargins(5, 0, 0, 0)
        role = self.character_data.get('role'); stat_font = QFont(self.font_family, HEADER_FONT_SIZE)
        if role: role_label = QLabel(f"<span style='{FIELD_LABEL_STYLE}'>Role:</span> <span style='{FIELD_VALUE_STYLE}'>{role}</span>"); role_label.setObjectName("RoleLabel"); role_label.setFont(stat_font); role_label.setTextFormat(Qt.TextFormat.RichText); stats_layout.addWidget(role_label)
        meta_stats_data = self.character_data.get("meta_stats", {}); tier = meta_stats_data.get('tier') if isinstance(meta_stats_data, dict) else None
        if tier and str(tier).strip(): tier_label = QLabel(f"<span style='{FIELD_LABEL_STYLE}'>Tier:</span> <span style='{FIELD_VALUE_STYLE}'>{tier}</span>"); tier_label.setObjectName("StatLabel"); tier_label.setFont(stat_font); tier_label.setTextFormat(Qt.TextFormat.RichText); stats_layout.addWidget(tier_label)
        stats_data = self.character_data.get("stats", {});
        if isinstance(stats_data, dict):
            health = stats_data.get('health'); difficulty = stats_data.get('difficulty')
            if health is not None: health_label = QLabel(f"<span style='{FIELD_LABEL_STYLE}'>Health:</span> <span style='{FIELD_VALUE_STYLE}'>{health}</span>"); health_label.setObjectName("StatLabel"); health_label.setFont(stat_font); health_label.setTextFormat(Qt.TextFormat.RichText); stats_layout.addWidget(health_label)
            if difficulty: difficulty_label = QLabel(f"<span style='{FIELD_LABEL_STYLE}'>Difficulty:</span> <span style='{FIELD_VALUE_STYLE}'>{difficulty}</span>"); difficulty_label.setObjectName("StatLabel"); difficulty_label.setFont(stat_font); difficulty_label.setTextFormat(Qt.TextFormat.RichText); stats_layout.addWidget(difficulty_label)
        name_stats_vbox.addLayout(stats_layout); name_stats_vbox.addStretch(1); header_layout.addLayout(name_stats_vbox, 0, 1, 2, 1, Qt.AlignmentFlag.AlignTop)
        # Buttons
        buttons_vbox = QVBoxLayout(); buttons_vbox.setSpacing(5); buttons_vbox.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight)
        self.fav_button = QPushButton(); self.fav_button.setObjectName("FavoriteButton"); self.fav_button.setCheckable(True); self.fav_button.setFixedSize(QSize(30, 30)); self.fav_button.setToolTip("Toggle Favorite"); self.fav_button.clicked.connect(self.toggle_favorite_button); self.update_favorite_button_style() # Uses self._is_favorite
        buttons_vbox.addWidget(self.fav_button)
        self.youtube_button = QPushButton("Video Guides"); self.youtube_button.setObjectName("LinkButton"); youtube_button_font = QFont(self.font_family, BASE_FONT_SIZE - 1); self.youtube_button.setFont(youtube_button_font); self.youtube_button.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed); self.youtube_button.setFixedHeight(25); self.youtube_button.setToolTip(f"Search YouTube for {SEARCH_SEASON_STRING} guides"); self.youtube_button.clicked.connect(self._open_youtube_search)
        buttons_vbox.addWidget(self.youtube_button); buttons_vbox.addStretch(1); header_layout.addLayout(buttons_vbox, 0, 2, 2, 1, Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight)
        # Add Header
        self.main_layout.addWidget(header_widget)
        # --- End Header ---

        # --- Sections (Build all sections immediately) ---
        # Abilities
        abilities_list = self.character_data.get('abilities', [])
        if abilities_list and isinstance(abilities_list, list):
            ability_group, ability_layout = self._create_section_group("Abilities") # Removed content_added_flag init here
            content_added_flag = False  # Initialize flag correctly
            for ability in abilities_list:
                widget = self._create_zoomable_widget(self._format_ability_html(ability))
                # CORRECTED: This line is now INSIDE the loop
                if self._add_widget_if_data(ability_layout, widget):
                    content_added_flag = True # Set flag if ANY widget is added
            
            if content_added_flag: # If at least one ability widget was added
                ability_layout.addStretch(1)
                self.main_layout.addWidget(ability_group)
            else: # No ability widgets were added
                ability_group.deleteLater()
        # Ultimate
        ultimate_data = self.character_data.get('ultimate')
        if ultimate_data and isinstance(ultimate_data, dict):
            ultimate_group, ultimate_layout = self._create_section_group("Ultimate"); widget = self._create_zoomable_widget(self._format_ultimate_html(ultimate_data))
            if self._add_widget_if_data(ultimate_layout, widget): ultimate_layout.addStretch(1); self.main_layout.addWidget(ultimate_group)
            else: ultimate_group.deleteLater()
        # Passives / Melee
        passives_list = self.character_data.get('passives', [])
        if passives_list and isinstance(passives_list, list):
            passive_group, passive_layout = self._create_section_group("Passives / Melee"); content_added_flag = False
            for passive in passives_list: widget = self._create_zoomable_widget(self._format_passive_html(passive));
            if self._add_widget_if_data(passive_layout, widget): content_added_flag = True
            if content_added_flag: passive_layout.addStretch(1); self.main_layout.addWidget(passive_group)
            else: passive_group.deleteLater()
        # Teamups
        teamups_list = self.character_data.get('teamups', [])
        if teamups_list and isinstance(teamups_list, list):
            teamup_group, teamup_layout = self._create_section_group("Teamups"); content_added = False
            for teamup_entry in teamups_list:
                formatted_html = self._format_teamup_html(teamup_entry)
                if formatted_html: widget = self._create_zoomable_widget(formatted_html);
                if self._add_widget_if_data(teamup_layout, widget): content_added = True
            if content_added: teamup_layout.addStretch(1); self.main_layout.addWidget(teamup_group)
            else: teamup_group.deleteLater()
        # Gameplay Strategy (Includes health/diff/tier which are already shown in header, maybe remove duplicates?)
        gameplay_data = self.character_data.get('gameplay'); has_gameplay_content = isinstance(gameplay_data, dict) and any(gameplay_data.values())
        # Only create if there's actual gameplay data beyond stats already in header
        if has_gameplay_content:
            gameplay_group, gameplay_layout = self._create_section_group("Gameplay Strategy", collapsible=True, initially_collapsed=True); content_added_flag = False
            overview = gameplay_data.get('strategy_overview');
            if overview: widget = self._create_zoomable_widget(f"<p>{overview}</p>"); content_added_flag = self._add_widget_if_data(gameplay_layout, widget) or content_added_flag
            weaknesses = gameplay_data.get('weaknesses', []); content_added_flag = self._add_list_as_bullets(gameplay_layout, "Weaknesses", weaknesses) or content_added_flag
            achievements = gameplay_data.get('achievements', [])
            if achievements and isinstance(achievements, list):
                 ach_html_parts = [html for ach in achievements if (html := self._format_achievement_html(ach))]
                 if ach_html_parts:
                      ach_title_label = QLabel(f"<span style='{SECTION_TITLE_STYLE_TEMPLATE.format(color=self.secondary_theme_color_str)}'>Achievements</span>"); ach_title_label.setFont(QFont(self.font_family, BASE_FONT_SIZE)); ach_title_label.setTextFormat(Qt.TextFormat.RichText); gameplay_layout.addWidget(ach_title_label)
                      widget = self._create_zoomable_widget("".join(ach_html_parts)); content_added_flag = self._add_widget_if_data(gameplay_layout, widget) or content_added_flag
            if content_added_flag: gameplay_layout.addStretch(1); self.main_layout.addWidget(gameplay_group)
            else: gameplay_group.deleteLater()
        # Balance History
        lore_data_for_balance = self.character_data.get('lore_details', {})
        balance_changes_original = lore_data_for_balance.get('balance_changes', []) if isinstance(lore_data_for_balance, dict) else []
        
        if balance_changes_original and isinstance(balance_changes_original, list):
             # --- MODIFICATION: Reverse the list for display ---
             balance_changes_reversed = list(reversed(balance_changes_original))
             # --- END MODIFICATION ---

             change_html_parts = [html for change in balance_changes_reversed if (html := self._format_balance_change_html(change))] # Use the reversed list
             if change_html_parts:
                 balance_group, balance_layout = self._create_section_group("Balance History", collapsible=True, initially_collapsed=True)
                 widget = self._create_zoomable_widget("".join(change_html_parts))
                 if self._add_widget_if_data(balance_layout, widget):
                     balance_layout.addStretch(1)
                     self.main_layout.addWidget(balance_group)
                 else:
                     balance_group.deleteLater() # Clean up if no content was actually added
        # Lore & History
        lore_data = self.character_data.get('lore_details')
        if isinstance(lore_data, dict):
             has_other_lore = any(k != 'balance_changes' and v for k, v in lore_data.items())
             if has_other_lore:
                 lore_group, lore_layout = self._create_section_group("Lore & History", collapsible=True, initially_collapsed=True); content_added_flag = False
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
                 if content_added_flag: lore_layout.addStretch(1); self.main_layout.addWidget(lore_group)
                 else: lore_group.deleteLater()
        # Background (Comic Lore)
        background_data = self.character_data.get('background')
        if isinstance(background_data, dict) and any(background_data.values()):
            bg_group, bg_layout = self._create_section_group("Background (Comic Lore)", collapsible=True, initially_collapsed=True); content_added_flag = False
            content_added_flag = self._add_field_label(bg_layout, "Real Name", background_data.get("real_name")) or content_added_flag; content_added_flag = self._add_list_as_bullets(bg_layout, "Aliases", background_data.get("aliases", [])) or content_added_flag; content_added_flag = self._add_field_label(bg_layout, "Gender", background_data.get("gender")) or content_added_flag; content_added_flag = self._add_field_label(bg_layout, "Birthplace", background_data.get("birthplace")) or content_added_flag; affiliation_val = background_data.get("affiliation")
            if isinstance(affiliation_val, list): content_added_flag = self._add_list_as_bullets(bg_layout, "Affiliation", affiliation_val) or content_added_flag
            elif affiliation_val: content_added_flag = self._add_field_label(bg_layout, "Affiliation", affiliation_val) or content_added_flag
            content_added_flag = self._add_list_as_bullets(bg_layout, "Relatives", background_data.get("relatives", [])) or content_added_flag; content_added_flag = self._add_field_label(bg_layout, "First Appearance", background_data.get("first_appearance_comic")) or content_added_flag; content_added_flag = self._add_list_as_bullets(bg_layout, "Powers/Skills", background_data.get("lore_powers_skills", [])) or content_added_flag
            if content_added_flag: bg_layout.addStretch(1); self.main_layout.addWidget(bg_group)
            else: bg_group.deleteLater()
        # Meta Stats
        meta_stats_data = self.character_data.get('meta_stats', {}) # Already fetched for header
        has_meta_content = isinstance(meta_stats_data, dict) and any(v is not None and str(v).strip() for k, v in meta_stats_data.items() if k != 'tier') # Exclude tier
        if has_meta_content:
            meta_group, meta_layout = self._create_section_group("Meta Stats", collapsible=True, initially_collapsed=True); content_added_to_layout = False
            stats_order = [ ("win_rate", "Win Rate"), ("wr_change", "WR Change"), ("pick_rate", "Pick Rate"), ("pr_change", "PR Change"), ("ban_rate", "Ban Rate"), ("matches", "Matches")]; html_lines = []; processed_keys = set()
            for key, display_name in stats_order:
                processed_keys.add(key); value = meta_stats_data.get(key)
                if value is not None and str(value).strip(): line = f"<p><span style='{FIELD_LABEL_STYLE}'>{display_name}:</span> <span style='{FIELD_VALUE_STYLE}'>{value}</span></p>"; html_lines.append(line)
            other_keys = {k: v for k, v in meta_stats_data.items() if k not in processed_keys and k != 'tier'}
            for key, value in other_keys.items():
                 if value is not None and str(value).strip(): display_name = key.replace("_", " ").title(); line = f"<p><span style='{FIELD_LABEL_STYLE}'>{display_name}:</span> <span style='{FIELD_VALUE_STYLE}'>{value}</span></p>"; html_lines.append(line)
            if html_lines:
                full_html = "".join(html_lines); content_widget = self._create_zoomable_widget(full_html)
                if self._add_widget_if_data(meta_layout, content_widget): meta_layout.addStretch(1); self.main_layout.addWidget(meta_group); content_added_to_layout = True
            if not content_added_to_layout: meta_group.deleteLater()
        # Extras (Misc / Data Sources)
        misc_data = self.character_data.get('misc', {}); data_sources = self.character_data.get('data_sources', {}); has_buzz = isinstance(misc_data, dict) and misc_data.get('community_buzz'); has_helpful = isinstance(misc_data, dict) and misc_data.get('helpful_links'); has_sources = isinstance(data_sources, dict) and any(bool(v) for v in data_sources.values() if isinstance(v, list))
        if has_buzz or has_helpful or has_sources:
            extras_group, extras_layout = self._create_section_group("Extras", collapsible=True, initially_collapsed=True); content_added_to_layout = False
            if has_buzz:
                buzz_text_url = misc_data.get('community_buzz')
                if buzz_text_url and isinstance(buzz_text_url, str) and buzz_text_url.strip():
                    link_html = f"<a href='{buzz_text_url}' style='color:#77C4FF; text-decoration: none;'>{self.character_name} Reddit Link</a>"; buzz_title_label = QLabel(f"<span style='{FIELD_LABEL_STYLE}'>Community Buzz:</span>"); buzz_title_label.setFont(QFont(self.font_family, BASE_FONT_SIZE)); buzz_title_label.setTextFormat(Qt.TextFormat.RichText); extras_layout.addWidget(buzz_title_label); buzz_link_label = QLabel(link_html); buzz_link_label.setTextFormat(Qt.TextFormat.RichText); buzz_link_label.setOpenExternalLinks(True); buzz_link_label.setFont(QFont(self.font_family, BASE_FONT_SIZE)); buzz_link_label.setWordWrap(True); buzz_link_label.setStyleSheet("QLabel { margin-left: 10px; }"); extras_layout.addWidget(buzz_link_label); content_added_to_layout = True
            if has_helpful:
                helpful_links = misc_data.get('helpful_links', []); links_html_parts = []
                if helpful_links and isinstance(helpful_links, list):
                    for link_item in helpful_links:
                        if isinstance(link_item, dict): title = link_item.get('title'); url = link_item.get('url')
                        if title and url and str(title).strip() and str(url).strip(): link_text = f"<a href='{url}' style='color: #77C4FF; text-decoration: none;'>{title}</a>"; links_html_parts.append(f"<li>{link_text}</li>")
                if links_html_parts:
                    if content_added_to_layout: separator = QFrame(); separator.setFrameShape(QFrame.Shape.HLine); separator.setFrameShadow(QFrame.Shadow.Sunken); extras_layout.addWidget(separator)
                    links_title_label = QLabel(f"<span style='{FIELD_LABEL_STYLE}'>Helpful Links:</span>"); links_title_label.setFont(QFont(self.font_family, BASE_FONT_SIZE)); links_title_label.setTextFormat(Qt.TextFormat.RichText); extras_layout.addWidget(links_title_label); links_html = f"<ul style='{LIST_ITEM_STYLE} margin-top: 0px;'>{''.join(links_html_parts)}</ul>"; links_widget = self._create_zoomable_widget(links_html)
                    if self._add_widget_if_data(extras_layout, links_widget): content_added_to_layout = True
            if has_sources:
                source_html_lines = []; source_order = [ ("wiki", "Game Wiki"), ("tracker", "RivalsTracker"), ("comic_wiki", "Marvel Wiki (Fandom)")]; processed_keys = set()
                for key, display_name in source_order:
                    processed_keys.add(key); urls = data_sources.get(key)
                    if urls and isinstance(urls, list):
                        link_parts = [f'<a href="{url}" style="color:#77C4FF; text-decoration: none;">{url}</a>' for url in urls if url and isinstance(url, str) and url.strip()]
                        if link_parts: source_html_lines.append(f"<p style='margin-bottom: 3px;'><span style='{FIELD_LABEL_STYLE}'>{display_name}:</span><br/><span style='margin-left: 10px;'>" + "<br/>".join(link_parts) + "</span></p>")
                other_sources = {k: v for k, v in data_sources.items() if k not in processed_keys}
                for key, urls in other_sources.items():
                    if urls and isinstance(urls, list):
                        link_parts = [f'<a href="{url}" style="color:#77C4FF; text-decoration: none;">{url}</a>' for url in urls if url and isinstance(url, str) and url.strip()]
                        if link_parts: display_name = key.replace("_", " ").title(); source_html_lines.append(f"<p style='margin-bottom: 3px;'><span style='{FIELD_LABEL_STYLE}'>{display_name}:</span><br/><span style='margin-left: 10px;'>" + "<br/>".join(link_parts) + "</span></p>")
                if source_html_lines:
                    if content_added_to_layout: separator = QFrame(); separator.setFrameShape(QFrame.Shape.HLine); separator.setFrameShadow(QFrame.Shadow.Sunken); extras_layout.addWidget(separator)
                    full_source_html = "".join(source_html_lines); source_widget = self._create_zoomable_widget(full_source_html)
                    if self._add_widget_if_data(extras_layout, source_widget): content_added_to_layout = True
            if content_added_to_layout: extras_layout.addStretch(1); self.main_layout.addWidget(extras_group)
            else: extras_group.deleteLater()
        # --- End Sections ---

        # Final stretch for the main card layout
        self.main_layout.addStretch(1)


    # --- Helper/Formatting methods (Keep all _create*, _add*, _format*, _make_text_links*) ---
    # ... (Paste the unchanged helper/formatting methods here: _open_youtube_search, _create_zoomable_widget, ...)
    # ... (_add_widget_if_data, _add_field_label, _add_list_as_bullets, _create_section_group, ...)
    # ... (_format_ability_html, _format_ultimate_html, _format_passive_html, _format_teamup_html, ...)
    # ... (_format_achievement_html, _format_hero_story_html, _format_balance_change_html, _make_text_links_clickable)
    @Slot()
    def _open_youtube_search(self):
        try:
            search_season = SEARCH_SEASON_STRING; query_parts = [f'"{self.character_name}"', '"Marvel Rivals"', f'"{search_season}"']
            search_query = " ".join(query_parts); encoded_query = urllib.parse.quote_plus(search_query); base_url = "https://www.youtube.com/results"
            time_filter_param = "EgIIAw%253D%253D"; search_url = f"{base_url}?search_query={encoded_query}&sp={time_filter_param}"
            print(f"Constructed YouTube Search URL: {search_url}"); QDesktopServices.openUrl(QUrl(search_url))
        except Exception as e: print(f"Error constructing or opening YouTube URL: {e}"); QMessageBox.warning(self, "Search Error", f"Could not open YouTube search.\nError: {e}")
    def _create_zoomable_widget(self, html_content):
        has_real_content = bool(html_content and re.search(r"\S", re.sub('<[^>]*>', '', html_content)))
        return ZoomableTextWidget(html_content, base_font_size_pt=BASE_FONT_SIZE) if has_real_content else None
    def _add_widget_if_data(self, layout, widget):
        if widget:
            layout.addWidget(widget)
            return True
        return False # Or "else: return False"
    def _add_field_label(self, layout, label_text, value):
        if value is not None and str(value).strip():
            label = QLabel(f"<span style='{FIELD_LABEL_STYLE}'>{label_text}:</span> <span style='{FIELD_VALUE_STYLE}'>{value}</span>")
            label.setTextFormat(Qt.TextFormat.RichText); label.setWordWrap(True); label.setFont(QFont(self.font_family, BASE_FONT_SIZE)); layout.addWidget(label); return True
        return False
    def _add_list_as_bullets(self, layout, title, data_list, is_sub_list=False):
        valid_items = [item for item in data_list if item is not None and str(item).strip()] if isinstance(data_list, list) else []
        if valid_items:
            if not is_sub_list:
                 title_label = QLabel(f"<span style='{FIELD_LABEL_STYLE}'>{title}:</span>"); title_label.setFont(QFont(self.font_family, BASE_FONT_SIZE)); title_label.setTextFormat(Qt.TextFormat.RichText); layout.addWidget(title_label)
            html = f"<ul style='{LIST_ITEM_STYLE} margin-top: 0px;'>" + "".join(f"<li>{item}</li>" for item in valid_items) + "</ul>"; widget = self._create_zoomable_widget(html); return self._add_widget_if_data(layout, widget)
        return False
    def _create_section_group(self, title, collapsible=False, initially_collapsed=False):
        if collapsible: group = CollapsibleGroupBox(title, parent=self, initially_collapsed=initially_collapsed)
        else: group = QGroupBox(title, parent=self)
        title_font = QFont(self.font_family, GROUP_TITLE_FONT_SIZE); title_font.setWeight(QFont.Weight.Bold); group.setFont(title_font)
        group_class_name = group.__class__.__name__
        group.setStyleSheet(f"""{group_class_name} {{ margin-top: 8px; border: 1px solid {self.primary_theme_color.darker(120).name()}; padding-top: 15px; }} {group_class_name}::title {{ color: {self.primary_theme_color_str}; subcontrol-origin: margin; subcontrol-position: top left; padding: 0 5px 0 5px; margin-left: 5px; }}""")
        layout = QVBoxLayout(); layout.setSpacing(4); layout.setContentsMargins(6, 10, 6, 6); group.setLayout(layout); return group, layout
    def _format_ability_html(self, ability_dict):
        if not ability_dict or not isinstance(ability_dict, dict): return ""
        html = ""; name = ability_dict.get("name"); keybind = ability_dict.get("keybind"); title_str = name if name else "Unnamed Ability"
        if keybind: title_str += f" ({keybind})"
        html += f"<p><span style='{ABILITY_TITLE_STYLE_TEMPLATE.format(color=self.secondary_theme_color_str)}'>{title_str}</span></p>"; details_list = []
        fields_to_process = {"Type": ability_dict.get("type"),"Description": ability_dict.get("description"),"Casting": ability_dict.get("casting"),"Damage": ability_dict.get("damage"),"Damage Falloff": ability_dict.get("damage_falloff"),"Fire Rate/Interval": ability_dict.get("fire_rate_interval"),"Ammo": ability_dict.get("ammo"),"Critical Hit": ability_dict.get("critical_hit"),"Cooldown": ability_dict.get("cooldown"),"Range": ability_dict.get("range"),"Projectile Speed": ability_dict.get("projectile_speed"),"Charges": ability_dict.get("charges"),"Duration": ability_dict.get("duration"),"Movement Boost": ability_dict.get("movement_boost"),"Energy Cost": ability_dict.get("energy_cost_details"),"Details": ability_dict.get("details")}
        for label, value in fields_to_process.items():
            if value is not None and str(value).strip(): display_value = "Yes" if label == "Critical Hit" and isinstance(value, bool) else str(value).replace('\n', '<br>'); details_list.append(f"<span style='{FIELD_LABEL_STYLE}'>{label}:</span> <span style='{FIELD_VALUE_STYLE}'>{display_value}</span>")
        if details_list: html += "<p style='margin-left: 10px; margin-top: 2px;'>" + "<br/>".join(details_list) + "</p>"; return html if details_list else ""
    def _format_ultimate_html(self, ult_dict):
        if not ult_dict or not isinstance(ult_dict, dict): return ""
        html = ""; name = ult_dict.get("name"); keybind = ult_dict.get("keybind"); title_str = name if name else "Unnamed Ultimate"
        if keybind: title_str += f" ({keybind})"
        html += f"<p><span style='{ABILITY_TITLE_STYLE_TEMPLATE.format(color=self.secondary_theme_color_str)}'>{title_str}</span></p>"; details_list = []
        fields_to_process = {"Type": ult_dict.get("type"),"Description": ult_dict.get("description"),"Casting": ult_dict.get("casting"),"Damage": ult_dict.get("damage"),"Range": ult_dict.get("range"),"Effect": ult_dict.get("effect"),"Duration": ult_dict.get("duration"),"Health on Revive": ult_dict.get("health_upon_revival"),"Slow Rate": ult_dict.get("slow_rate"),"Projectile Speed": ult_dict.get("projectile_speed"),"Movement Boost": ult_dict.get("movement_boost"),"Bonus Health": ult_dict.get("bonus_health_details"),"Energy Cost": ult_dict.get("energy_cost"),"Details": ult_dict.get("details")}
        for label, value in fields_to_process.items():
             if value is not None and str(value).strip(): display_value = str(value).replace('\n', '<br>'); details_list.append(f"<span style='{FIELD_LABEL_STYLE}'>{label}:</span> <span style='{FIELD_VALUE_STYLE}'>{display_value}</span>")
        if details_list: html += "<p style='margin-left: 10px; margin-top: 2px;'>" + "<br/>".join(details_list) + "</p>"; return html if details_list else ""
    def _format_passive_html(self, passive_dict):
        if not passive_dict or not isinstance(passive_dict, dict): return ""
        html = ""; name = passive_dict.get("name"); keybind = passive_dict.get("keybind"); title_str = name if name else "Unnamed Passive/Melee"
        if keybind: title_str += f" ({keybind})"
        html += f"<p><span style='{ABILITY_TITLE_STYLE_TEMPLATE.format(color=self.secondary_theme_color_str)}'>{title_str}</span></p>"; details_list = []
        fields_to_process = {"Type": passive_dict.get("type"),"Description": passive_dict.get("description"),"Cooldown": passive_dict.get("cooldown"),"Damage": passive_dict.get("damage"),"Range": passive_dict.get("range"),"Trigger Condition": passive_dict.get("trigger_condition"),"Effect/Boost": passive_dict.get("effect_boost"),"Speed Details": passive_dict.get("speed_details"),"Details": passive_dict.get("details")}
        for label, value in fields_to_process.items():
            if value is not None and str(value).strip(): display_value = str(value).replace('\n', '<br>'); details_list.append(f"<span style='{FIELD_LABEL_STYLE}'>{label}:</span> <span style='{FIELD_VALUE_STYLE}'>{display_value}</span>")
        if details_list: html += "<p style='margin-left: 10px; margin-top: 2px;'>" + "<br/>".join(details_list) + "</p>"; return html if details_list else ""
    def _format_teamup_html(self, teamup_dict):
        if not teamup_dict or not isinstance(teamup_dict, dict): return ""
        html = ""; name = teamup_dict.get("name"); keybind = teamup_dict.get("keybind"); title_str = name if name else "Unnamed Team-Up"
        if keybind: title_str += f" ({keybind})"
        html += f"<p><span style='{ABILITY_TITLE_STYLE_TEMPLATE.format(color=self.secondary_theme_color_str)}'>{title_str}</span></p>"; details_list = []
        partner = teamup_dict.get("partner"); partner_str = "";
        if isinstance(partner, list): partner_str = ", ".join(p for p in partner if p)
        elif isinstance(partner, str) and partner: partner_str = partner
        if partner_str: details_list.append(f"<span style='{FIELD_LABEL_STYLE}'>Partner(s):</span> <span style='{FIELD_VALUE_STYLE}'>{partner_str}</span>")
        fields_to_process = {"Effect": teamup_dict.get("effect"),"Team-Up Bonus": teamup_dict.get("teamup_bonus"),"Duration": teamup_dict.get("duration"),"Cooldown": teamup_dict.get("cooldown"),"Range/Target": teamup_dict.get("range_target"),"Special Notes": teamup_dict.get("special_notes"),"Details": teamup_dict.get("details")}
        for label, value in fields_to_process.items():
            if value is not None and str(value).strip(): display_value = str(value).replace('\n', '<br>'); details_list.append(f"<span style='{FIELD_LABEL_STYLE}'>{label}:</span> <span style='{FIELD_VALUE_STYLE}'>{display_value}</span>")
        if details_list: html += "<p style='margin-left: 10px; margin-top: 2px;'>" + "<br/>".join(details_list) + "</p>"; return html if details_list else ""
    def _format_achievement_html(self, ach_dict):
         if not ach_dict or not isinstance(ach_dict, dict): return ""
         name = ach_dict.get("name"); desc = ach_dict.get("description"); points = ach_dict.get("points"); html = ""
         if not name and not desc: return ""
         if name: html += f"<p><span style='{FIELD_LABEL_STYLE}'>{name}</span>" + (f" ({points} Pts)" if points is not None else "") + "</p>"
         if desc: display_desc = str(desc).replace('\n', '<br>'); html += f"<p style='margin-left: 15px; margin-top: 1px; {FIELD_VALUE_STYLE}'>{display_desc}</p>"; return html
    def _format_hero_story_html(self, story_dict):
         if not story_dict or not isinstance(story_dict, dict): return ""
         title = story_dict.get("title"); content = story_dict.get("content"); status = story_dict.get("status"); html = ""
         if not title and not content: return ""
         if title: html = f"<p><span style='{FIELD_LABEL_STYLE}'>{title}</span></p>"
         if content: display_content = str(content).replace('\n', '<br>'); html += f"<div style='margin-left: 15px; margin-top: 1px; {FIELD_VALUE_STYLE}'>{display_content}</div>"
         if status: html += f"<p style='margin-left: 15px; font-style: italic; color: {DETAILS_COLOR};'>{status}</p>"; return html
    def _format_balance_change_html(self, change_dict):
         if not change_dict or not isinstance(change_dict, dict):
             return ""
         
         original_date_version_string = change_dict.get("date_version")
         changes_list = change_dict.get("changes")

         if not original_date_version_string or not changes_list or not isinstance(changes_list, list):
             return ""

         valid_changes = [c for c in changes_list if c and isinstance(c, str) and c.strip()]
         if not valid_changes:
             return ""

         # --- NEW: Americanize Date Logic ---
         display_date_heading = original_date_version_string # Default if parsing fails
         
         # Regex to capture YY/MM/DD at the start, followed by an optional colon and the rest
         date_parse_match = re.match(r"(\d{2})/(\d{2})/(\d{2})\s*(?::\s*(.*))?", original_date_version_string)
         
         if date_parse_match:
             year_yy = date_parse_match.group(1)
             month_mm = date_parse_match.group(2)
             day_dd = date_parse_match.group(3)
             remaining_text_after_date = date_parse_match.group(4) # This will be None if no colon and text after

             # Reformat to MM/DD/YY
             american_date_short = f"{month_mm}/{day_dd}/{year_yy}"
             
             # More descriptive date (e.g., April 11, 2025)
             month_names = {
                 "01": "Jan", "02": "Feb", "03": "Mar", "04": "Apr",
                 "05": "May", "06": "Jun", "07": "Jul", "08": "Aug",
                 "09": "Sep", "10": "Oct", "11": "Nov", "12": "Dec"
             }
             month_name_str = month_names.get(month_mm, month_mm) # Fallback to number if not in map
             full_year = f"20{year_yy}" # Assuming 21st century

             # Choose your preferred format here:
             # formatted_date = american_date_short
             formatted_date = f"{month_name_str} {day_dd}, {full_year}"

             display_date_heading = formatted_date
             if remaining_text_after_date and remaining_text_after_date.strip():
                 display_date_heading += f": {remaining_text_after_date.strip()}"
         # --- END Americanize Date Logic ---

         html_output = f"<p><span style='{FIELD_LABEL_STYLE}'>{display_date_heading}:</span></p>"
         html_output += f"<ul style='{LIST_ITEM_STYLE}'>" + "".join(f"<li>{self._make_text_links_clickable(change_item)}</li>" for change_item in valid_changes) + "</ul>" # Added link clicking for change items
         return html_output
    

    def _make_text_links_clickable(self, raw_text):
        if not raw_text: return ""
        url_pattern = re.compile(r'(\b(?:https?://|www\.)[^\s<>()"\']+)', re.IGNORECASE)
        def replace_url(match):
            url = match.group(1); display_url = url.replace('&', '&').replace('<', '<').replace('>', '>')
            href = url if url.startswith(('http://', 'https://')) else 'http://' + url
            link_style = "color:#77C4FF; text-decoration: underline;"; return f'<a href="{href}" style="{link_style}">{display_url}</a>'
        text_escaped = raw_text.replace('&', '&').replace('<', '<').replace('>', '>'); linked_text = url_pattern.sub(replace_url, text_escaped); return linked_text

    # Favorite button slots
    @Slot()
    def toggle_favorite_button(self):
        self._is_favorite = not self._is_favorite; self.update_favorite_button_style(); self.favorite_toggled.emit(self.character_name, self._is_favorite)
    def update_favorite_button_style(self):
        self.fav_button.setChecked(self._is_favorite); self.fav_button.setProperty("favorited", self._is_favorite); self.fav_button.setText("★" if self._is_favorite else "☆"); self.fav_button.style().unpolish(self.fav_button); self.fav_button.style().polish(self.fav_button)

# --- End of CharacterCard class ---

# Keep JsonUpdateWorker (Unchanged)
class JsonUpdateWorker(QThread):
    progress = Signal(int, int, str); finished = Signal(bool, str)
    def __init__(self, github_api_url, firebase_manifest_url, firebase_base_char_url, local_dir, parent=None):
        super().__init__(parent); self.github_api_url = github_api_url; self.firebase_manifest_url = firebase_manifest_url
        self.firebase_base_char_url = firebase_base_char_url; self.local_char_dir = Path(local_dir); self.is_running = True; self.source_used = "None"
    def run(self):
        print("JsonUpdateWorker: Thread started."); json_files_to_download = []; total_files_to_download = 0; files_downloaded = 0; error_occurred = False; first_error_details = ""; final_message = ""
        try:
            self.source_used = "GitHub"; print(f"JsonUpdateWorker: Attempting source: {self.source_used} ({self.github_api_url})")
            response_gh = requests.get(self.github_api_url, timeout=15); response_gh.raise_for_status(); repo_files_data = response_gh.json()
            for item in repo_files_data:
                if item['type'] == 'file' and item['name'].lower().endswith('.json'):
                    download_url = item.get('download_url')
                    if not download_url: raw_base = "https://raw.githubusercontent.com/Reg0lino/Marvel-Rivals-Dashboard/main/characters/"; download_url = raw_base + item['name']
                    json_files_to_download.append({'name': item['name'], 'url': download_url})
            if not json_files_to_download: raise ValueError("No JSON files found via GitHub API.")
            print(f"JsonUpdateWorker: Using {self.source_used} source. Found {len(json_files_to_download)} files.")
        except (requests.exceptions.RequestException, ValueError) as e_github:
            first_error_details = f"GitHub source failed: {type(e_github).__name__}: {e_github}"; print(f"WARN: {first_error_details}"); print(f"JsonUpdateWorker: Attempting Firebase fallback source: {self.firebase_manifest_url}")
            self.source_used = "Firebase"; json_files_to_download = []
            try:
                response_fb = requests.get(self.firebase_manifest_url, timeout=15); response_fb.raise_for_status(); manifest_filenames = response_fb.json()
                if not isinstance(manifest_filenames, list): raise ValueError("Invalid manifest format from Firebase (expected a JSON list).")
                for filename in manifest_filenames:
                    if isinstance(filename, str) and filename.lower().endswith('.json'):
                        base_url = self.firebase_base_char_url;
                        if not base_url.endswith('/'): base_url += '/'
                        full_url = base_url + filename; json_files_to_download.append({'name': filename, 'url': full_url})
                    else: print(f"WARN: Skipping invalid entry in Firebase manifest: {filename}")
                if not json_files_to_download: raise ValueError("No valid JSON filenames found in Firebase manifest.")
                print(f"JsonUpdateWorker: Using {self.source_used} fallback source. Found {len(json_files_to_download)} files from manifest.")
            except Exception as e_firebase:
                print(f"ERROR: Firebase fallback also failed: {type(e_firebase).__name__}: {e_firebase}"); error_occurred = True
                final_message = f"Update Failed:\n- {first_error_details}\n- Firebase fallback failed: {e_firebase}"; self.finished.emit(False, final_message)
                print("JsonUpdateWorker: Thread finished unsuccessfully (both sources failed)."); return
        except Exception as e_other_source:
             print(f"ERROR: Unexpected error determining download source: {e_other_source}"); error_occurred = True
             final_message = f"Update Failed: Error identifying download source: {e_other_source}"; self.finished.emit(False, final_message)
             print("JsonUpdateWorker: Thread finished unsuccessfully (source determination error)."); return
        if json_files_to_download:
            total_files_to_download = len(json_files_to_download); specific_download_errors = []
            try:
                self.local_char_dir.mkdir(parents=True, exist_ok=True); print(f"JsonUpdateWorker: Ensured local directory exists: {self.local_char_dir}")
                for index, file_info in enumerate(json_files_to_download):
                    filename = file_info['name']; download_url = file_info['url']; local_filepath = self.local_char_dir / filename
                    self.progress.emit(index, total_files_to_download, filename)
                    try:
                        file_response = requests.get(download_url, timeout=30); file_response.raise_for_status()
                        with open(local_filepath, 'wb') as f: f.write(file_response.content)
                        files_downloaded += 1
                    except requests.exceptions.RequestException as e_download:
                        error_occurred = True; err_msg = f"- Failed {filename}: {type(e_download).__name__}"; print(f"ERROR: {err_msg} ({e_download})"); specific_download_errors.append(err_msg)
                if not error_occurred: final_message = f"Successfully downloaded {files_downloaded} character files using {self.source_used}.\n\nPlease restart the dashboard to apply the updates."
                else:
                    final_message = f"Update completed with errors (Source: {self.source_used}).\nDownloaded: {files_downloaded}/{total_files_to_download}\nErrors:\n"
                    if len(specific_download_errors) <= 5: final_message += "\n".join(specific_download_errors)
                    else: final_message += "\n".join(specific_download_errors[:5]) + f"\n- ... ({len(specific_download_errors) - 5} more errors, check logs)"
                    final_message += "\n\nPlease check console logs. You may need to restart."
            except Exception as e_loop:
                print(f"ERROR: Unexpected error during download process setup: {e_loop}"); error_occurred = True; final_message = f"Update Failed: Error preparing download: {e_loop}"; import traceback; traceback.print_exc()
        else:
            if not error_occurred: final_message = f"Update check complete using {self.source_used}. No character files were found to download."; print(f"WARN: {final_message}")
        success = not error_occurred; self.finished.emit(success, final_message); print(f"JsonUpdateWorker: Thread finished. Success: {success}, Source Used: {self.source_used}")
    def stop(self): self.is_running = False; print("JsonUpdateWorker: Stop requested.")


# --- Main Window ---
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        print("Initializing MainWindow...")
        self.font_family = CURRENT_FONT_FAMILY_NAME
        self.using_custom_font = CUSTOM_FONT_LOADED
        self._load_external_config()
        load_character_summaries() # Keep loading summaries for jump bar/sorting
        self.favorites = load_favorites()
        self.character_cards = {}
        self.jump_bar_labels = {}
        self.jump_bar_flow_layout = None
        self.jump_bar_container = None
        self.json_update_worker = None
        self.setWindowTitle("Marvel Rivals Dashboard")

        # Icon Loading...
        try:
            icon_filename = "Marvel Rivals Dashboard.ico"; icon_path = resource_path(os.path.join('images', icon_filename))
            if os.path.exists(icon_path): self.setWindowIcon(QIcon(icon_path))
            else: print(f"WARNING: App icon not found at relative path {icon_path}")
        except Exception as e: print(f"ERROR setting main window icon: {e}")

        self.resize(1000, 950)
        self.main_widget = QWidget(); self.setCentralWidget(self.main_widget)
        self.main_layout = QVBoxLayout(self.main_widget); self.main_layout.setContentsMargins(10, 5, 10, 10); self.main_layout.setSpacing(8)

        # Create UI Elements...
        self.unified_top_bar = self._create_unified_top_bar()
        self.main_layout.addWidget(self.unified_top_bar)
        self._create_jump_bar() # Uses summary data
        if self.jump_bar_container: self.main_layout.addWidget(self.jump_bar_container)
        self._create_scroll_area()

        # --- Call reverted population method ---
        print("DEBUG: About to call populate_character_cards from __init__")
        self.populate_character_cards() # <<< Use reverted method name
        print("DEBUG: Returned from populate_character_cards called by __init__")
        # ---

        # Apply initial sort/filter...
        self.sort_and_filter_characters() # Filter will make them visible

        print("MainWindow initialization complete.")
        print(f"Dashboard DEBUG: Flag path configured as: {READY_FLAG_FILE}")
    # --- Override showEvent ---
    def showEvent(self, event):
        """Override showEvent to create the ready flag shortly after window appears."""
        super().showEvent(event) # Call base implementation first
        print("Dashboard DEBUG: MainWindow showEvent triggered.")
        # --- Remove Timer, call directly ---
        self._create_ready_flag()
        # ---

    # --- Flag Creation Method (Correctly placed in MainWindow) ---
    def _create_ready_flag(self):
        """Creates the ready flag file to signal the launcher."""
        print(f"Dashboard DEBUG: Attempting to create flag at: {READY_FLAG_FILE}") # Verify path again
        try:
            config_path_obj = Path(CONFIG_FOLDER)
            # Ensure config folder exists
            config_path_obj.mkdir(parents=True, exist_ok=True) # Use pathlib
            print(f"Dashboard DEBUG: Ensured config folder exists: {config_path_obj}")

            flag_path = Path(READY_FLAG_FILE)
            flag_path.touch(exist_ok=True) # Create empty file
            print(f"Dashboard: Successfully created ready flag: {READY_FLAG_FILE}")
        except Exception as e:
            # --- Enhanced Error Logging ---
            import traceback
            print(f"Dashboard ERROR: Failed to create ready flag '{READY_FLAG_FILE}': {e}")
            traceback.print_exc() # Log the full stack trace
            # ---

    # --- Rest of MainWindow methods ---
    def _load_external_config(self):
        global CHARACTER_IMAGE_MAP, CHARACTER_ICON_MAP, INFO_FILES
        if DEBUG_MODE: print("DEBUG: Attempting to load CHARACTER_IMAGE_MAP.")
        CHARACTER_IMAGE_MAP = load_json_config('character_images.json')
        if DEBUG_MODE: print(f"DEBUG: _load_external_config - CHARACTER_IMAGE_MAP loaded? {'Yes' if CHARACTER_IMAGE_MAP else 'No'}")
        if DEBUG_MODE: print("DEBUG: Attempting to load CHARACTER_ICON_MAP.")
        CHARACTER_ICON_MAP = load_json_config('character_icons.json')
        if DEBUG_MODE: print(f"DEBUG: _load_external_config - CHARACTER_ICON_MAP loaded? {'Yes' if CHARACTER_ICON_MAP else 'No'}")
        if DEBUG_MODE: print("DEBUG: Attempting to load INFO_FILES.")
        INFO_FILES = load_json_config('info_files.json')
        if DEBUG_MODE: print(f"DEBUG: _load_external_config - INFO_FILES loaded? {'Yes' if INFO_FILES else 'No'}")
        if not CHARACTER_IMAGE_MAP or not CHARACTER_ICON_MAP or not INFO_FILES:
             print("ERROR: Essential configuration files (JSON) missing or invalid. Cannot continue.")
             app_instance = QApplication.instance()
             if app_instance: QMessageBox.critical(None,"Fatal Error","Essential config files (JSON) missing or invalid."); app_instance.quit()
             sys.exit(1)

    def _create_unified_top_bar(self):
        top_bar_widget = QWidget(); main_top_layout = QVBoxLayout(top_bar_widget); main_top_layout.setContentsMargins(0, 5, 0, 5); main_top_layout.setSpacing(8)
        button_flow_container = QWidget(); button_flow_layout = FlowLayout(button_flow_container, margin=0, hSpacing=6, vSpacing=4)
        sp_buttons = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum); button_flow_container.setSizePolicy(sp_buttons)
        font_info_buttons = QFont(self.font_family, BASE_FONT_SIZE); sorted_info_keys = sorted(INFO_FILES.keys())
        for key in sorted_info_keys: button = QPushButton(key); button.setObjectName("InfoButton"); button.setFont(font_info_buttons); button.setToolTip(f"Show {key.replace('_', ' ').title()} Info"); button.clicked.connect(lambda checked=False, k=key: self._show_info_popup(k)); button_flow_layout.addWidget(button)
        tracker_button = QPushButton("Tracker"); tracker_button.setObjectName("InfoButton"); tracker_button.setFont(font_info_buttons); tracker_button.setToolTip("Open RivalsTracker Leaderboard (rivalstracker.com)"); tracker_url = QUrl("https://rivalstracker.com/leaderboard"); tracker_button.clicked.connect(lambda: QDesktopServices.openUrl(tracker_url)); button_flow_layout.addWidget(tracker_button)
        self.launch_ai_updater_button = QPushButton("Launch AI Updater"); self.launch_ai_updater_button.setObjectName("InfoButton"); self.launch_ai_updater_button.setFont(font_info_buttons); self.launch_ai_updater_button.setToolTip("Open the AI Data Scraper/Generator Tool (Requires Python & API Key setup)"); self.launch_ai_updater_button.clicked.connect(self._confirm_launch_updater); button_flow_layout.addWidget(self.launch_ai_updater_button)
        self.update_data_button = QPushButton("Update Data"); self.update_data_button.setObjectName("InfoButton"); self.update_data_button.setFont(font_info_buttons); self.update_data_button.setToolTip("Download latest character data & info files from the central source (Internet required)"); self.update_data_button.clicked.connect(self._start_json_update); button_flow_layout.addWidget(self.update_data_button)
        main_top_layout.addWidget(button_flow_container)
        search_controls_bar = QWidget(); search_controls_layout = QHBoxLayout(search_controls_bar); search_controls_layout.setContentsMargins(0, 0, 0, 0); search_controls_layout.setSpacing(8)
        font_controls = QFont(self.font_family, BASE_FONT_SIZE); self.search_input = QLineEdit(); self.search_input.setFont(font_controls); self.search_input.setPlaceholderText("Search Characters..."); self.search_input.textChanged.connect(self.filter_characters)
        self.sort_combo = QComboBox(); self.sort_combo.setFont(font_controls); self.sort_combo.addItems(["Sort by Name", "Sort by Role", "Favorites First"]); self.sort_combo.setCurrentText("Favorites First"); self.sort_combo.currentIndexChanged.connect(self.sort_and_filter_characters)
        self.filter_combo = QComboBox(); self.filter_combo.setFont(font_controls); self.filter_combo.addItems(["Filter by Role: All", "Vanguard", "Duelist", "Strategist"]); self.filter_combo.currentIndexChanged.connect(self.sort_and_filter_characters)
        search_controls_layout.addWidget(self.search_input, 1); search_controls_layout.addWidget(self.sort_combo); search_controls_layout.addWidget(self.filter_combo); search_controls_layout.addStretch(1)
        self.exit_button = QPushButton("✕"); self.exit_button.setObjectName("ExitButton"); self.exit_button.setFixedSize(24, 24); self.exit_button.setToolTip("Exit Application"); app_instance = QApplication.instance()
        if app_instance: self.exit_button.clicked.connect(app_instance.quit)
        else: print("WARNING: Could not connect Exit button: QApplication instance not found yet.")
        search_controls_layout.addWidget(self.exit_button); main_top_layout.addWidget(search_controls_bar)
        return top_bar_widget

    def _create_jump_bar(self):
        self.jump_bar_container = QGroupBox("Jump to Character"); title_font = QFont(self.font_family, GROUP_TITLE_FONT_SIZE); title_font.setWeight(QFont.Weight.Bold)
        self.jump_bar_container.setFont(title_font); self.jump_bar_container.setObjectName("JumpBarGroupBox"); self.jump_bar_container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        jump_bar_widget = QWidget(self.jump_bar_container); self.jump_bar_flow_layout = FlowLayout(jump_bar_widget, margin=0, hSpacing=JUMP_BAR_FIXED_SPACING, vSpacing=JUMP_BAR_FIXED_SPACING)
        sp_jump = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred); jump_bar_widget.setSizePolicy(sp_jump)
        group_content_layout = QVBoxLayout(self.jump_bar_container); group_content_layout.setContentsMargins(5, 8, 5, 5); group_content_layout.addWidget(jump_bar_widget)
        if not CHARACTER_SUMMARY_DATA:
            print("Jump Bar: No character summaries loaded to create icons.")
            placeholder_label = QLabel("(No characters found)"); placeholder_label.setAlignment(Qt.AlignmentFlag.AlignCenter); self.jump_bar_flow_layout.addWidget(placeholder_label)
            self.jump_bar_container.deleteLater(); self.jump_bar_container = None; return
        self.jump_bar_labels.clear()
        icon_font = QFont(self.font_family, BASE_FONT_SIZE + 1); icon_font.setWeight(QFont.Weight.Bold)
        if DEBUG_MODE: print(f"DEBUG JumpBar Setup: Creating icons for {len(CHARACTER_SUMMARY_DATA)} summaries...")
        for summary in CHARACTER_SUMMARY_DATA:
            char_name = summary['name']; icon_label = ClickableLabel(tooltip_text=char_name)
            icon_label.setFixedSize(JUMP_BAR_FIXED_ICON_SIZE, JUMP_BAR_FIXED_ICON_SIZE)
            icon_filename = summary.get('icon_file'); icon_found = False
            if icon_filename:
                icon_path = os.path.join(IMAGE_FOLDER, icon_filename)
                if os.path.exists(icon_path):
                    pixmap = QPixmap(icon_path)
                    if not pixmap.isNull(): scaled_pixmap = pixmap.scaled(JUMP_BAR_FIXED_ICON_SIZE, JUMP_BAR_FIXED_ICON_SIZE, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation); icon_label.setPixmap(scaled_pixmap); icon_found = True
            if not icon_found:
                first_letter = char_name[0].upper() if char_name else "?"; icon_label.setText(first_letter); icon_label.setFont(icon_font); icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter); icon_label.setStyleSheet(f"border: 1px solid #555; border-radius: 3px; color: #DDDDDD; background-color: #444444;")
            icon_label.clicked.connect(self.jump_to_character); self.jump_bar_labels[char_name] = icon_label; self.jump_bar_flow_layout.addWidget(icon_label)
        if DEBUG_MODE: print(f"DEBUG JumpBar Setup: Finished creating icons.")

    def _create_scroll_area(self):
        self.scroll_area = QScrollArea(); self.scroll_area.setWidgetResizable(True); self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setStyleSheet("QScrollArea { padding-top: %dpx; }" % SCROLL_PADDING_TOP)
        self.scroll_content_widget = QWidget(); self.scroll_layout = QVBoxLayout(self.scroll_content_widget)
        self.scroll_layout.setAlignment(Qt.AlignmentFlag.AlignTop); self.scroll_layout.setSpacing(15)
        self.scroll_area.setWidget(self.scroll_content_widget); self.main_layout.addWidget(self.scroll_area)

    def load_single_character_data(self, character_name):
        safe_filename_base = character_name.replace(' ', '_').replace('&', 'and'); filename = f"{safe_filename_base}.json"; filepath = os.path.join(CHARACTER_DATA_FOLDER, filename)
        if not os.path.exists(filepath): print(f"ERROR (Load Full): JSON file not found for '{character_name}' at {filepath}"); return None
        data = None
        try:
            with open(filepath, 'r', encoding='utf-8-sig') as f: data = json.load(f)
        except UnicodeDecodeError:
             try:
                 with open(filepath, 'r', encoding='utf-8') as f: data = json.load(f)
             except Exception as e_inner: print(f"ERROR loading {filepath} (UTF-8 fallback): {e_inner}"); return None
        except json.JSONDecodeError as e_json: print(f"ERROR (Load Full): Invalid JSON in {filepath}: {e_json} (Line: {e_json.lineno}, Col: {e_json.colno})"); return None
        except Exception as e: print(f"ERROR loading {filepath}: {e}"); return None
        if isinstance(data, dict): return data
        else: print(f"ERROR (Load Full): Data from {filepath} is not dict (Type: {type(data)})."); return None

    def populate_character_cards(self): # <<< RENAMED BACK
        """Creates full CharacterCard widgets based on summary data, loading full data."""
        print("Populating full character cards (Pre-loading)...") # <<< UPDATED PRINT

        # Clear existing cards
        while self.scroll_layout.count():
             item = self.scroll_layout.takeAt(0)
             if item and item.widget(): item.widget().deleteLater()
        self.character_cards.clear()

        if not CHARACTER_SUMMARY_DATA:
            print("No character summaries loaded to populate cards.")
            return

        created_count = 0
        error_count = 0
        # Loop through summaries to get names/favorites
        for summary in CHARACTER_SUMMARY_DATA:
            char_name = summary['name']
            is_fav = summary['is_fav'] # Get fav status from summary

            # --- Load FULL data here ---
            char_data = self.load_single_character_data(char_name)
            if char_data is None:
                print(f"  ERROR: Failed to load full data for '{char_name}'. Skipping card.")
                error_count += 1
                continue # Skip this card if data loading failed
            # ---

            # --- Create card with FULL data ---
            # Pass name, full data, and favorite status
            card = CharacterCard(char_name, char_data, is_fav) # <<< CHANGED SIGNATURE BACK
            card.favorite_toggled.connect(self.handle_favorite_toggle)
            # ---

            self.character_cards[char_name] = card
            self.scroll_layout.addWidget(card)
            card.setVisible(False) # Still initially hide until filter step
            created_count += 1

        print(f"Created {created_count} full card widgets.")
        if error_count > 0:
            print(f"  ({error_count} cards skipped due to data loading errors)")
    @Slot(str)
    def jump_to_character(self, character_name):
        if DEBUG_MODE: print(f"\nDEBUG Jump: Clicked on '{character_name}'")
        card_widget = self.character_cards.get(character_name)
        if DEBUG_MODE: print(f"DEBUG Jump: Card widget found? {'Yes' if card_widget else 'No'}")
        if card_widget:
            self.scroll_content_widget.layout().activate(); self.scroll_content_widget.adjustSize(); QApplication.processEvents()
            is_visible = card_widget.isVisible()
            if DEBUG_MODE: print(f"DEBUG Jump: Card visible? {is_visible}")
            if is_visible:
                v_scroll_bar = self.scroll_area.verticalScrollBar(); scrollbar_min = v_scroll_bar.minimum(); scrollbar_max = v_scroll_bar.maximum()
                if DEBUG_MODE: print(f"DEBUG Jump: Scroll range: min={scrollbar_min}, max={scrollbar_max}, current={v_scroll_bar.value()}")
                target_y = card_widget.pos().y(); offset = SCROLL_PADDING_TOP
                if scrollbar_max < scrollbar_min: scrollbar_max = scrollbar_min
                scroll_to_y = max(scrollbar_min, min(target_y - offset, scrollbar_max))
                if DEBUG_MODE: print(f"DEBUG Jump: Card y={target_y}, Offset={offset}, TargetScroll={scroll_to_y}")
                v_scroll_bar.setValue(scroll_to_y); QApplication.processEvents()
                if DEBUG_MODE: print(f"DEBUG Jump: Scrollbar value AFTER set = {v_scroll_bar.value()}")
            else: print(f"Cannot jump to '{character_name}', card is not visible.")
        else: print(f"Cannot jump to '{character_name}', card widget not found.")

    @Slot(str, bool)
    def handle_favorite_toggle(self, character_name, is_favorite):
        if is_favorite: self.favorites.add(character_name); print(f"Added '{character_name}' to favorites.")
        else: self.favorites.discard(character_name); print(f"Removed '{character_name}' from favorites.")
        save_favorites(self.favorites)
        if self.sort_combo.currentText() == "Favorites First":
            if DEBUG_MODE: print("DEBUG Favorite Toggle: Re-sorting and resetting scroll to top.")
            self.sort_and_filter_characters(); QTimer.singleShot(0, self._scroll_to_top)
        else:
            if character_name in self.character_cards: self.character_cards[character_name]._is_favorite = is_favorite
            if DEBUG_MODE: print("DEBUG Favorite Toggle: Sort is not 'Favorites First', no re-sort/scroll.")

    def _scroll_to_top(self):
        if self.scroll_area:
            v_scroll_bar = self.scroll_area.verticalScrollBar()
            if v_scroll_bar:
                if DEBUG_MODE: print(f"DEBUG ScrollToTop: Setting scroll value to minimum ({v_scroll_bar.minimum()}).")
                v_scroll_bar.setValue(v_scroll_bar.minimum())
            elif DEBUG_MODE: print("DEBUG ScrollToTop: Vertical scroll bar not found.")
        elif DEBUG_MODE: print("DEBUG ScrollToTop: Scroll area not found.")

    def filter_characters(self):
        search_term = self.search_input.text().lower().strip(); selected_role_filter = self.filter_combo.currentText().split(": ")[-1]
        role_filter_active = selected_role_filter != "All"; visible_count = 0
        for name, card in self.character_cards.items():
            show_card = True
            if role_filter_active:
                # Get role from the full data, ensure it's a string before lowercasing
                char_role_data = card.character_data.get('role', '')  # Get role from the full data
                char_role = char_role_data.lower() if isinstance(char_role_data, str) else ''  # Ensure it's a string before lowercasing
                if selected_role_filter.lower() != char_role: show_card = False
            if show_card and search_term:
                if search_term not in card.character_name.lower(): show_card = False
            card.setVisible(show_card);
            if show_card: visible_count += 1
        if DEBUG_MODE: print(f"DEBUG Filter: Search='{search_term}', Role='{selected_role_filter}'. Visible={visible_count}/{len(self.character_cards)}")

    def sort_and_filter_characters(self):
        print("Sorting and filtering cards..."); sort_key = self.sort_combo.currentText(); widgets_to_sort = []
        items_to_readd = []
        while self.scroll_layout.count():
             item = self.scroll_layout.takeAt(0)
             if item and item.widget() and isinstance(item.widget(), CharacterCard): widget = item.widget(); widget.setParent(None); widgets_to_sort.append(widget)
             elif item: items_to_readd.append(item)
        def get_name(widget): return widget.character_name
        def get_role(widget): return widget.summary_data.get('role', 'ZZZ')
        def get_favorite_then_name(widget): return (0 if widget._is_favorite else 1, widget.character_name)
        if sort_key == "Sort by Name": widgets_to_sort.sort(key=get_name)
        elif sort_key == "Sort by Role": widgets_to_sort.sort(key=lambda w: (get_role(w), get_name(w)))
        elif sort_key == "Favorites First": widgets_to_sort.sort(key=get_favorite_then_name)
        for widget in widgets_to_sort: self.scroll_layout.addWidget(widget)
        for item in items_to_readd: self.scroll_layout.addItem(item)
        self.filter_characters(); print("Sorting and filtering complete.")

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

    @Slot()
    def _confirm_launch_updater(self):
        reply = QMessageBox.question(self, "Launch Updater?", "This will close the dashboard and open the Updater tool (updater_v3.py).\n\nAre you sure?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            print("User confirmed. Launching updater_v3.py...")
            try:
                script_dir = os.path.dirname(__file__); updater_script_path = os.path.normpath(os.path.join(script_dir, 'scraper', 'updater_v3.py'))
                if os.path.exists(updater_script_path):
                    print(f"Found updater script at: {updater_script_path}"); subprocess.Popen([sys.executable, updater_script_path]); QApplication.instance().quit()
                else: error_msg = f"Updater script not found at:\n{updater_script_path}"; print(f"ERROR: {error_msg}"); QMessageBox.critical(self, "Error", error_msg)
            except Exception as e: error_msg = f"Failed to launch updater: {e}"; print(f"ERROR: {error_msg}"); QMessageBox.critical(self, "Launch Error", error_msg)

    @Slot()
    def _start_json_update(self):
        print("JSON Update: Button clicked.")
        reply = QMessageBox.question(self, "Confirm Data Update", "This will download the latest character data files from the central source, overwriting existing local files.\n\nThis cannot be undone. Are you sure?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            print("JSON Update: User confirmed. Proceeding...")
            if self.json_update_worker and self.json_update_worker.isRunning(): QMessageBox.information(self, "Update in Progress", "An update check is already running."); return
            self.update_data_button.setEnabled(False); self.update_data_button.setText("Checking...")
            local_dir = CHARACTER_DATA_FOLDER; github_api_url = "https://api.github.com/repos/Reg0lino/Marvel-Rivals-Dashboard/contents/characters"; firebase_base_url = "https://marvel-rivals-dashboard.web.app"; firebase_manifest_url = f"{firebase_base_url}/characters_manifest.json"; firebase_base_char_url = f"{firebase_base_url}/characters/"
            print(f"JSON Update: Starting worker.")
            self.json_update_worker = JsonUpdateWorker(github_api_url=github_api_url, firebase_manifest_url=firebase_manifest_url, firebase_base_char_url=firebase_base_char_url, local_dir=local_dir)
            self.json_update_worker.progress.connect(self._handle_update_progress); self.json_update_worker.finished.connect(self._handle_update_finished)
            self.json_update_worker.start(); print("JSON Update: Worker thread started.")
        else: print("JSON Update: User cancelled data update.")
    @Slot(int, int, str)
    def _handle_update_progress(self, current_file, total_files, filename):
        progress_text = f"Downloading {current_file + 1}/{total_files}..."; self.update_data_button.setText(progress_text); print(f"Progress: {progress_text} ({filename})")
    @Slot(bool, str)
    def _handle_update_finished(self, success, message):
        print(f"JSON Update: Worker finished. Success: {success}, Message: {message}")
        self.update_data_button.setEnabled(True); self.update_data_button.setText("Update Data")
        if success: QMessageBox.information(self, "Update Complete", message)
        else: QMessageBox.warning(self, "Update Failed", message)
        self.json_update_worker = None; print("JSON Update: Worker reference cleaned up.")

# --- End of MainWindow class ---

# --- Main Execution ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Marvel Rivals Dashboard")
    parser.add_argument('--debug', action='store_true', help='Enable detailed console logging.')
    # Screen argument now accepts Name OR Index (as string)
    parser.add_argument('--screen', type=str, default=None, help='Identifier (name or index) of the target screen.')
    parser.add_argument('--fullscreen', action='store_true', help='Start in fullscreen mode.')
    args = parser.parse_args()

    DEBUG_MODE = args.debug # Set global DEBUG_MODE from args
    print(f"Executing rivals_dashboard.py... DEBUG_MODE={'ON' if DEBUG_MODE else 'OFF'}")

    try: QApplication.setAttribute(Qt.AA_EnableHighDpiScaling); QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)
    except AttributeError: pass
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    app = QApplication(sys.argv)

    # --- Font Loading (Keep As Is) ---
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

    # Load static JSON Config (Unchanged)
    CHARACTER_IMAGE_MAP = load_json_config('character_images.json')
    CHARACTER_ICON_MAP = load_json_config('character_icons.json')
    INFO_FILES = load_json_config('info_files.json')

    app.setStyleSheet(get_stylesheet())

    try:
        window = MainWindow() # Instantiate main window

        # --- Screen and Fullscreen Handling (MODIFIED LOGIC) ---
        target_screen = None
        primary_screen = QApplication.primaryScreen()
        available_screens = QApplication.screens()
        screen_identifier_from_arg = args.screen # Name or Index passed from launcher

        print(f"Dashboard: Received screen identifier: '{screen_identifier_from_arg}'")

        if screen_identifier_from_arg is not None:
            found_match = False
            # 1. Try matching by name first (more reliable if names exist)
            for screen in available_screens:
                if screen.name() and screen.name() == screen_identifier_from_arg:
                    target_screen = screen
                    print(f"Dashboard: Found screen by NAME match: {screen.name()}")
                    found_match = True
                    break

            # 2. If no name match, try matching by index (as a fallback)
            if not found_match:
                try:
                    screen_index = int(screen_identifier_from_arg)
                    if 0 <= screen_index < len(available_screens):
                        target_screen = available_screens[screen_index]
                        print(f"Dashboard: Found screen by INDEX match: {screen_index} (Name: {target_screen.name() or 'N/A'})")
                        found_match = True
                    else:
                        print(f"Dashboard Warning: Screen index '{screen_index}' out of range.")
                except ValueError:
                    # Identifier was not a valid integer index string
                    print(f"Dashboard Warning: Screen identifier '{screen_identifier_from_arg}' is not a valid name or index.")

            # 3. If still no match, default to primary
            if not found_match:
                print(f"Dashboard Warning: Could not find screen matching identifier '{screen_identifier_from_arg}'. Using primary screen.")
                target_screen = primary_screen

        else: # Default to primary screen if no identifier was passed
            print("Dashboard: No screen identifier provided. Using primary screen.")
            target_screen = primary_screen

        # Fallback if target_screen is still somehow None
        if not target_screen:
            print("Dashboard Error: Could not determine target screen! Using first available.")
            target_screen = available_screens[0] if available_screens else None

        # --- Apply Geometry/Fullscreen based on target_screen ---
        if target_screen:
            screen_geometry = target_screen.geometry() # Use full geometry for fullscreen
            available_geometry = target_screen.availableGeometry() # Use available for windowed
            target_screen_name_for_log = target_screen.name() or f"Index {available_screens.index(target_screen)}"

            if args.fullscreen:
                print(f"Dashboard: Setting fullscreen mode on screen '{target_screen_name_for_log}'.")
                # Set geometry to the target screen's dimensions BEFORE showing fullscreen
                window.setGeometry(screen_geometry)
                window.showFullScreen()
            else: # Windowed mode positioning on the target screen
                print(f"Dashboard: Setting windowed mode on screen '{target_screen_name_for_log}'.")
                desired_width = 1000; desired_height = 950
                safe_width = min(desired_width, available_geometry.width())
                safe_height = min(desired_height, available_geometry.height())
                if safe_width != desired_width or safe_height != desired_height: print(f"Dashboard Warning: Clamped window size to {safe_width}x{safe_height} to fit screen.")
                window.resize(safe_width, safe_height)

                # Center on target screen's AVAILABLE geometry
                center_point = available_geometry.center()
                window_geo = window.frameGeometry()
                window_geo.moveCenter(center_point)
                # Clamp position
                final_pos = window_geo.topLeft()
                final_pos.setX(max(available_geometry.left(), min(final_pos.x(), available_geometry.right() - window_geo.width())))
                final_pos.setY(max(available_geometry.top(), min(final_pos.y(), available_geometry.bottom() - window_geo.height())))
                window.move(final_pos)
                window.show() # Show windowed AFTER setting size and position
        else:
            print("Dashboard Error: No target screen could be determined. Showing with default size/position.")
            window.resize(1020, 1000); window.show()
        # --- End Screen and Fullscreen Handling ---

        sys.exit(app.exec())

    except RuntimeError as e: print(f"Dashboard halted during init: {e}"); sys.exit(1)
    except Exception as e: import traceback; traceback.print_exc(); QMessageBox.critical(None, "Fatal Startup Error", f"An unexpected error occurred:\n{e}\n\nSee console for details."); sys.exit(1)
    parser = argparse.ArgumentParser(description="Marvel Rivals Dashboard")
    parser.add_argument('--debug', action='store_true', help='Enable detailed console logging.')
    parser.add_argument('--screen', type=str, default=None, help='Name of the target screen to launch on.')
    parser.add_argument('--fullscreen', action='store_true', help='Start in fullscreen mode.')
    args = parser.parse_args()

    DEBUG_MODE = args.debug # Set global DEBUG_MODE from args
    print(f"Executing rivals_dashboard.py... DEBUG_MODE={'ON' if DEBUG_MODE else 'OFF'}")

    try: QApplication.setAttribute(Qt.AA_EnableHighDpiScaling); QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)
    except AttributeError: pass
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    app = QApplication(sys.argv)

    # --- Font Loading (Keep As Is) ---
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

    # Load static JSON Config (Unchanged)
    CHARACTER_IMAGE_MAP = load_json_config('character_images.json')
    CHARACTER_ICON_MAP = load_json_config('character_icons.json')
    INFO_FILES = load_json_config('info_files.json')

    app.setStyleSheet(get_stylesheet())

    try:
        window = MainWindow() # Instantiate main window (uses optimized loading)

        # --- Screen and Fullscreen Handling (Keep As Is) ---
        target_screen = None; primary_screen = QApplication.primaryScreen()
        if args.screen:
            available_screens = QApplication.screens(); screen_found = False
            for screen in available_screens:
                current_screen_name = screen.name() if screen.name() else f"Unknown_{available_screens.index(screen)}"
                if current_screen_name == args.screen: target_screen = screen; print(f"Dashboard: Using target screen: {args.screen}"); screen_found = True; break
            if not screen_found: print(f"Dashboard Warning: Screen '{args.screen}' not found. Using primary."); target_screen = primary_screen
        else: print("Dashboard: Using primary screen."); target_screen = primary_screen
        if not target_screen: print("Dashboard Error: Could not determine target screen!"); target_screen = QApplication.screens()[0] if QApplication.screens() else None
        if target_screen:
            screen_geometry = target_screen.geometry(); available_geometry = target_screen.availableGeometry()
            if args.fullscreen: print("Dashboard: Setting fullscreen mode."); window.setGeometry(screen_geometry); window.showFullScreen()
            else:
                print("Dashboard: Setting windowed mode."); desired_width = 1000; desired_height = 950
                safe_width = min(desired_width, available_geometry.width()); safe_height = min(desired_height, available_geometry.height())
                if safe_width != desired_width or safe_height != desired_height: print(f"Dashboard Warning: Clamped window size to {safe_width}x{safe_height}.")
                window.resize(safe_width, safe_height)
                center_point = available_geometry.center(); window_geo = window.frameGeometry(); window_geo.moveCenter(center_point)
                final_pos = window_geo.topLeft()
                final_pos.setX(max(available_geometry.left(), min(final_pos.x(), available_geometry.right() - window_geo.width())))
                final_pos.setY(max(available_geometry.top(), min(final_pos.y(), available_geometry.bottom() - window_geo.height())))
                window.move(final_pos); window.show()
        else: print("Dashboard Error: No target screen. Showing default."); window.resize(1020, 1000); window.show()

        sys.exit(app.exec())

    except RuntimeError as e: print(f"Dashboard halted during init: {e}"); sys.exit(1)
    except Exception as e: import traceback; traceback.print_exc(); QMessageBox.critical(None, "Fatal Startup Error", f"An unexpected error occurred:\n{e}\n\nSee console for details."); sys.exit(1)