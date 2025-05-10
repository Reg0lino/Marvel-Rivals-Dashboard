# data_forge_main.py
import sys
import os
import json
import re # For robust filename cleaning
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QLabel, QFileDialog, QTabWidget, QFormLayout,
                             QLineEdit, QTextEdit, QComboBox, QListWidget, QListWidgetItem,
                             QMessageBox, QDialog,
                             QSpinBox, QDoubleSpinBox, QScrollArea, QStackedWidget,
                             QGroupBox, QDialogButtonBox) # Added QGroupBox, QDialog, QDialogButtonBox
from PyQt5.QtGui import QPixmap, QMovie, QFont, QIcon, QFontDatabase
from PyQt5.QtCore import Qt, QSize

# --- Constants for Directories ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHARACTERS_DIR = os.path.join(BASE_DIR, "characters")
IMAGES_DIR = os.path.join(BASE_DIR, "images")
CONFIG_DIR = os.path.join(BASE_DIR, "config")
STYLES_DIR = os.path.join(BASE_DIR, "styles")
CHARACTER_COLOR_POOLS_FILE = os.path.join(CONFIG_DIR, "character_color_pools.json")
EDITOR_STYLESHEET_PATH = os.path.join(STYLES_DIR, "editor_theme.qss")

# --- Placeholder List Editor Dialog ---
class ListEntryDialog(QDialog):
    def __init__(self, parent=None, title="Edit Entry", current_text=""):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.layout = QVBoxLayout(self)
        self.text_edit = QTextEdit(current_text)
        self.text_edit.setAcceptRichText(True) # Allow basic HTML
        self.text_edit.setMinimumHeight(100)
        self.layout.addWidget(self.text_edit)
        self.buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, Qt.Horizontal, self)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        self.layout.addWidget(self.buttons)
        self.setMinimumWidth(400)

    def get_text(self):
        return self.text_edit.toHtml()

class ComboEntryDialog(QDialog): # For Key Combos
    def __init__(self, parent=None, combo_data=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Key Combo")
        self.layout = QFormLayout(self)
        self.layout.setSpacing(10)

        self.name_edit = QLineEdit()
        self.sequence_edit = QTextEdit()
        self.purpose_edit = QTextEdit()
        self.notes_edit = QTextEdit()

        for editor in [self.sequence_edit, self.purpose_edit, self.notes_edit]:
            editor.setAcceptRichText(True)
            editor.setMinimumHeight(80)

        if combo_data:
            self.name_edit.setText(combo_data.get("name", ""))
            self.sequence_edit.setHtml(combo_data.get("sequence_description_html", ""))
            self.purpose_edit.setHtml(combo_data.get("purpose_html", ""))
            self.notes_edit.setHtml(combo_data.get("notes_html", ""))

        self.layout.addRow("Combo Name:", self.name_edit)
        self.layout.addRow("Sequence (HTML):", self.sequence_edit)
        self.layout.addRow("Purpose (HTML):", self.purpose_edit)
        self.layout.addRow("Notes (HTML):", self.notes_edit)

        self.buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, Qt.Horizontal, self)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        self.layout.addWidget(self.buttons)
        self.setMinimumWidth(500)

    def get_data(self):
        return {
            "name": self.name_edit.text(),
            "sequence_description_html": self.sequence_edit.toHtml(),
            "purpose_html": self.purpose_edit.toHtml(),
            "notes_html": self.notes_edit.toHtml()
        }


class DataForgeWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Rivals Data Forge")
        self.setGeometry(100, 100, 1600, 950)
        self.current_character_data = None
        self.current_character_filepath = None
        self.unsaved_changes = False
        self.app_font_family = "Arial"
        self.font_point_size = 14
        self.roles = ["Duelist", "Strategist", "Vanguard", "Unknown"]
        self.character_color_pools = self.load_color_pools()
        self.base_stylesheet = ""

        self.input_widgets_identity = []
        self.input_widgets_lore = []
        self.input_widgets_gameplay = [] # For Gameplay Strategy tab
        self.ability_forms = {}
        self.input_widgets_ability_forms = {}
        self.themed_labels = []

        self.set_app_icon()
        self.load_custom_font()
        self.initUI()
        self.load_styles_qss_initial()

    # ... (load_color_pools, set_app_icon, load_custom_font, load_styles_qss_initial as before) ...
    def load_color_pools(self):
        try:
            if os.path.exists(CHARACTER_COLOR_POOLS_FILE):
                with open(CHARACTER_COLOR_POOLS_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Error loading character color pools: {e}")
        return {}

    def set_app_icon(self):
        app_icon_path = os.path.join(IMAGES_DIR, "Marvel Rivals Dashboard.ico")
        if os.path.exists(app_icon_path):
            self.setWindowIcon(QIcon(app_icon_path))

    def load_custom_font(self):
        font_path = os.path.join(STYLES_DIR, "font", "Refrigerator Deluxe.otf")
        if os.path.exists(font_path):
            font_id = QFontDatabase.addApplicationFont(font_path)
            if font_id != -1:
                font_families = QFontDatabase.applicationFontFamilies(font_id)
                if font_families:
                    self.app_font_family = font_families[0]
                    app_font = QFont(self.app_font_family, self.font_point_size)
                    QApplication.setFont(app_font)
                    self.setFont(app_font)
                    print(f"Custom font '{self.app_font_family}' loaded at {self.font_point_size}pt for editor.")
                    return
        default_font = QFont("Arial", self.font_point_size)
        QApplication.setFont(default_font)
        self.setFont(default_font)
        print(f"Using default font 'Arial' at {self.font_point_size}pt.")

    def load_styles_qss_initial(self):
        if os.path.exists(EDITOR_STYLESHEET_PATH):
            with open(EDITOR_STYLESHEET_PATH, "r") as f:
                self.base_stylesheet = f.read()
            self.setStyleSheet(self.base_stylesheet)
            print("Base editor stylesheet loaded.")
        else:
            print(f"EDITOR STYLESHEET NOT FOUND at {EDITOR_STYLESHEET_PATH}")
            self.setStyleSheet("QWidget { background-color: #282828; color: #E5E5E5; font-size: 14pt; }")


    def apply_character_theme_styles(self, primary_color, secondary_color):
        print(f"DEBUG: Applying character theme. Primary: {primary_color}, Secondary: {secondary_color}")
        if not primary_color: primary_color = "#0078D7"
        if not secondary_color: secondary_color = self.lighten_color(primary_color, 30)
        contrasting_text_color_primary = self.get_contrasting_text_color(primary_color)
        dynamic_styles = f"""
            QTabWidget::pane {{ border: 3px solid {secondary_color}; border-top: none; }}
            QTabBar::tab:selected {{
                background-color: {primary_color}; color: {contrasting_text_color_primary};
                border: 1px solid {self.lighten_color(primary_color, -20)};
                border-bottom-color: {primary_color};
            }}
            QTabBar::tab:hover:selected {{ background-color: {self.lighten_color(primary_color, 15)}; }}
            QLineEdit:focus, QTextEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {{
                border: 2px solid {primary_color};
            }}
            QListWidget::item:selected {{ background-color: {primary_color}; color: {contrasting_text_color_primary}; }}
            QScrollArea QScrollBar::handle:vertical, QListWidget QScrollBar::handle:vertical, QTextEdit QScrollBar::handle:vertical {{
                background: {secondary_color};
            }}
            QScrollArea QScrollBar::handle:vertical:hover, QListWidget QScrollBar::handle:vertical:hover, QTextEdit QScrollBar::handle:vertical:hover {{
                background: {self.lighten_color(secondary_color, 15)};
            }}
            QScrollArea QScrollBar::handle:horizontal, QListWidget QScrollBar::handle:horizontal, QTextEdit QScrollBar::handle:horizontal {{
                background: {secondary_color};
            }}
            QScrollArea QScrollBar::handle:horizontal:hover, QListWidget QScrollBar::handle:horizontal:hover, QTextEdit QScrollBar::handle:horizontal:hover {{
                background: {self.lighten_color(secondary_color, 15)};
            }}
            QComboBox QAbstractItemView::item:selected {{ background-color: {primary_color}; color: {contrasting_text_color_primary}; }}
        """
        self.setStyleSheet(self.base_stylesheet + dynamic_styles)
        current_char_name = self.current_character_data.get("name", "No Character Loaded") if self.current_character_data else "No Character Loaded"
        self.char_name_label.setText(current_char_name)
        self.char_name_label.setStyleSheet(f"""
            QLabel#CharacterNameDynamicLabel {{
                font-size: 24pt; font-weight: bold; padding-left: 10px;
                color: {primary_color}; background-color: transparent;
            }}
        """)
        for label, color_type in self.themed_labels:
            color_to_use = primary_color if color_type == "primary" else secondary_color
            current_style = label.styleSheet() # Get existing style if any
            label.setStyleSheet(f"{current_style} color: {color_to_use}; font-weight: bold; background-color: transparent;")

    def initUI(self):
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(10,10,10,10)
        self.main_layout.setSpacing(10)

        top_bar_layout = QHBoxLayout()
        top_bar_layout.setSpacing(15)
        self.title_label = QLabel("Rivals Data Forge")
        self.title_label.setObjectName("DataForgeAppTitleLabel")
        self.title_label.setAlignment(Qt.AlignCenter)
        top_bar_layout.addWidget(self.title_label, 1)
        self.load_button = QPushButton("Load Character")
        self.load_button.clicked.connect(self.load_character_dialog)
        top_bar_layout.addWidget(self.load_button)
        self.save_button = QPushButton("Save Changes")
        self.save_button.clicked.connect(self.save_character_data_ui)
        self.save_button.setEnabled(False)
        top_bar_layout.addWidget(self.save_button)
        self.main_layout.addLayout(top_bar_layout)

        self.character_display_widget = QWidget()
        character_display_layout = QHBoxLayout(self.character_display_widget)
        character_display_layout.setContentsMargins(0, 10, 0, 5)
        self.char_icon_label = QLabel()
        self.char_icon_label.setFixedSize(80, 80)
        self.char_icon_label.setAlignment(Qt.AlignCenter)
        self.char_icon_label.setStyleSheet("border: 1px solid #444; border-radius: 5px; background-color: #202020;")
        character_display_layout.addWidget(self.char_icon_label)
        self.char_name_label = QLabel("No Character Loaded")
        self.char_name_label.setObjectName("CharacterNameDynamicLabel")
        character_display_layout.addWidget(self.char_name_label)
        character_display_layout.addStretch()
        self.main_layout.addWidget(self.character_display_widget)
        self.character_display_widget.setVisible(False)

        body_layout = QHBoxLayout()
        body_layout.setSpacing(15)
        self.main_content_stack = QStackedWidget()
        body_layout.addWidget(self.main_content_stack, 3)

        self.welcome_widget = QWidget()
        welcome_layout = QVBoxLayout(self.welcome_widget)
        welcome_layout.setAlignment(Qt.AlignCenter)
        
        # --- Welcome Screen GIF changed to wolv.gif ---
        wolv_gif_path = os.path.join(IMAGES_DIR, "wolv.gif")
        self.large_welcome_gif_label = QLabel() # Renamed for clarity
        if os.path.exists(wolv_gif_path):
            self.large_welcome_movie = QMovie(wolv_gif_path) # Renamed
            self.large_welcome_movie.setScaledSize(QSize(450, 450)) # Scaled up
            self.large_welcome_gif_label.setMovie(self.large_welcome_movie)
            self.large_welcome_movie.start()
        else:
            self.large_welcome_gif_label.setText("Welcome GIF (wolv.gif) Not Found")
        welcome_layout.addStretch(1)
        welcome_layout.addWidget(self.large_welcome_gif_label)
        welcome_text = QLabel("Load a Character to Begin Editing!")
        welcome_text.setAlignment(Qt.AlignCenter)
        welcome_text.setFont(QFont(self.app_font_family, 18, QFont.Bold))
        welcome_layout.addWidget(welcome_text)
        welcome_layout.addStretch(2)
        self.main_content_stack.addWidget(self.welcome_widget)

        self.tab_widget = QTabWidget()
        self.tab_widget.setObjectName("MainTabWidget")
        self.themed_labels.clear() # Clear before setting up tabs
        self.tab_identity_stats = QWidget()
        self.setup_identity_stats_tab()
        self.tab_widget.addTab(self.tab_identity_stats, "Identity & Stats")
        self.tab_lore_quotes_scroll = QScrollArea()
        self.tab_lore_quotes_scroll.setWidgetResizable(True)
        self.setup_lore_quotes_tab()
        self.tab_widget.addTab(self.tab_lore_quotes_scroll, "Lore & Quotes")
        self.tab_abilities = QWidget()
        self.setup_abilities_kit_tab()
        self.tab_widget.addTab(self.tab_abilities, "Abilities Kit")
        
        self.tab_gameplay_scroll = QScrollArea()
        self.tab_gameplay_scroll.setWidgetResizable(True)
        self.setup_gameplay_strategy_tab() # Call the new setup method
        self.tab_widget.addTab(self.tab_gameplay_scroll, "Gameplay Strategy")

        self.tab_matchups_teamups = QWidget()
        self.tab_widget.addTab(self.tab_matchups_teamups, "Matchups & Team-Ups")
        self.tab_meta_balance = QWidget()
        self.tab_widget.addTab(self.tab_meta_balance, "Meta & Balance")
        self.main_content_stack.addWidget(self.tab_widget)

        self.sidebar_gif_widget = QWidget()
        self.sidebar_gif_widget.setFixedWidth(280)
        sidebar_gif_layout = QVBoxLayout(self.sidebar_gif_widget)
        sidebar_gif_layout.setAlignment(Qt.AlignCenter)
        sidebar_gif_layout.setContentsMargins(5,5,5,5)
        self.sidebar_spidey_gif_label = QLabel()
        spidey_gif_path = os.path.join(IMAGES_DIR, "loading.gif") # Path for sidebar Spidey
        if os.path.exists(spidey_gif_path):
            self.sidebar_spidey_movie = QMovie(spidey_gif_path)
            self.sidebar_spidey_movie.setScaledSize(QSize(250, 250))
            self.sidebar_spidey_gif_label.setMovie(self.sidebar_spidey_movie)
            self.sidebar_spidey_movie.start()
        else:
            self.sidebar_spidey_gif_label.setText("Sidebar GIF Not Found")
        sidebar_gif_layout.addWidget(self.sidebar_spidey_gif_label)
        body_layout.addWidget(self.sidebar_gif_widget)

        self.main_layout.addLayout(body_layout, 1)
        self.main_content_stack.setCurrentWidget(self.welcome_widget)
        self.tab_widget.setEnabled(False)
        self.statusBar().showMessage("Ready. Load a character to begin editing.")

    # ... (setup_identity_stats_tab, setup_lore_quotes_tab, setup_abilities_kit_tab as before) ...
    # ... (_create_ability_form_widget, display_selected_ability_form, _get_form_id_from_item_data, populate_ability_selector as before) ...
    # ... (_clean_for_filename, load_character_dialog, load_character_data_from_file as before, ensuring debug prints are there) ...
    # ... (get_contrasting_text_color, lighten_color as before) ...
    # ... (populate_ui_from_data - will need update for gameplay tab later) ...
    # ... (disconnect_all_input_signals, connect_all_input_signals - will need update) ...
    # ... (disconnect_signals_for_form, connect_signals_for_form, mark_unsaved_changes as before) ...
    # ... (save_character_data_ui, gather_data_from_ui - will need update) ...
    # ... (closeEvent as before) ...
    def setup_identity_stats_tab(self):
        widget_content = QWidget()
        layout = QFormLayout(widget_content)
        layout.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        layout.setLabelAlignment(Qt.AlignRight); layout.setSpacing(10)
        self.input_widgets_identity = []
        self.identity_id_value = QLineEdit(); self.identity_id_value.setReadOnly(True)
        layout.addRow("Character ID:", self.identity_id_value)
        self.identity_name_edit = QLineEdit(); self.identity_name_edit.setReadOnly(True)
        layout.addRow("Name:", self.identity_name_edit)
        self.identity_role_combo = QComboBox(); self.identity_role_combo.addItems(self.roles); self.identity_role_combo.setEnabled(False)
        layout.addRow("Role:", self.identity_role_combo)
        self.identity_release_version_edit = QLineEdit()
        layout.addRow("Release Version:", self.identity_release_version_edit); self.input_widgets_identity.append(self.identity_release_version_edit)
        stats_group_label = QLabel("Basic Stats"); stats_group_label.setObjectName("SectionHeaderLabel")
        self.themed_labels.append((stats_group_label, "secondary"))
        layout.addRow(stats_group_label)
        self.stats_health_spin = QSpinBox(); self.stats_health_spin.setRange(0,9999); layout.addRow("Health:", self.stats_health_spin); self.input_widgets_identity.append(self.stats_health_spin)
        self.stats_armor_spin = QSpinBox(); self.stats_armor_spin.setRange(0,9999); layout.addRow("Armor:", self.stats_armor_spin); self.input_widgets_identity.append(self.stats_armor_spin)
        self.stats_shields_spin = QSpinBox(); self.stats_shields_spin.setRange(0,9999); layout.addRow("Regen. Shields:", self.stats_shields_spin); self.input_widgets_identity.append(self.stats_shields_spin)
        self.stats_speed_spin = QDoubleSpinBox(); self.stats_speed_spin.setRange(0,99.9); self.stats_speed_spin.setDecimals(1); self.stats_speed_spin.setSuffix(" m/s")
        layout.addRow("Speed:", self.stats_speed_spin); self.input_widgets_identity.append(self.stats_speed_spin)
        self.stats_difficulty_spin = QSpinBox(); self.stats_difficulty_spin.setRange(0,5); layout.addRow("Difficulty (0-5):", self.stats_difficulty_spin); self.input_widgets_identity.append(self.stats_difficulty_spin)
        self.stats_resource_type_edit = QLineEdit(); layout.addRow("Resource Type:", self.stats_resource_type_edit); self.input_widgets_identity.append(self.stats_resource_type_edit)
        self.stats_resource_max_spin = QSpinBox(); self.stats_resource_max_spin.setRange(0,99999); layout.addRow("Max Resource:", self.stats_resource_max_spin); self.input_widgets_identity.append(self.stats_resource_max_spin)
        self.tab_identity_stats.setLayout(layout)

    def setup_lore_quotes_tab(self):
        content_widget = QWidget()
        layout = QFormLayout(content_widget)
        layout.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        layout.setLabelAlignment(Qt.AlignRight); layout.setSpacing(10)
        self.input_widgets_lore = []
        quotes_label = QLabel("Notable Quotes"); quotes_label.setObjectName("SectionHeaderLabel")
        self.themed_labels.append((quotes_label, "secondary"))
        layout.addRow(quotes_label)
        self.lore_ingame_bio_quote_edit = QTextEdit(); self.lore_ingame_bio_quote_edit.setPlaceholderText("In-game bio quote..."); self.lore_ingame_bio_quote_edit.setFixedHeight(80)
        layout.addRow("Bio Quote:", self.lore_ingame_bio_quote_edit); self.input_widgets_lore.append(self.lore_ingame_bio_quote_edit)
        self.lore_official_quote_edit = QTextEdit(); self.lore_official_quote_edit.setPlaceholderText("Official quote..."); self.lore_official_quote_edit.setFixedHeight(80)
        layout.addRow("Official Quote:", self.lore_official_quote_edit); self.input_widgets_lore.append(self.lore_official_quote_edit)
        lore_details_label = QLabel("Lore Details"); lore_details_label.setObjectName("SectionHeaderLabel")
        self.themed_labels.append((lore_details_label, "secondary"))
        layout.addRow(lore_details_label)
        self.lore_ingame_bio_text_edit = QTextEdit(); self.lore_ingame_bio_text_edit.setPlaceholderText("In-game bio text (HTML)..."); self.lore_ingame_bio_text_edit.setMinimumHeight(120)
        layout.addRow("In-Game Bio:", self.lore_ingame_bio_text_edit); self.input_widgets_lore.append(self.lore_ingame_bio_text_edit)
        self.lore_official_description_edit = QTextEdit(); self.lore_official_description_edit.setPlaceholderText("Official description (HTML)..."); self.lore_official_description_edit.setMinimumHeight(120)
        layout.addRow("Official Desc.:", self.lore_official_description_edit); self.input_widgets_lore.append(self.lore_official_description_edit)
        self.lore_real_name_edit = QLineEdit(); layout.addRow("Real Name:", self.lore_real_name_edit); self.input_widgets_lore.append(self.lore_real_name_edit)
        self.lore_aliases_edit = QLineEdit(); self.lore_aliases_edit.setPlaceholderText("Comma-separated")
        layout.addRow("Aliases:", self.lore_aliases_edit); self.input_widgets_lore.append(self.lore_aliases_edit)
        self.lore_birthplace_edit = QLineEdit(); layout.addRow("Birthplace:", self.lore_birthplace_edit); self.input_widgets_lore.append(self.lore_birthplace_edit)
        self.lore_gender_edit = QLineEdit(); layout.addRow("Gender:", self.lore_gender_edit); self.input_widgets_lore.append(self.lore_gender_edit)
        self.lore_eye_color_edit = QLineEdit(); layout.addRow("Eye Color:", self.lore_eye_color_edit); self.input_widgets_lore.append(self.lore_eye_color_edit)
        self.lore_hair_color_edit = QLineEdit(); layout.addRow("Hair Color:", self.lore_hair_color_edit); self.input_widgets_lore.append(self.lore_hair_color_edit)
        self.lore_affiliation_edit = QLineEdit(); self.lore_affiliation_edit.setPlaceholderText("Comma-separated")
        layout.addRow("Affiliation:", self.lore_affiliation_edit); self.input_widgets_lore.append(self.lore_affiliation_edit)
        self.tab_lore_quotes_scroll.setWidget(content_widget)

    def setup_abilities_kit_tab(self):
        main_abilities_layout = QHBoxLayout(self.tab_abilities)
        main_abilities_layout.setSpacing(10)
        self.ability_selector_list = QListWidget()
        self.ability_selector_list.setFixedWidth(300)
        self.ability_selector_list.setObjectName("AbilitySelector")
        self.ability_selector_list.currentItemChanged.connect(self.display_selected_ability_form)
        main_abilities_layout.addWidget(self.ability_selector_list)
        self.ability_form_scroll_area = QScrollArea()
        self.ability_form_scroll_area.setWidgetResizable(True)
        main_abilities_layout.addWidget(self.ability_form_scroll_area, 1)
        self.ability_form_stack = QStackedWidget()
        default_ability_widget = QWidget()
        default_layout = QVBoxLayout(default_ability_widget)
        default_layout.setAlignment(Qt.AlignCenter)
        default_label = QLabel("Select an ability from the left to edit details.")
        default_label.setWordWrap(True)
        default_layout.addWidget(default_label)
        default_layout.addStretch()
        self.ability_form_stack.addWidget(default_ability_widget)
        self.ability_form_scroll_area.setWidget(self.ability_form_stack)

    def _create_ability_form_widget(self, ability_data, form_id_suffix):
        form_widget = QWidget()
        layout = QFormLayout(form_widget)
        layout.setContentsMargins(15,15,15,15); layout.setSpacing(10)
        layout.setLabelAlignment(Qt.AlignRight)
        current_input_widgets = []
        name_edit = QLineEdit(ability_data.get("name", f"New Ability {form_id_suffix}"))
        layout.addRow("Name:", name_edit); current_input_widgets.append(name_edit)
        desc_edit = QTextEdit(ability_data.get("description", ""))
        desc_edit.setPlaceholderText("Ability description (plain text for now)..."); desc_edit.setFixedHeight(100)
        layout.addRow("Description:", desc_edit); current_input_widgets.append(desc_edit)
        keybind_edit = QLineEdit(ability_data.get("keybind", ""))
        layout.addRow("Keybind:", keybind_edit); current_input_widgets.append(keybind_edit)
        cooldown_edit = QLineEdit(ability_data.get("cooldown", ""))
        layout.addRow("Cooldown:", cooldown_edit); current_input_widgets.append(cooldown_edit)
        self.input_widgets_ability_forms[form_id_suffix] = current_input_widgets
        return form_widget

    def display_selected_ability_form(self, current_item, previous_item):
        if previous_item:
            prev_item_data = previous_item.data(Qt.UserRole)
            if prev_item_data:
                prev_form_id = self._get_form_id_from_item_data(prev_item_data)
                self.disconnect_signals_for_form(prev_form_id)
        if not current_item:
            self.ability_form_stack.setCurrentIndex(0); return
        item_data = current_item.data(Qt.UserRole)
        if not item_data:
            self.ability_form_stack.setCurrentIndex(0); return
        form_id = self._get_form_id_from_item_data(item_data)
        ability_data_from_json = item_data.get("original_data", {})
        if form_id not in self.ability_forms:
            new_form_widget = self._create_ability_form_widget(ability_data_from_json, form_id)
            self.ability_forms[form_id] = new_form_widget
            self.ability_form_stack.addWidget(new_form_widget)
        form_to_display = self.ability_forms.get(form_id)
        if form_to_display:
            self.ability_form_stack.setCurrentWidget(form_to_display)
            self.connect_signals_for_form(form_id)
        else:
            self.ability_form_stack.setCurrentIndex(0)

    def _get_form_id_from_item_data(self, item_data):
        source_key = item_data.get("source_key")
        index = item_data.get("index")
        form_id = f"{source_key}"
        if index is not None: form_id += f"_{index}"
        return form_id

    def populate_ability_selector(self):
        self.ability_selector_list.clear()
        if not self.current_character_data: return
        abilities = self.current_character_data.get("abilities", [])
        ultimate = self.current_character_data.get("ultimate", {})
        passives = self.current_character_data.get("passives", [])
        for i, ab_data in enumerate(abilities):
            name = ab_data.get("name", f"Ability {i+1}")
            list_item = QListWidgetItem(f"{name} (Ability)")
            list_item.setData(Qt.UserRole, {"source_key": "abilities", "index": i, "original_data": ab_data})
            self.ability_selector_list.addItem(list_item)
        if ultimate and ultimate.get("name"):
            name = ultimate.get("name", "Ultimate")
            list_item = QListWidgetItem(f"{name} (Ultimate)")
            list_item.setData(Qt.UserRole, {"source_key": "ultimate", "index": None, "original_data": ultimate})
            self.ability_selector_list.addItem(list_item)
        for i, pa_data in enumerate(passives):
            name = pa_data.get("name", f"Passive {i+1}")
            list_item = QListWidgetItem(f"{name} (Passive)")
            list_item.setData(Qt.UserRole, {"source_key": "passives", "index": i, "original_data": pa_data})
            self.ability_selector_list.addItem(list_item)
        if self.ability_selector_list.count() > 0:
            self.ability_selector_list.setCurrentRow(0)

    def _clean_for_filename(self, name):
        name = name.replace('&', 'and')
        name = re.sub(r'[^\w\s-]', '', name)
        name = name.replace(' ', '_')
        return name

    def load_character_dialog(self):
        if self.unsaved_changes:
            reply = QMessageBox.question(self, 'Unsaved Changes',"Unsaved changes. Save before loading another?",
                                           QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel, QMessageBox.Save)
            if reply == QMessageBox.Save:
                if not self.save_character_data_ui(): return
            elif reply == QMessageBox.Cancel: return
        options = QFileDialog.Options()
        filepath, _ = QFileDialog.getOpenFileName(self, "Load Character JSON", CHARACTERS_DIR, "JSON Files (*.json)", options=options)
        if filepath:
            self.load_character_data_from_file(filepath)

    def load_character_data_from_file(self, filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            self.current_character_data = data
            self.current_character_filepath = filepath
            self.tab_widget.setEnabled(True)
            char_name_from_json = data.get("name", "Unknown Character")
            print(f"DEBUG: Loading character: '{char_name_from_json}' from {filepath}")
            self.title_label.setText(f"Rivals Data Forge - Editing: {char_name_from_json}")
            self.char_name_label.setText(char_name_from_json) # Set text for the main display
            icon_filename_part = self._clean_for_filename(char_name_from_json)
            icon_filename = f"{icon_filename_part}_Icon.webp"
            icon_path = os.path.join(IMAGES_DIR, icon_filename)
            print(f"DEBUG: Icon attempt: Name='{char_name_from_json}', Cleaned='{icon_filename_part}', Path='{icon_path}'")
            if os.path.exists(icon_path):
                icon_pixmap = QPixmap(icon_path)
                self.char_icon_label.setPixmap(icon_pixmap.scaled(80, 80, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            else:
                self.char_icon_label.setText("No Icon"); print(f"DEBUG: Icon NOT FOUND: {icon_path}")
            char_colors = self.character_color_pools.get(char_name_from_json, [])
            primary_color = char_colors[0] if char_colors else "#0078D7"
            secondary_color = char_colors[1] if len(char_colors) > 1 else self.lighten_color(primary_color, 30)
            print(f"DEBUG: Colors for {char_name_from_json}: Primary={primary_color}, Secondary={secondary_color}")
            self.apply_character_theme_styles(primary_color, secondary_color)
            self.character_display_widget.setVisible(True)
            self.main_content_stack.setCurrentWidget(self.tab_widget)
            self.save_button.setEnabled(False); self.unsaved_changes = False
            self.ability_forms.clear(); self.input_widgets_ability_forms.clear()
            while self.ability_form_stack.count() > 1:
                widget_to_remove = self.ability_form_stack.widget(1)
                self.ability_form_stack.removeWidget(widget_to_remove)
                widget_to_remove.deleteLater()
            self.populate_ui_from_data()
            self.populate_ability_selector()
            self.statusBar().showMessage(f"Loaded: {char_name_from_json}", 5000)
            QApplication.processEvents()
        except Exception as e:
            print(f"ERROR in load_character_data_from_file: {e}")
            self.character_display_widget.setVisible(False)
            self.main_content_stack.setCurrentWidget(self.welcome_widget)
            self.tab_widget.setEnabled(False)
            self.statusBar().showMessage(f"Error loading file: {e}")
            QMessageBox.critical(self, "Load Error", f"Could not load character data from {filepath}.\nError: {e}")
            self.current_character_data = None; self.current_character_filepath = None
            self.title_label.setText("Rivals Data Forge")
            self.char_name_label.setText("No Character Loaded")
            self.char_name_label.setStyleSheet(f"font-family: '{self.app_font_family}'; font-size: 20pt; font-weight: bold; padding-left: 10px; color: #E0E0E0;")
            self.char_icon_label.clear(); self.ability_selector_list.clear()
            self.setStyleSheet(self.base_stylesheet)

    def get_contrasting_text_color(self, hex_color):
        hex_color = hex_color.lstrip('#')
        if len(hex_color) != 6: return "#FFFFFF"
        try:
            r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
            brightness = (0.299 * r + 0.587 * g + 0.114 * b)
            return "#000000" if brightness > 128 else "#FFFFFF"
        except ValueError: return "#FFFFFF"

    def lighten_color(self, hex_color, percent):
        hex_color = hex_color.lstrip('#')
        if len(hex_color) != 6: return f"#{hex_color}"
        try:
            rgb = [int(hex_color[i:i+2], 16) for i in (0, 2, 4)]
            for i in range(3):
                val = rgb[i]; val = int(val * (1 + percent / 100.0)); val = max(0, min(255, val)); rgb[i] = val
            return f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"
        except ValueError: return f"#{hex_color}"
    
    def populate_ui_from_data(self):
        if not self.current_character_data: return
        self.disconnect_all_input_signals()
        self.identity_id_value.setText(self.current_character_data.get("character_id", "N/A"))
        self.identity_name_edit.setText(self.current_character_data.get("name", "")) # For the QLineEdit
        role = self.current_character_data.get("role", "Unknown")
        if role in self.roles: self.identity_role_combo.setCurrentText(role)
        else: self.identity_role_combo.setCurrentText("Unknown")
        self.identity_release_version_edit.setText(self.current_character_data.get("release_version", ""))
        stats_data = self.current_character_data.get("stats_basic", self.current_character_data.get("stats", {}))
        def safe_set_spinbox(spinbox, value, default=0, is_float=False):
            final_value = default
            if value is not None:
                try: final_value = float(value) if is_float else int(value)
                except (ValueError, TypeError): pass
            spinbox.setValue(final_value)
        safe_set_spinbox(self.stats_health_spin, stats_data.get("health"))
        safe_set_spinbox(self.stats_armor_spin, stats_data.get("armor"))
        safe_set_spinbox(self.stats_shields_spin, stats_data.get("shields_regenerating", stats_data.get("shields")))
        speed_str = str(stats_data.get("speed_mps", stats_data.get("speed", "0")) or "0")
        speed_val_to_set = 0.0
        try: speed_val_to_set = float(speed_str.replace("m/s", "").strip())
        except: pass
        safe_set_spinbox(self.stats_speed_spin, speed_val_to_set, is_float=True)
        safe_set_spinbox(self.stats_difficulty_spin, stats_data.get("difficulty_rating", stats_data.get("difficulty")))
        self.stats_resource_type_edit.setText(stats_data.get("resource_type") or "")
        resource_max_val = stats_data.get("resource_max", stats_data.get("resource_maximum"))
        safe_set_spinbox(self.stats_resource_max_spin, resource_max_val if stats_data.get("resource_type") else 0)
        lore_data = self.current_character_data.get("lore", self.current_character_data.get("lore_details", {}))
        quotes_data = self.current_character_data.get("quotes", {})
        bio_quote = quotes_data.get("ingame_bio_quote", self.current_character_data.get("ingame_bio_quote", ""))
        official_quote = quotes_data.get("official_quote", self.current_character_data.get("official_quote", ""))
        self.lore_ingame_bio_quote_edit.setHtml(bio_quote)
        self.lore_official_quote_edit.setHtml(official_quote)
        bio_text = lore_data.get("ingame_bio_text", self.current_character_data.get("ingame_bio_text",""))
        official_desc = lore_data.get("official_description", self.current_character_data.get("official_description",""))
        self.lore_ingame_bio_text_edit.setHtml(bio_text)
        self.lore_official_description_edit.setHtml(official_desc)
        self.lore_real_name_edit.setText(lore_data.get("real_name",""))
        self.lore_aliases_edit.setText(", ".join(lore_data.get("aliases",[])))
        self.lore_birthplace_edit.setText(lore_data.get("birthplace",""))
        self.lore_gender_edit.setText(lore_data.get("gender",""))
        self.lore_eye_color_edit.setText(lore_data.get("eye_color",""))
        self.lore_hair_color_edit.setText(lore_data.get("hair_color",""))
        self.lore_affiliation_edit.setText(", ".join(lore_data.get("affiliation",[])))

        # --- Gameplay Strategy Tab Population ---
        gameplay_data = self.current_character_data.get("gameplay", {})
        strategy_overview_html_blob = gameplay_data.get("strategy_overview", "") # Existing blob
        # "Perfect" schema gameplay strategy data
        gameplay_strategy_structured = self.current_character_data.get("gameplay_strategy_structured", {})

        # Helper to get value: prefer structured, fallback to parsing blob (AI part later), then empty
        def get_gameplay_value(field_key, html_blob_content):
            if field_key in gameplay_strategy_structured:
                return gameplay_strategy_structured[field_key]
            # AI PLACEHOLDER: Parse html_blob_content to extract for field_key
            # For now, if it's overall_summary and blob exists, use blob, else empty
            if field_key == "overall_playstyle_summary_html" and html_blob_content and not gameplay_strategy_structured:
                 return html_blob_content # Temp: put full blob in first field if no structured data
            return "" # Default to empty for other fields or if no blob
        
        def get_gameplay_list_value(field_key, html_blob_content): # For list fields
            if field_key in gameplay_strategy_structured:
                return gameplay_strategy_structured[field_key]
            # AI PLACEHOLDER: Parse html_blob_content to extract list for field_key
            return []


        self.gs_overall_summary_edit.setHtml(get_gameplay_value("overall_playstyle_summary_html", strategy_overview_html_blob))
        self.gs_positioning_edit.setHtml(get_gameplay_value("positioning_philosophy_html", strategy_overview_html_blob))
        self.gs_resource_mgmt_edit.setHtml(get_gameplay_value("resource_management_tips_html", strategy_overview_html_blob))
        self.gs_ultimate_usage_edit.setHtml(get_gameplay_value("ultimate_usage_tips_html", strategy_overview_html_blob))
        self.gs_synergies_edit.setHtml(get_gameplay_value("synergies_team_play_html", strategy_overview_html_blob))

        self.populate_list_widget_html(self.gs_strengths_list, get_gameplay_list_value("strengths_list_html", strategy_overview_html_blob))
        self.populate_list_widget_html(self.gs_weaknesses_list, get_gameplay_list_value("weaknesses_list_html", strategy_overview_html_blob))
        self.populate_list_widget_html(self.gs_advanced_tips_list, get_gameplay_list_value("advanced_tips_html", strategy_overview_html_blob))
        self.populate_key_combos_list(self.gs_key_combos_list, get_gameplay_list_value("key_combos_detailed", strategy_overview_html_blob))

        matchup_data = gameplay_strategy_structured.get("matchup_considerations", {})
        # AI PLACEHOLDER for parsing matchup from blob if matchup_data is empty
        self.gs_match_fav_arch_edit.setHtml(matchup_data.get("favorable_against_archetypes_html", ""))
        self.gs_match_fav_hero_edit.setHtml(matchup_data.get("favorable_against_specific_heroes_html", ""))
        self.gs_match_cha_arch_edit.setHtml(matchup_data.get("challenging_against_archetypes_html", ""))
        self.gs_match_cha_hero_edit.setHtml(matchup_data.get("challenging_against_specific_heroes_html", ""))

        char_name = self.current_character_data.get("name", "Unknown Character")
        char_colors = self.character_color_pools.get(char_name, [])
        primary_color = char_colors[0] if char_colors else "#0078D7"
        secondary_color = char_colors[1] if len(char_colors) > 1 else self.lighten_color(primary_color, 30)
        self.apply_character_theme_styles(primary_color, secondary_color)
        QApplication.processEvents()
        self.connect_all_input_signals()
        self.unsaved_changes = False
        self.save_button.setEnabled(False)

    def setup_gameplay_strategy_tab(self):
        gameplay_content_widget = QWidget()
        main_gameplay_layout = QVBoxLayout(gameplay_content_widget)
        main_gameplay_layout.setSpacing(15)
        self.input_widgets_gameplay = []

        form_layout = QFormLayout()
        form_layout.setSpacing(10)
        form_layout.setLabelAlignment(Qt.AlignTop | Qt.AlignRight) # Align labels top-right

        # Overall Strategy Section
        overall_label = QLabel("Overall Strategy"); overall_label.setObjectName("SectionHeaderLabel")
        self.themed_labels.append((overall_label, "secondary"))
        main_gameplay_layout.addWidget(overall_label)
        
        self.gs_overall_summary_edit = QTextEdit(); self.gs_overall_summary_edit.setAcceptRichText(True); self.gs_overall_summary_edit.setPlaceholderText("Describe the general playstyle, core role, and unique aspects..."); self.gs_overall_summary_edit.setMinimumHeight(120)
        form_layout.addRow("Overall Playstyle Summary:", self.gs_overall_summary_edit); self.input_widgets_gameplay.append(self.gs_overall_summary_edit)
        
        self.gs_positioning_edit = QTextEdit(); self.gs_positioning_edit.setAcceptRichText(True); self.gs_positioning_edit.setPlaceholderText("Ideal positioning, map awareness, flanking routes..."); self.gs_positioning_edit.setMinimumHeight(100)
        form_layout.addRow("Positioning Philosophy:", self.gs_positioning_edit); self.input_widgets_gameplay.append(self.gs_positioning_edit)

        self.gs_resource_mgmt_edit = QTextEdit(); self.gs_resource_mgmt_edit.setAcceptRichText(True); self.gs_resource_mgmt_edit.setPlaceholderText("Tips for managing any unique resources, cooldowns..."); self.gs_resource_mgmt_edit.setMinimumHeight(80)
        form_layout.addRow("Resource Management:", self.gs_resource_mgmt_edit); self.input_widgets_gameplay.append(self.gs_resource_mgmt_edit)

        self.gs_ultimate_usage_edit = QTextEdit(); self.gs_ultimate_usage_edit.setAcceptRichText(True); self.gs_ultimate_usage_edit.setPlaceholderText("Best scenarios, timing, and impact of the ultimate ability..."); self.gs_ultimate_usage_edit.setMinimumHeight(100)
        form_layout.addRow("Ultimate Usage Tips:", self.gs_ultimate_usage_edit); self.input_widgets_gameplay.append(self.gs_ultimate_usage_edit)

        self.gs_synergies_edit = QTextEdit(); self.gs_synergies_edit.setAcceptRichText(True); self.gs_synergies_edit.setPlaceholderText("How this character works with others, team compositions..."); self.gs_synergies_edit.setMinimumHeight(100)
        form_layout.addRow("Synergies & Team Play:", self.gs_synergies_edit); self.input_widgets_gameplay.append(self.gs_synergies_edit)
        main_gameplay_layout.addLayout(form_layout)

        # Key Combos Section
        self.gs_key_combos_group = QGroupBox("Key Combos (Detailed)")
        self.gs_key_combos_group.setObjectName("SectionHeaderLabel") # Use for styling
        self.themed_labels.append((self.gs_key_combos_group, "secondary")) # Theme the groupbox title
        key_combos_layout = QVBoxLayout()
        self.gs_key_combos_list = QListWidget()
        key_combos_layout.addWidget(self.gs_key_combos_list)
        combo_btn_layout = QHBoxLayout()
        add_combo_btn = QPushButton("Add Combo"); add_combo_btn.clicked.connect(lambda: self.add_key_combo_item())
        edit_combo_btn = QPushButton("Edit Combo"); edit_combo_btn.clicked.connect(lambda: self.edit_key_combo_item())
        remove_combo_btn = QPushButton("Remove Combo"); remove_combo_btn.clicked.connect(lambda: self.remove_list_item(self.gs_key_combos_list))
        combo_btn_layout.addWidget(add_combo_btn); combo_btn_layout.addWidget(edit_combo_btn); combo_btn_layout.addWidget(remove_combo_btn)
        key_combos_layout.addLayout(combo_btn_layout)
        self.gs_key_combos_group.setLayout(key_combos_layout)
        main_gameplay_layout.addWidget(self.gs_key_combos_group)
        # self.input_widgets_gameplay.append(self.gs_key_combos_list) # QListWidget itself doesn't trigger textChanged

        # Strengths, Weaknesses, Advanced Tips (as list editors)
        self.gs_strengths_list, strengths_group = self._create_list_editor_group("Strengths (HTML List)", "Add Strength", self.input_widgets_gameplay)
        self.themed_labels.append((strengths_group, "secondary"))
        main_gameplay_layout.addWidget(strengths_group)

        self.gs_weaknesses_list, weaknesses_group = self._create_list_editor_group("Weaknesses (HTML List)", "Add Weakness", self.input_widgets_gameplay)
        self.themed_labels.append((weaknesses_group, "secondary"))
        main_gameplay_layout.addWidget(weaknesses_group)
        
        self.gs_advanced_tips_list, adv_tips_group = self._create_list_editor_group("Advanced Tips (HTML List)", "Add Tip", self.input_widgets_gameplay)
        self.themed_labels.append((adv_tips_group, "secondary"))
        main_gameplay_layout.addWidget(adv_tips_group)

        # Matchup Considerations Section
        matchup_group = QGroupBox("Matchup Considerations"); matchup_group.setObjectName("SectionHeaderLabel")
        self.themed_labels.append((matchup_group, "secondary"))
        matchup_layout = QFormLayout(matchup_group)
        matchup_layout.setSpacing(10); matchup_layout.setLabelAlignment(Qt.AlignTop | Qt.AlignRight)

        self.gs_match_fav_arch_edit = QTextEdit(); self.gs_match_fav_arch_edit.setAcceptRichText(True); self.gs_match_fav_arch_edit.setPlaceholderText("Archetypes this character is strong against..."); self.gs_match_fav_arch_edit.setMinimumHeight(80)
        matchup_layout.addRow("Favorable vs Archetypes:", self.gs_match_fav_arch_edit); self.input_widgets_gameplay.append(self.gs_match_fav_arch_edit)
        self.gs_match_fav_hero_edit = QTextEdit(); self.gs_match_fav_hero_edit.setAcceptRichText(True); self.gs_match_fav_hero_edit.setPlaceholderText("Specific heroes this character counters..."); self.gs_match_fav_hero_edit.setMinimumHeight(80)
        matchup_layout.addRow("Favorable vs Heroes:", self.gs_match_fav_hero_edit); self.input_widgets_gameplay.append(self.gs_match_fav_hero_edit)
        self.gs_match_cha_arch_edit = QTextEdit(); self.gs_match_cha_arch_edit.setAcceptRichText(True); self.gs_match_cha_arch_edit.setPlaceholderText("Archetypes this character struggles against..."); self.gs_match_cha_arch_edit.setMinimumHeight(80)
        matchup_layout.addRow("Challenging vs Archetypes:", self.gs_match_cha_arch_edit); self.input_widgets_gameplay.append(self.gs_match_cha_arch_edit)
        self.gs_match_cha_hero_edit = QTextEdit(); self.gs_match_cha_hero_edit.setAcceptRichText(True); self.gs_match_cha_hero_edit.setPlaceholderText("Specific heroes that counter this character..."); self.gs_match_cha_hero_edit.setMinimumHeight(80)
        matchup_layout.addRow("Challenging vs Heroes:", self.gs_match_cha_hero_edit); self.input_widgets_gameplay.append(self.gs_match_cha_hero_edit)
        main_gameplay_layout.addWidget(matchup_group)

        main_gameplay_layout.addStretch() # Push content to the top
        self.tab_gameplay_scroll.setWidget(gameplay_content_widget)

    def _create_list_editor_group(self, title, add_button_text, input_widget_list_ref):
        group_box = QGroupBox(title)
        # group_box.setObjectName("SectionHeaderLabel") # Already handled by themed_labels
        layout = QVBoxLayout()
        list_widget = QListWidget()
        # input_widget_list_ref.append(list_widget) # QListWidget itself doesn't fire textChanged
        
        # Connect itemChanged for QListWidget if items become editable directly
        # list_widget.itemChanged.connect(self.mark_unsaved_changes)

        btn_layout = QHBoxLayout()
        add_btn = QPushButton(add_button_text)
        edit_btn = QPushButton("Edit Entry")
        remove_btn = QPushButton("Remove Entry")

        add_btn.clicked.connect(lambda checked, lw=list_widget: self.add_list_item_html(lw))
        edit_btn.clicked.connect(lambda checked, lw=list_widget: self.edit_list_item_html(lw))
        remove_btn.clicked.connect(lambda checked, lw=list_widget: self.remove_list_item(lw))

        btn_layout.addWidget(add_btn); btn_layout.addWidget(edit_btn); btn_layout.addWidget(remove_btn)
        layout.addWidget(list_widget)
        layout.addLayout(btn_layout)
        group_box.setLayout(layout)
        return list_widget, group_box

    def add_list_item_html(self, list_widget):
        dialog = ListEntryDialog(self, title=f"Add New Entry for {list_widget.parentWidget().title()}")
        if dialog.exec_() == QDialog.Accepted:
            html_content = dialog.get_text()
            if html_content.strip():
                item = QListWidgetItem(self.strip_html_for_display(html_content, 50)) # Show snippet
                item.setData(Qt.UserRole, html_content) # Store full HTML
                list_widget.addItem(item)
                self.mark_unsaved_changes()

    def edit_list_item_html(self, list_widget):
        current_item = list_widget.currentItem()
        if current_item:
            full_html_content = current_item.data(Qt.UserRole)
            dialog = ListEntryDialog(self, title=f"Edit Entry for {list_widget.parentWidget().title()}", current_text=full_html_content)
            if dialog.exec_() == QDialog.Accepted:
                new_html_content = dialog.get_text()
                current_item.setText(self.strip_html_for_display(new_html_content, 50))
                current_item.setData(Qt.UserRole, new_html_content)
                self.mark_unsaved_changes()

    def add_key_combo_item(self):
        dialog = ComboEntryDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            combo_data = dialog.get_data()
            if combo_data["name"].strip():
                display_text = f"{combo_data['name']}: {self.strip_html_for_display(combo_data['sequence_description_html'], 30)}"
                item = QListWidgetItem(display_text)
                item.setData(Qt.UserRole, combo_data)
                self.gs_key_combos_list.addItem(item)
                self.mark_unsaved_changes()

    def edit_key_combo_item(self):
        current_item = self.gs_key_combos_list.currentItem()
        if current_item:
            combo_data = current_item.data(Qt.UserRole)
            dialog = ComboEntryDialog(self, combo_data=combo_data)
            if dialog.exec_() == QDialog.Accepted:
                new_combo_data = dialog.get_data()
                display_text = f"{new_combo_data['name']}: {self.strip_html_for_display(new_combo_data['sequence_description_html'], 30)}"
                current_item.setText(display_text)
                current_item.setData(Qt.UserRole, new_combo_data)
                self.mark_unsaved_changes()
                
    def remove_list_item(self, list_widget):
        current_item = list_widget.currentItem()
        if current_item:
            row = list_widget.row(current_item)
            list_widget.takeItem(row)
            self.mark_unsaved_changes()
            del current_item

    def strip_html_for_display(self, html_string, max_len=50):
        if not html_string: return ""
        # Basic HTML tag stripping
        text = re.sub(r'<[^>]+>', '', html_string)
        text = text.replace('&nbsp;', ' ').strip()
        return (text[:max_len] + '...') if len(text) > max_len else text

    def populate_list_widget_html(self, list_widget, data_list):
        list_widget.clear()
        if data_list:
            for html_content in data_list:
                item = QListWidgetItem(self.strip_html_for_display(html_content, 50))
                item.setData(Qt.UserRole, html_content)
                list_widget.addItem(item)

    def populate_key_combos_list(self, list_widget, combos_data_list):
        list_widget.clear()
        if combos_data_list:
            for combo_data in combos_data_list:
                display_text = f"{combo_data.get('name', 'Unnamed Combo')}: {self.strip_html_for_display(combo_data.get('sequence_description_html', ''), 30)}"
                item = QListWidgetItem(display_text)
                item.setData(Qt.UserRole, combo_data)
                list_widget.addItem(item)

    def get_list_widget_data_html(self, list_widget):
        return [list_widget.item(i).data(Qt.UserRole) for i in range(list_widget.count())]

    def get_key_combos_data(self, list_widget):
        return [list_widget.item(i).data(Qt.UserRole) for i in range(list_widget.count())]


    def disconnect_all_input_signals(self):
        all_static_widgets = self.input_widgets_identity + self.input_widgets_lore + self.input_widgets_gameplay
        for widget in all_static_widgets:
            try:
                if isinstance(widget, (QLineEdit, QTextEdit)): widget.textChanged.disconnect()
                elif isinstance(widget, (QSpinBox, QDoubleSpinBox)): widget.valueChanged.disconnect()
                elif isinstance(widget, QComboBox): widget.currentIndexChanged.disconnect()
            except TypeError: pass
            except AttributeError: pass
        for form_id in list(self.input_widgets_ability_forms.keys()):
            self.disconnect_signals_for_form(form_id)
        # Disconnect list widget itemChanged if they were connected
        for lw in [self.gs_strengths_list, self.gs_weaknesses_list, self.gs_advanced_tips_list, self.gs_key_combos_list]:
            try: lw.itemChanged.disconnect(self.mark_unsaved_changes) # Assuming this was connected
            except: pass


    def connect_all_input_signals(self):
        editable_identity_widgets = [w for w in self.input_widgets_identity if not (isinstance(w, QLineEdit) and w.isReadOnly()) and not (isinstance(w, QComboBox) and not w.isEnabled())]
        for widget in editable_identity_widgets + self.input_widgets_lore + self.input_widgets_gameplay:
            try:
                if isinstance(widget, QLineEdit): widget.textChanged.connect(self.mark_unsaved_changes)
                elif isinstance(widget, QTextEdit): widget.textChanged.connect(self.mark_unsaved_changes)
                elif isinstance(widget, (QSpinBox, QDoubleSpinBox)): widget.valueChanged.connect(self.mark_unsaved_changes)
                elif isinstance(widget, QComboBox): widget.currentIndexChanged.connect(self.mark_unsaved_changes)
            except TypeError: pass # Already connected
        current_list_item = self.ability_selector_list.currentItem()
        if current_list_item:
            item_data = current_list_item.data(Qt.UserRole)
            if item_data:
                form_id = self._get_form_id_from_item_data(item_data)
                self.connect_signals_for_form(form_id)
        # Connect list widget itemChanged if they are made directly editable (not the case with current dialog approach)
        # For now, add/edit/remove buttons will call mark_unsaved_changes directly.


    def disconnect_signals_for_form(self, form_id):
        if form_id in self.input_widgets_ability_forms:
            for widget in self.input_widgets_ability_forms[form_id]:
                try:
                    if isinstance(widget, (QLineEdit, QTextEdit)): widget.textChanged.disconnect()
                    elif isinstance(widget, (QSpinBox, QDoubleSpinBox)): widget.valueChanged.disconnect()
                    elif isinstance(widget, QComboBox): widget.currentIndexChanged.disconnect()
                except TypeError: pass
                except AttributeError: pass

    def connect_signals_for_form(self, form_id):
        if form_id in self.input_widgets_ability_forms:
            for widget in self.input_widgets_ability_forms[form_id]:
                try:
                    if isinstance(widget, (QLineEdit, QTextEdit)): widget.textChanged.connect(self.mark_unsaved_changes)
                    elif isinstance(widget, (QSpinBox, QDoubleSpinBox)): widget.valueChanged.connect(self.mark_unsaved_changes)
                    elif isinstance(widget, QComboBox): widget.currentIndexChanged.connect(self.mark_unsaved_changes)
                except TypeError: pass
                except AttributeError: pass

    def mark_unsaved_changes(self):
        if not self.tab_widget.isEnabled(): return
        self.unsaved_changes = True
        self.save_button.setEnabled(True)
        self.statusBar().showMessage("Unsaved changes.", 3000)

    def save_character_data_ui(self):
        if not self.current_character_filepath or not self.current_character_data:
            QMessageBox.warning(self, "Save Error", "No character data loaded to save.")
            return False
        self.gather_data_from_ui()
        try:
            backup_filepath = self.current_character_filepath + ".bak"
            if os.path.exists(self.current_character_filepath):
                if os.path.exists(backup_filepath): os.remove(backup_filepath)
                os.rename(self.current_character_filepath, backup_filepath)
                print(f"Backup created: {backup_filepath}")
            with open(self.current_character_filepath, 'w', encoding='utf-8') as f:
                json.dump(self.current_character_data, f, indent=2, ensure_ascii=False)
            self.statusBar().showMessage(f"Saved {os.path.basename(self.current_character_filepath)} successfully.", 5000)
            self.unsaved_changes = False; self.save_button.setEnabled(False)
            flag_file_path = os.path.join(CONFIG_DIR, "data_editor_update.flag")
            with open(flag_file_path, 'w') as f:
                f.write(f"updated: {self.current_character_data.get('name', 'Unknown')}")
            print(f"Update flag created: {flag_file_path}")
            return True
        except Exception as e:
            self.statusBar().showMessage(f"Error saving file: {e}")
            QMessageBox.critical(self, "Save Error", f"Could not save data to {self.current_character_filepath}.\nError: {e}")
            return False

    def gather_data_from_ui(self):
        if not self.current_character_data: return
        self.current_character_data["release_version"] = self.identity_release_version_edit.text()
        if "stats_basic" in self.current_character_data: target_stats_dict = self.current_character_data["stats_basic"]
        elif "stats" in self.current_character_data: target_stats_dict = self.current_character_data["stats"]
        else: target_stats_dict = {}; self.current_character_data["stats_basic"] = target_stats_dict
        target_stats_dict["health"] = self.stats_health_spin.value()
        target_stats_dict["armor"] = self.stats_armor_spin.value()
        target_stats_dict["shields_regenerating"] = self.stats_shields_spin.value()
        target_stats_dict["speed_mps"] = self.stats_speed_spin.value()
        target_stats_dict["difficulty_rating"] = self.stats_difficulty_spin.value() if self.stats_difficulty_spin.value() > 0 else None
        resource_type = self.stats_resource_type_edit.text()
        if resource_type:
            target_stats_dict["resource_type"] = resource_type
            target_stats_dict["resource_max"] = self.stats_resource_max_spin.value()
        else:
            target_stats_dict.pop("resource_type", None); target_stats_dict.pop("resource_max", None)
        if "lore" in self.current_character_data: target_lore_dict = self.current_character_data["lore"]
        elif "lore_details" in self.current_character_data: target_lore_dict = self.current_character_data["lore_details"]
        elif "background" in self.current_character_data: target_lore_dict = self.current_character_data["background"]
        else: target_lore_dict = {}; self.current_character_data["lore"] = target_lore_dict
        self.current_character_data["ingame_bio_quote"] = self.lore_ingame_bio_quote_edit.toHtml()
        self.current_character_data["official_quote"] = self.lore_official_quote_edit.toHtml()
        target_lore_dict["ingame_bio_text"] = self.lore_ingame_bio_text_edit.toHtml()
        target_lore_dict["official_description"] = self.lore_official_description_edit.toHtml()
        target_lore_dict["real_name"] = self.lore_real_name_edit.text() or None
        target_lore_dict["aliases"] = [a.strip() for a in self.lore_aliases_edit.text().split(',') if a.strip()]
        target_lore_dict["birthplace"] = self.lore_birthplace_edit.text() or None
        target_lore_dict["gender"] = self.lore_gender_edit.text() or None
        target_lore_dict["eye_color"] = self.lore_eye_color_edit.text() or None
        target_lore_dict["hair_color"] = self.lore_hair_color_edit.text() or None
        target_lore_dict["affiliation"] = [a.strip() for a in self.lore_affiliation_edit.text().split(',') if a.strip()]
        if self.current_character_data:
            for form_id, input_fields_list in self.input_widgets_ability_forms.items():
                item_data = None
                for i in range(self.ability_selector_list.count()):
                    list_item_widget = self.ability_selector_list.item(i)
                    if self._get_form_id_from_item_data(list_item_widget.data(Qt.UserRole)) == form_id:
                        item_data = list_item_widget.data(Qt.UserRole); break
                if item_data and input_fields_list:
                    source_key = item_data.get("source_key"); index = item_data.get("index")
                    original_ability_data = None
                    if source_key == "abilities" and index is not None and index < len(self.current_character_data.get("abilities",[])): original_ability_data = self.current_character_data["abilities"][index]
                    elif source_key == "ultimate": original_ability_data = self.current_character_data.get("ultimate",{})
                    elif source_key == "passives" and index is not None and index < len(self.current_character_data.get("passives",[])): original_ability_data = self.current_character_data["passives"][index]
                    if original_ability_data is not None:
                        try:
                            original_ability_data["name"] = input_fields_list[0].text()
                            original_ability_data["description"] = input_fields_list[1].toPlainText()
                            original_ability_data["keybind"] = input_fields_list[2].text() or None
                            original_ability_data["cooldown"] = input_fields_list[3].text() or None
                        except IndexError: print(f"Warning: Mismatch saving ability form fields for {form_id}.")
                        except Exception as e: print(f"Error processing data for ability form {form_id}: {e}")
        
        # --- Gameplay Strategy Data Gathering ---
        gameplay_strategy_structured = {
            "overall_playstyle_summary_html": self.gs_overall_summary_edit.toHtml(),
            "positioning_philosophy_html": self.gs_positioning_edit.toHtml(),
            "resource_management_tips_html": self.gs_resource_mgmt_edit.toHtml(),
            "ultimate_usage_tips_html": self.gs_ultimate_usage_edit.toHtml(),
            "synergies_team_play_html": self.gs_synergies_edit.toHtml(),
            "key_combos_detailed": self.get_key_combos_data(self.gs_key_combos_list),
            "strengths_list_html": self.get_list_widget_data_html(self.gs_strengths_list),
            "weaknesses_list_html": self.get_list_widget_data_html(self.gs_weaknesses_list),
            "advanced_tips_html": self.get_list_widget_data_html(self.gs_advanced_tips_list),
            "matchup_considerations": {
                "favorable_against_archetypes_html": self.gs_match_fav_arch_edit.toHtml(),
                "favorable_against_specific_heroes_html": self.gs_match_fav_hero_edit.toHtml(),
                "challenging_against_archetypes_html": self.gs_match_cha_arch_edit.toHtml(),
                "challenging_against_specific_heroes_html": self.gs_match_cha_hero_edit.toHtml()
            }
        }
        self.current_character_data["gameplay_strategy_structured"] = gameplay_strategy_structured

        # --- Improved Placeholder for Re-assembling gameplay.strategy_overview HTML blob ---
        import re
        html_parts = []

        def add_section_html(title, content_html):
            if content_html and content_html.strip() and content_html.lower() != "<!doctype html public \"-//w3c//dtd html 4.0 transitional//en\">\n<html>\n<head>\n<meta http-equiv=\"content-type\" content=\"text/html; charset=utf-8\">\n<title></title>\n<meta name=\"generator\" content=\"libreoffice 24.2.2.2 (linux)\">\n<meta name=\"created\" content=\"0;0\">\n<meta name=\"changed\" content=\"0;0\">\n<style type=\"text/css\">\n<!--\n@page { margin: 2cm }\n\t\tp { margin-bottom: 0.25cm; line-height: 115% }\n\t\ta:link { so-language: zxx }\n-->\n</style>\n</head>\n<body>\n<p><br><br>\n</p>\n</body>\n</html>".lower().strip():
                clean_content = content_html
                boilerplate_start = "<!doctype html"
                boilerplate_end = "</body>\n</html>"
                if clean_content.lower().strip().startswith(boilerplate_start.lower()) and \
                   clean_content.lower().strip().endswith(boilerplate_end.lower()):
                    body_start_index = clean_content.lower().find("<body>")
                    body_end_index = clean_content.lower().rfind("</body>")
                    if body_start_index != -1 and body_end_index != -1:
                        clean_content = clean_content[body_start_index + len("<body>") : body_end_index].strip()
                        if not clean_content or clean_content == "<p><br><br>\n</p>":
                            return
                html_parts.append(f"<p><b><u>{title}:</u></b><br>\n{clean_content}</p>")

        def add_list_section_html(title, list_items_html):
            if list_items_html:
                items_html = "".join([f"<li>{item}</li>" for item in list_items_html if item.strip()])
                if items_html:
                    html_parts.append(f"<p><b><u>{title}:</u></b><br>\n<ul>{items_html}</ul></p>")
        
        def add_combo_section_html(title, combos_data):
            if combos_data:
                combo_html_parts = []
                for combo in combos_data:
                    combo_part = f"<li><b>{combo.get('name', 'Unnamed Combo')}</b>"
                    details = []
                    if combo.get('sequence_description_html', '').strip(): details.append(f"<p><em>Sequence:</em> {combo['sequence_description_html']}</p>")
                    if combo.get('purpose_html', '').strip(): details.append(f"<p><em>Purpose:</em> {combo['purpose_html']}</p>")
                    if combo.get('notes_html', '').strip(): details.append(f"<p><em>Notes:</em> {combo['notes_html']}</p>")
                    if details:
                        combo_part += "<ul>" + "".join([f"<li>{d}</li>" for d in details]) + "</ul>"
                    combo_part += "</li>"
                    combo_html_parts.append(combo_part)
                if combo_html_parts:
                    html_parts.append(f"<p><b><u>{title}:</u></b><br>\n<ul>{''.join(combo_html_parts)}</ul></p>")

        add_section_html("Overall Playstyle", gameplay_strategy_structured.get("overall_playstyle_summary_html"))
        add_section_html("Positioning Philosophy", gameplay_strategy_structured.get("positioning_philosophy_html"))
        add_section_html("Resource Management", gameplay_strategy_structured.get("resource_management_tips_html"))
        add_section_html("Ultimate Usage Tips", gameplay_strategy_structured.get("ultimate_usage_tips_html"))
        add_section_html("Synergies & Team Play", gameplay_strategy_structured.get("synergies_team_play_html"))

        add_combo_section_html("Key Combos & Ability Usage", gameplay_strategy_structured.get("key_combos_detailed"))
        
        add_list_section_html("Core Strengths", gameplay_strategy_structured.get("strengths_list_html"))
        add_list_section_html("Weaknesses", gameplay_strategy_structured.get("weaknesses_list_html"))
        add_list_section_html("Advanced Tips", gameplay_strategy_structured.get("advanced_tips_html"))

        mc = gameplay_strategy_structured.get("matchup_considerations", {})
        matchup_html_parts = []
        if mc.get("favorable_against_archetypes_html", "").strip():
            matchup_html_parts.append(f"<p><em>Favorable vs Archetypes:</em> {mc['favorable_against_archetypes_html']}</p>")
        if mc.get("favorable_against_specific_heroes_html", "").strip():
            matchup_html_parts.append(f"<p><em>Favorable vs Heroes:</em> {mc['favorable_against_specific_heroes_html']}</p>")
        if mc.get("challenging_against_archetypes_html", "").strip():
            matchup_html_parts.append(f"<p><em>Challenging vs Archetypes:</em> {mc['challenging_against_archetypes_html']}</p>")
        if mc.get("challenging_against_specific_heroes_html", "").strip():
            matchup_html_parts.append(f"<p><em>Challenging vs Heroes:</em> {mc['challenging_against_specific_heroes_html']}</p>")
        if matchup_html_parts:
            html_parts.append(f"<p><b><u>Matchup Considerations:</u></b><br>\n{''.join(matchup_html_parts)}</p>")

        # Fallback for gameplay.weaknesses if the dashboard reads it directly and not from strategy_overview
        plain_weaknesses_list = []
        for html_weakness in gameplay_strategy_structured.get("weaknesses_list_html", []):
            plain_text = re.sub(r'<[^>]+>', '', html_weakness).strip()
            if plain_text:
                plain_weaknesses_list.append(plain_text)

        final_html_blob = "\n".join(html_parts)
        if "gameplay" not in self.current_character_data:
            self.current_character_data["gameplay"] = {}
        self.current_character_data["gameplay"]["strategy_overview"] = final_html_blob
        self.current_character_data["gameplay"]["weaknesses"] = plain_weaknesses_list

        print("DEBUG: Generated strategy_overview blob (length):", len(final_html_blob))

    def closeEvent(self, event):
        if self.unsaved_changes:
            reply = QMessageBox.question(self, 'Exit Confirmation',
                                           "You have unsaved changes. Save before exiting?",
                                           QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel,
                                           QMessageBox.Cancel)
            if reply == QMessageBox.Save:
                if self.save_character_data_ui(): event.accept()
                else: event.ignore()
            elif reply == QMessageBox.Discard: event.accept()
            else: event.ignore()
        else: event.accept()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    mainWindow = DataForgeWindow()
    mainWindow.show()
    sys.exit(app.exec_())