# data_forge_main.py
import sys
import os
import json
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QLabel, QFileDialog, QTabWidget, QFormLayout,
                             QLineEdit, QTextEdit, QComboBox, QListWidget, QListWidgetItem, QMessageBox, 
                             QSpinBox, QDoubleSpinBox, QScrollArea, QStackedWidget,
                             QGroupBox) # Added QStackedWidget, QGroupBox
from PyQt5.QtGui import QPixmap, QMovie, QFont, QIcon, QFontDatabase
from PyQt5.QtCore import Qt, QSize

# --- Constants for Directories ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHARACTERS_DIR = os.path.join(BASE_DIR, "characters")
IMAGES_DIR = os.path.join(BASE_DIR, "images")
CONFIG_DIR = os.path.join(BASE_DIR, "config")
STYLES_DIR = os.path.join(BASE_DIR, "styles")

class DataForgeWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Rivals Data Forge")
        self.setGeometry(100, 100, 1350, 900) # Made wider for abilities tab
        self.current_character_data = None
        self.current_character_filepath = None
        self.unsaved_changes = False
        self.app_font_family = "Arial" 
        self.roles = ["Duelist", "Strategist", "Vanguard", "Unknown"]

        self.set_app_icon()
        self.load_custom_font()

        self.initUI()
        self.load_styles_qss()
        
        self.input_widgets_identity = []
        self.input_widgets_lore = []
        self.ability_forms = {}  # Key: e.g. "primary_fire_0", "ultimate"
        self.input_widgets_ability_forms = {}  # Key: same as above; Value: list of input widgets in that form

    def set_app_icon(self):
        # ... (same as before)
        app_icon_path = os.path.join(IMAGES_DIR, "Marvel Rivals Dashboard.ico")
        if os.path.exists(app_icon_path):
            self.setWindowIcon(QIcon(app_icon_path))
        else:
            print(f"App icon not found: {app_icon_path}")

    def load_custom_font(self):
        # ... (same as before)
        font_path = os.path.join(STYLES_DIR, "font", "Refrigerator Deluxe.otf")
        if os.path.exists(font_path):
            font_id = QFontDatabase.addApplicationFont(font_path)
            if font_id != -1:
                font_families = QFontDatabase.applicationFontFamilies(font_id)
                if font_families:
                    self.app_font_family = font_families[0]
                    QApplication.setFont(QFont(self.app_font_family, 10)) 
                    print(f"Custom font '{self.app_font_family}' loaded.")
                else:
                    print("Failed to get font family from loaded font.")
            else:
                print("Failed to load custom font (addApplicationFont returned -1).")
        else:
            print(f"Custom font not found at {font_path}")
        self.setFont(QFont(self.app_font_family, 10))

    def load_styles_qss(self):
        # ... (same as before)
        stylesheet_path = os.path.join(STYLES_DIR, "dark_theme.qss")
        if os.path.exists(stylesheet_path):
            with open(stylesheet_path, "r") as f:
                self.setStyleSheet(f.read())
            print("Stylesheet loaded.")
        else:
            print(f"Stylesheet not found at {stylesheet_path}")

    def initUI(self):
        # ... (Top Bar and Character Display Area mostly same as before) ...
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(10,10,10,10)

        top_bar_layout = QHBoxLayout()
        top_bar_layout.setSpacing(15)
        self.spidey_gif_label = QLabel()
        spidey_gif_path = os.path.join(IMAGES_DIR, "loading.gif")
        if os.path.exists(spidey_gif_path):
            self.spidey_movie = QMovie(spidey_gif_path); self.spidey_movie.setScaledSize(QSize(70, 70))
            self.spidey_gif_label.setMovie(self.spidey_movie); self.spidey_movie.start()
            top_bar_layout.addWidget(self.spidey_gif_label)
        else: top_bar_layout.addWidget(QLabel("GIF")) 
        self.title_label = QLabel("Rivals Data Forge"); self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setStyleSheet("font-size: 20pt; font-weight: bold;")
        top_bar_layout.addWidget(self.title_label, 1)
        self.load_button = QPushButton("Load Character"); self.load_button.clicked.connect(self.load_character_dialog)
        top_bar_layout.addWidget(self.load_button)
        self.save_button = QPushButton("Save Changes"); self.save_button.clicked.connect(self.save_character_data_ui)
        self.save_button.setEnabled(False); top_bar_layout.addWidget(self.save_button)
        self.main_layout.addLayout(top_bar_layout)

        character_display_layout = QHBoxLayout(); character_display_layout.setContentsMargins(0, 10, 0, 5)
        self.char_icon_label = QLabel(); self.char_icon_label.setFixedSize(80, 80); self.char_icon_label.setAlignment(Qt.AlignCenter)
        character_display_layout.addWidget(self.char_icon_label)
        self.char_name_label = QLabel("No Character Loaded")
        self.char_name_label.setStyleSheet(f"font-family: '{self.app_font_family}'; font-size: 18pt; font-weight: bold; padding-left: 10px;")
        character_display_layout.addWidget(self.char_name_label); character_display_layout.addStretch()
        self.main_layout.addLayout(character_display_layout)

        # --- Tab Widget ---
        self.tab_widget = QTabWidget()
        self.tab_widget.setEnabled(False)

        self.tab_identity_stats = QWidget()
        self.setup_identity_stats_tab()
        self.tab_widget.addTab(self.tab_identity_stats, "Identity & Stats")

        self.tab_lore_quotes = QScrollArea() 
        self.tab_lore_quotes.setWidgetResizable(True)
        self.setup_lore_quotes_tab()
        self.tab_widget.addTab(self.tab_lore_quotes, "Lore & Quotes")

        self.tab_abilities = QWidget() # This will now have a more complex layout
        self.setup_abilities_kit_tab()
        self.tab_widget.addTab(self.tab_abilities, "Abilities Kit")
        
        # ... (placeholders for other tabs remain same)
        self.tab_gameplay = QWidget()
        self.tab_widget.addTab(self.tab_gameplay, "Gameplay Strategy")
        self.tab_matchups_teamups = QWidget()
        self.tab_widget.addTab(self.tab_matchups_teamups, "Matchups & Team-Ups")
        self.tab_meta_balance = QWidget()
        self.tab_widget.addTab(self.tab_meta_balance, "Meta & Balance")


        self.main_layout.addWidget(self.tab_widget)
        self.statusBar().showMessage("Ready. Load a character to begin editing.")

    def setup_identity_stats_tab(self):
        widget_content = QWidget()
        layout = QFormLayout(widget_content) 
        layout.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        self.input_widgets_identity = [] 

        self.identity_id_value = QLineEdit()
        self.identity_id_value.setReadOnly(True)
        layout.addRow("Character ID (Read-only):", self.identity_id_value)

        self.identity_name_edit = QLineEdit()
        self.identity_name_edit.setReadOnly(True) # <<< CHANGED TO READ-ONLY
        layout.addRow("Name (Read-only):", self.identity_name_edit)
        # No longer add to self.input_widgets_identity for tracking if read-only

        self.identity_role_combo = QComboBox()
        self.identity_role_combo.addItems(self.roles)
        self.identity_role_combo.setEnabled(False) # <<< CHANGED TO DISABLED (effectively read-only)
        layout.addRow("Role (Read-only):", self.identity_role_combo)
        # No longer add to self.input_widgets_identity
        
        self.identity_release_version_edit = QLineEdit()
        layout.addRow("Release Version:", self.identity_release_version_edit)
        self.input_widgets_identity.append(self.identity_release_version_edit) # Still editable

        stats_group_label = QLabel("Basic Stats") # ... (rest of this method is same as before)
        stats_group_label.setStyleSheet("font-weight: bold; margin-top: 10px; margin-bottom: 5px;")
        layout.addRow(stats_group_label)
        self.stats_health_spin = QSpinBox(); self.stats_health_spin.setRange(0,9999); layout.addRow("Health:", self.stats_health_spin)
        self.input_widgets_identity.append(self.stats_health_spin)
        self.stats_armor_spin = QSpinBox(); self.stats_armor_spin.setRange(0,9999); layout.addRow("Armor:", self.stats_armor_spin)
        self.input_widgets_identity.append(self.stats_armor_spin)
        self.stats_shields_spin = QSpinBox(); self.stats_shields_spin.setRange(0,9999); layout.addRow("Regenerating Shields:", self.stats_shields_spin)
        self.input_widgets_identity.append(self.stats_shields_spin)
        self.stats_speed_spin = QDoubleSpinBox(); self.stats_speed_spin.setRange(0,99.9); self.stats_speed_spin.setDecimals(1); self.stats_speed_spin.setSuffix(" m/s")
        layout.addRow("Speed:", self.stats_speed_spin)
        self.input_widgets_identity.append(self.stats_speed_spin)
        self.stats_difficulty_spin = QSpinBox(); self.stats_difficulty_spin.setRange(0,5); layout.addRow("Difficulty Rating (0-5):", self.stats_difficulty_spin)
        self.input_widgets_identity.append(self.stats_difficulty_spin)
        self.stats_resource_type_edit = QLineEdit(); layout.addRow("Resource Type (e.g., Mana):", self.stats_resource_type_edit)
        self.input_widgets_identity.append(self.stats_resource_type_edit)
        self.stats_resource_max_spin = QSpinBox(); self.stats_resource_max_spin.setRange(0,99999); layout.addRow("Max Resource Value:", self.stats_resource_max_spin)
        self.input_widgets_identity.append(self.stats_resource_max_spin)
        layout.addRow(QLabel()); layout.setVerticalSpacing(10)
        self.tab_identity_stats.setLayout(layout)


    def setup_lore_quotes_tab(self):
        # ... (same as before)
        content_widget = QWidget()
        layout = QFormLayout(content_widget)
        layout.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        self.input_widgets_lore = []
        quotes_label = QLabel("Quotes"); quotes_label.setStyleSheet("font-weight: bold; margin-bottom: 5px;")
        layout.addRow(quotes_label)
        self.lore_ingame_bio_quote_edit = QTextEdit(); self.lore_ingame_bio_quote_edit.setPlaceholderText("Enter in-game bio quote..."); self.lore_ingame_bio_quote_edit.setFixedHeight(60)
        layout.addRow("In-Game Bio Quote:", self.lore_ingame_bio_quote_edit); self.input_widgets_lore.append(self.lore_ingame_bio_quote_edit)
        self.lore_official_quote_edit = QTextEdit(); self.lore_official_quote_edit.setPlaceholderText("Enter official quote..."); self.lore_official_quote_edit.setFixedHeight(60)
        layout.addRow("Official Quote:", self.lore_official_quote_edit); self.input_widgets_lore.append(self.lore_official_quote_edit)
        lore_details_label = QLabel("Lore Details"); lore_details_label.setStyleSheet("font-weight: bold; margin-top: 15px; margin-bottom: 5px;")
        layout.addRow(lore_details_label)
        self.lore_ingame_bio_text_edit = QTextEdit(); self.lore_ingame_bio_text_edit.setPlaceholderText("Enter in-game bio text..."); self.lore_ingame_bio_text_edit.setMinimumHeight(100)
        layout.addRow("In-Game Bio Text:", self.lore_ingame_bio_text_edit); self.input_widgets_lore.append(self.lore_ingame_bio_text_edit)
        self.lore_official_description_edit = QTextEdit(); self.lore_official_description_edit.setPlaceholderText("Enter official description..."); self.lore_official_description_edit.setMinimumHeight(100)
        layout.addRow("Official Description:", self.lore_official_description_edit); self.input_widgets_lore.append(self.lore_official_description_edit)
        self.lore_real_name_edit = QLineEdit(); layout.addRow("Real Name:", self.lore_real_name_edit); self.input_widgets_lore.append(self.lore_real_name_edit)
        self.lore_aliases_edit = QLineEdit(); self.lore_aliases_edit.setPlaceholderText("Comma-separated") 
        layout.addRow("Aliases (comma-sep):", self.lore_aliases_edit); self.input_widgets_lore.append(self.lore_aliases_edit)
        self.lore_birthplace_edit = QLineEdit(); layout.addRow("Birthplace:", self.lore_birthplace_edit); self.input_widgets_lore.append(self.lore_birthplace_edit)
        self.lore_gender_edit = QLineEdit(); layout.addRow("Gender:", self.lore_gender_edit); self.input_widgets_lore.append(self.lore_gender_edit)
        self.lore_eye_color_edit = QLineEdit(); layout.addRow("Eye Color:", self.lore_eye_color_edit); self.input_widgets_lore.append(self.lore_eye_color_edit)
        self.lore_hair_color_edit = QLineEdit(); layout.addRow("Hair Color:", self.lore_hair_color_edit); self.input_widgets_lore.append(self.lore_hair_color_edit)
        self.lore_affiliation_edit = QLineEdit(); self.lore_affiliation_edit.setPlaceholderText("Comma-separated")
        layout.addRow("Affiliation (comma-sep):", self.lore_affiliation_edit); self.input_widgets_lore.append(self.lore_affiliation_edit)
        layout.setVerticalSpacing(10); self.tab_lore_quotes.setWidget(content_widget)

    def setup_abilities_kit_tab(self):
        # Main layout for the "Abilities Kit" tab
        main_abilities_layout = QHBoxLayout(self.tab_abilities) # Use QHBoxLayout for side-by-side
        main_abilities_layout.setSpacing(10)

        # Left side: List of ability categories/specific abilities
        self.ability_selector_list = QListWidget()
        self.ability_selector_list.setFixedWidth(250) # Adjust width as needed
        # We will populate this list when a character is loaded
        self.ability_selector_list.currentItemChanged.connect(self.display_selected_ability_form)
        main_abilities_layout.addWidget(self.ability_selector_list)

        # Right side: StackedWidget to show the form for the selected ability
        self.ability_form_stack = QStackedWidget()
        main_abilities_layout.addWidget(self.ability_form_stack, 1) # Give it more stretch factor

        # Placeholder widget for when no ability is selected or for categories
        default_ability_widget = QWidget()
        default_layout = QVBoxLayout(default_ability_widget)
        default_layout.addWidget(QLabel("Select an ability or category from the left to edit."))
        default_layout.addStretch()
        self.ability_form_stack.addWidget(default_ability_widget)
        
        # We will dynamically add/remove widgets (forms) to self.ability_form_stack
        # and store references to their input fields for data gathering/population.

    def display_selected_ability_form(self, current_item, previous_item):
        if not current_item:
            self.ability_form_stack.setCurrentIndex(0)
            return

        item_data = current_item.data(Qt.UserRole)
        if not item_data:
            self.ability_form_stack.setCurrentIndex(0)
            return

        ability_key = item_data.get("key")
        ability_index = item_data.get("index")
        form_id = f"{ability_key}"
        if ability_index is not None:
            form_id += f"_{ability_index}"

        # Disconnect signals from previous form
        if previous_item:
            prev_item_data = previous_item.data(Qt.UserRole)
            if prev_item_data:
                prev_form_id = f"{prev_item_data.get('key')}"
                if prev_item_data.get('index') is not None:
                    prev_form_id += f"_{prev_item_data.get('index')}"
                self.disconnect_signals_for_form(prev_form_id)

        if form_id not in self.ability_forms:
            form_widget = QWidget()
            form_layout = QFormLayout(form_widget)

            # Get ability data for this form
            ability_data = None
            if ability_key and self.current_character_data and "abilities_kit" in self.current_character_data:
                kit_section = self.current_character_data["abilities_kit"].get(ability_key)
                if isinstance(kit_section, list) and ability_index is not None and ability_index < len(kit_section):
                    ability_data = kit_section[ability_index]
                elif isinstance(kit_section, dict):
                    ability_data = kit_section

            display_ability_name = ability_data.get("name", form_id.replace("_", " ").title()) if ability_data else form_id.replace("_", " ").title()
            form_layout.addRow(QLabel(f"<b>Editing: {display_ability_name}</b>"))

            name_edit = QLineEdit(ability_data.get("name", "") if ability_data else "")
            form_layout.addRow("Name:", name_edit)

            desc_edit = QTextEdit(ability_data.get("description_short", "") if ability_data else "")
            desc_edit.setPlaceholderText("Short description...")
            desc_edit.setFixedHeight(80)
            form_layout.addRow("Short Description:", desc_edit)

            self.ability_forms[form_id] = form_widget
            self.input_widgets_ability_forms[form_id] = [name_edit, desc_edit]
            self.ability_form_stack.addWidget(form_widget)

        form_to_display = self.ability_forms.get(form_id)
        if form_to_display:
            self.ability_form_stack.setCurrentWidget(form_to_display)
            self.connect_signals_for_form(form_id)
        else:
            self.ability_form_stack.setCurrentIndex(0)

    def create_and_populate_ability_form_fields(self, form_layout, ability_data, form_id):
        # Placeholder for future dynamic form building
        pass

    def disconnect_signals_for_form(self, form_id):
        if form_id in self.input_widgets_ability_forms:
            for widget in self.input_widgets_ability_forms[form_id]:
                try:
                    if isinstance(widget, (QLineEdit, QTextEdit)):
                        widget.textChanged.disconnect()
                    elif isinstance(widget, (QSpinBox, QDoubleSpinBox)):
                        widget.valueChanged.disconnect()
                    elif isinstance(widget, QComboBox):
                        widget.currentIndexChanged.disconnect()
                except TypeError:
                    pass
                except AttributeError:
                    pass

    def connect_signals_for_form(self, form_id):
        if form_id in self.input_widgets_ability_forms:
            for widget in self.input_widgets_ability_forms[form_id]:
                if isinstance(widget, (QLineEdit, QTextEdit)):
                    widget.textChanged.connect(self.mark_unsaved_changes)
                elif isinstance(widget, (QSpinBox, QDoubleSpinBox)):
                    widget.valueChanged.connect(self.mark_unsaved_changes)
                elif isinstance(widget, QComboBox):
                    widget.currentIndexChanged.connect(self.mark_unsaved_changes)

    def populate_ability_selector(self):
        self.ability_selector_list.clear()
        if not self.current_character_data or "abilities_kit" not in self.current_character_data:
            return

        kit = self.current_character_data["abilities_kit"]
        
        # Order of abilities in the selector
        ability_order = [
            ("primary_fire", "Primary Fire"), ("secondary_fire", "Secondary Fire"),
            ("ability_1", "Ability 1 (Shift)"), ("ability_2", "Ability 2 (E)"),
            ("ability_3", "Ability 3 (F)"), ("mobility_ability", "Mobility"),
            ("ultimate", "Ultimate"), ("passives", "Passives"), ("melee", "Melee")
        ]

        for key, display_name in ability_order:
            ability_data = kit.get(key)
            if ability_data: # If the key exists and is not None/empty
                if isinstance(ability_data, list) and ability_data: # For arrays like primary_fire, passives
                    for i, ab_item in enumerate(ability_data):
                        item_name = ab_item.get("name", f"{display_name} Mode {i+1}")
                        list_item = QListWidgetItem(f"{display_name}: {item_name}")
                        list_item.setData(Qt.UserRole, {"key": key, "index": i}) # Store key and index
                        self.ability_selector_list.addItem(list_item)
                elif isinstance(ability_data, dict) and ability_data.get("name"): # For single objects like ultimate, ability_1
                    item_name = ability_data.get("name", display_name)
                    list_item = QListWidgetItem(f"{display_name}: {item_name}")
                    list_item.setData(Qt.UserRole, {"key": key, "index": None}) # Store key, no index
                    self.ability_selector_list.addItem(list_item)
        
        if self.ability_selector_list.count() > 0:
            self.ability_selector_list.setCurrentRow(0) # Select the first item


    def load_character_dialog(self):
        # ... (same as before) ...
        if self.unsaved_changes:
            reply = QMessageBox.question(self, 'Unsaved Changes',
                                           "You have unsaved changes. Do you want to save before loading another character?",
                                           QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel,
                                           QMessageBox.Save)
            if reply == QMessageBox.Save:
                if not self.save_character_data_ui(): 
                    return 
            elif reply == QMessageBox.Cancel:
                return
        options = QFileDialog.Options()
        filepath, _ = QFileDialog.getOpenFileName(self, "Load Character JSON", CHARACTERS_DIR,
                                                  "JSON Files (*.json);;All Files (*)", options=options)
        if filepath:
            self.load_character_data_from_file(filepath)

    def load_character_data_from_file(self, filepath):
        # ... (Styling for char_name_label and icon loading same as before) ...
        try:
            with open(filepath, 'r', encoding='utf-8') as f: data = json.load(f)
            self.current_character_data = data; self.current_character_filepath = filepath
            char_name = data.get("name", "Unknown Character")
            self.title_label.setText(f"Rivals Data Forge - Editing: {char_name}")
            char_color = data.get("color_theme", "#FFFFFF"); self.char_name_label.setText(char_name)
            self.char_name_label.setStyleSheet(f"font-family: '{self.app_font_family}'; font-size: 18pt; font-weight: bold; padding-left: 10px; color: {char_color};")
            icon_filename = char_name.replace(" ", "_").replace("-","_") + "_Icon.webp"
            icon_path = os.path.join(IMAGES_DIR, icon_filename)
            if os.path.exists(icon_path):
                self.char_icon_label.setPixmap(QPixmap(icon_path).scaled(80, 80, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            else:
                self.char_icon_label.setPixmap(QPixmap()); self.char_icon_label.setText("No\nIcon"); print(f"Icon not found for {char_name}: {icon_path}")
            self.statusBar().showMessage(f"Loaded {os.path.basename(filepath)}. Make your edits.")
            self.tab_widget.setEnabled(True); self.save_button.setEnabled(False); self.unsaved_changes = False
            self.populate_ui_from_data()
            self.populate_ability_selector() # Populate ability list
        except Exception as e:
            # ... (error handling same)
            self.statusBar().showMessage(f"Error loading file: {e}")
            QMessageBox.critical(self, "Load Error", f"Could not load character data from {filepath}.\nError: {e}")
            self.current_character_data = None; self.current_character_filepath = None; self.tab_widget.setEnabled(False)
            self.title_label.setText("Rivals Data Forge"); self.char_name_label.setText("No Character Loaded")
            self.char_name_label.setStyleSheet(f"font-family: '{self.app_font_family}'; font-size: 18pt; font-weight: bold; padding-left: 10px;")
            self.char_icon_label.clear(); self.ability_selector_list.clear()


    def populate_ui_from_data(self):
        # ... (Identity & Stats, Lore & Quotes population same as before) ...
        if not self.current_character_data: return
        self.disconnect_all_input_signals()
        # Identity & Stats
        self.identity_id_value.setText(self.current_character_data.get("character_id", "N/A"))
        self.identity_name_edit.setText(self.current_character_data.get("name", "")) # Will be read-only
        role = self.current_character_data.get("role", "Unknown")
        self.identity_role_combo.setCurrentText(role if role in self.roles else "Unknown") # Will be disabled
        self.identity_release_version_edit.setText(self.current_character_data.get("release_version", ""))
        stats_basic = self.current_character_data.get("stats_basic", {})
        self.stats_health_spin.setValue(stats_basic.get("health",0)); self.stats_armor_spin.setValue(stats_basic.get("armor",0))
        self.stats_shields_spin.setValue(stats_basic.get("shields_regenerating",0))
        try: speed_val = float(stats_basic.get("speed_mps", "0.0") or 0.0)
        except: speed_val = 0.0
        self.stats_speed_spin.setValue(speed_val)
        self.stats_difficulty_spin.setValue(stats_basic.get("difficulty_rating",0))
        self.stats_resource_type_edit.setText(stats_basic.get("resource_type") or "")
        self.stats_resource_max_spin.setValue(stats_basic.get("resource_max") if stats_basic.get("resource_type") else 0)
        # Lore & Quotes
        lore_data = self.current_character_data.get("lore", {}); quotes_data = self.current_character_data.get("quotes", {})
        self.lore_ingame_bio_quote_edit.setHtml(quotes_data.get("ingame_bio_quote","")); self.lore_official_quote_edit.setHtml(quotes_data.get("official_quote",""))
        self.lore_ingame_bio_text_edit.setHtml(lore_data.get("ingame_bio_text","")); self.lore_official_description_edit.setHtml(lore_data.get("official_description",""))
        self.lore_real_name_edit.setText(lore_data.get("real_name","")); self.lore_aliases_edit.setText(", ".join(lore_data.get("aliases",[])))
        self.lore_birthplace_edit.setText(lore_data.get("birthplace","")); self.lore_gender_edit.setText(lore_data.get("gender",""))
        self.lore_eye_color_edit.setText(lore_data.get("eye_color","")); self.lore_hair_color_edit.setText(lore_data.get("hair_color",""))
        self.lore_affiliation_edit.setText(", ".join(lore_data.get("affiliation",[])))
        
        # --- TODO: Populate Abilities Kit Tab (Dynamic Form based on selection) ---
        # For now, the selector list is populated in load_character_data_from_file
        # and display_selected_ability_form shows a placeholder.

        QApplication.processEvents(); self.connect_all_input_signals()
        self.unsaved_changes = False; self.save_button.setEnabled(False)
        self.statusBar().showMessage(f"Data loaded for {self.current_character_data.get('name')}. Fields populated.", 5000)

    def disconnect_all_input_signals(self):
        # ... (same as before, ensure to add new widget lists here later) ...
        all_widgets_to_disconnect = self.input_widgets_identity + self.input_widgets_lore
        for widget in all_widgets_to_disconnect:
            try:
                if isinstance(widget, (QLineEdit, QTextEdit)): widget.textChanged.disconnect()
                elif isinstance(widget, (QSpinBox, QDoubleSpinBox)): widget.valueChanged.disconnect()
                elif isinstance(widget, QComboBox): widget.currentIndexChanged.disconnect()
            except (TypeError, AttributeError): pass
        # Disconnect signals for ability forms
        for form_id in list(self.input_widgets_ability_forms.keys()):
            self.disconnect_signals_for_form(form_id)

    def connect_all_input_signals(self):
        # ... (same as before, ensure to add new widget lists here later) ...
        # Identity (only editable ones)
        self.identity_release_version_edit.textChanged.connect(self.mark_unsaved_changes)
        for widget in self.input_widgets_identity: # Iterate through list of actually editable widgets
            if widget not in [self.identity_name_edit, self.identity_role_combo]: # Skip read-only/disabled
                if isinstance(widget, QLineEdit): widget.textChanged.connect(self.mark_unsaved_changes)
                elif isinstance(widget, QComboBox): widget.currentIndexChanged.connect(self.mark_unsaved_changes)
                elif isinstance(widget, (QSpinBox, QDoubleSpinBox)): widget.valueChanged.connect(self.mark_unsaved_changes)
        # Lore
        for widget in self.input_widgets_lore:
            if isinstance(widget, QLineEdit): widget.textChanged.connect(self.mark_unsaved_changes)
            elif isinstance(widget, QTextEdit): widget.textChanged.connect(self.mark_unsaved_changes)
        # Connect signals for currently displayed ability form
        current_list_item = self.ability_selector_list.currentItem()
        if current_list_item:
            item_data = current_list_item.data(Qt.UserRole)
            if item_data:
                ability_key = item_data.get("key")
                ability_index = item_data.get("index")
                form_id = f"{ability_key}"
                if ability_index is not None:
                    form_id += f"_{ability_index}"
                self.connect_signals_for_form(form_id)

    def mark_unsaved_changes(self):
        # ... (same as before) ...
        if not self.tab_widget.isEnabled(): return
        self.unsaved_changes = True; self.save_button.setEnabled(True)
        self.statusBar().showMessage("Unsaved changes.", 3000)

    def save_character_data_ui(self):
        # ... (same as before) ...
        if not self.current_character_filepath or not self.current_character_data:
            QMessageBox.warning(self, "Save Error", "No character data loaded to save."); return False
        self.gather_data_from_ui()
        try:
            backup_filepath = self.current_character_filepath + ".bak"
            if os.path.exists(self.current_character_filepath):
                if os.path.exists(backup_filepath): os.remove(backup_filepath) 
                os.rename(self.current_character_filepath, backup_filepath); print(f"Backup created: {backup_filepath}")
            with open(self.current_character_filepath, 'w', encoding='utf-8') as f:
                json.dump(self.current_character_data, f, indent=2) 
            self.statusBar().showMessage(f"Saved {os.path.basename(self.current_character_filepath)} successfully.", 5000)
            self.unsaved_changes = False; self.save_button.setEnabled(False)
            flag_file_path = os.path.join(CONFIG_DIR, "data_editor_update.flag")
            with open(flag_file_path, 'w') as f: f.write(f"updated: {self.current_character_data.get('name', 'Unknown')}")
            print(f"Update flag created: {flag_file_path}"); return True
        except Exception as e:
            self.statusBar().showMessage(f"Error saving file: {e}")
            QMessageBox.critical(self, "Save Error", f"Could not save data to {self.current_character_filepath}.\nError: {e}"); return False


    def gather_data_from_ui(self):
        # ... (Identity & Stats, Lore & Quotes gathering same as before, respecting read-only fields) ...
        if not self.current_character_data: return
        # Identity (only editable)
        self.current_character_data["release_version"] = self.identity_release_version_edit.text()
        # Name and Role are not gathered as they are read-only/disabled in UI

        if "stats_basic" not in self.current_character_data: self.current_character_data["stats_basic"] = {}
        stats_basic = self.current_character_data["stats_basic"]
        stats_basic["health"]=self.stats_health_spin.value(); stats_basic["armor"]=self.stats_armor_spin.value()
        stats_basic["shields_regenerating"]=self.stats_shields_spin.value(); stats_basic["speed_mps"]=self.stats_speed_spin.value()
        stats_basic["difficulty_rating"]=self.stats_difficulty_spin.value()
        resource_type_text = self.stats_resource_type_edit.text()
        if resource_type_text.strip():
            stats_basic["resource_type"]=resource_type_text; stats_basic["resource_max"]=self.stats_resource_max_spin.value()
        else:
             stats_basic["resource_type"]=None; stats_basic["resource_max"]=None
        # Lore & Quotes
        if "lore" not in self.current_character_data: self.current_character_data["lore"] = {}
        if "quotes" not in self.current_character_data: self.current_character_data["quotes"] = {}
        lore_data = self.current_character_data["lore"]; quotes_data = self.current_character_data["quotes"]
        quotes_data["ingame_bio_quote"]=self.lore_ingame_bio_quote_edit.toHtml(); quotes_data["official_quote"]=self.lore_official_quote_edit.toHtml()
        lore_data["ingame_bio_text"]=self.lore_ingame_bio_text_edit.toHtml(); lore_data["official_description"]=self.lore_official_description_edit.toHtml()
        lore_data["real_name"]=self.lore_real_name_edit.text()
        lore_data["aliases"]=[alias.strip() for alias in self.lore_aliases_edit.text().split(',') if alias.strip()]
        lore_data["birthplace"]=self.lore_birthplace_edit.text(); lore_data["gender"]=self.lore_gender_edit.text()
        lore_data["eye_color"]=self.lore_eye_color_edit.text(); lore_data["hair_color"]=self.lore_hair_color_edit.text()
        lore_data["affiliation"]=[aff.strip() for aff in self.lore_affiliation_edit.text().split(',') if aff.strip()]
        
        # --- Gather data from Abilities Kit Tab ---
        if self.current_character_data and "abilities_kit" in self.current_character_data:
            kit = self.current_character_data["abilities_kit"]
            for form_id, form_widget in self.ability_forms.items():
                parts = form_id.split('_')
                key = parts[0]
                if len(parts) > 1 and parts[0] in ["primary", "secondary", "ability", "passives"]:
                    key = f"{parts[0]}_{parts[1]}"
                    try:
                        index_str_start = 2
                        if parts[0] == "ability" and len(parts) > 2 and parts[1].isdigit():
                            key = f"{parts[0]}_{parts[1]}"
                            index_str_start = 2
                        idx_or_name_part = parts[index_str_start] if len(parts) > index_str_start else None
                        is_indexed_list = isinstance(kit.get(key), list)
                        if is_indexed_list and idx_or_name_part and idx_or_name_part.isdigit():
                            index = int(idx_or_name_part)
                            if index < len(kit[key]):
                                # Placeholder for actual data gathering from form widgets
                                pass
                        elif not is_indexed_list and isinstance(kit.get(key), dict):
                            pass
                    except (IndexError, ValueError, KeyError) as e:
                        print(f"Error parsing form_id '{form_id}' for data gathering: {e}")

    def closeEvent(self, event):
        # ... (same as before) ...
        if self.unsaved_changes:
            reply = QMessageBox.question(self, 'Exit Confirmation', "You have unsaved changes. Exit without saving?", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply == QMessageBox.Yes: event.accept()
            else: event.ignore()
        else: event.accept()

# Application Execution
if __name__ == '__main__':
    app = QApplication(sys.argv)
    mainWindow = DataForgeWindow()
    mainWindow.show()
    sys.exit(app.exec_())