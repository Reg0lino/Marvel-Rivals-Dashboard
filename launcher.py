# -*- coding: utf-8 -*-
import sys
import os
import subprocess
import json
from datetime import datetime
import platform # For OS-specific launching

# --- PySide6 Imports ---
from PySide6.QtWidgets import (
    QApplication, QDialog, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QComboBox, QPushButton, QSizePolicy, QSpacerItem, QFrame,
    QMessageBox, QCheckBox
)
from PySide6.QtCore import Qt, QSize, Signal, Slot, QPoint, QStandardPaths, QUrl, QTimer
from PySide6.QtGui import QScreen, QPixmap, QPainter, QColor, QPalette, QMouseEvent, QFont, QIcon, QMovie

# --- Import from Dashboard ---
try:
    from rivals_dashboard import (
        resource_path,
        H1_COLOR, H2_COLOR, H3_COLOR
    )
    print("Successfully imported essential constants from rivals_dashboard.")
except ImportError as e:
    print(f"FATAL ERROR: Could not import necessary components from rivals_dashboard: {e}")
    print("Make sure launcher.py is in the correct root directory relative to rivals_dashboard.py")
    try:
        if not QApplication.instance(): err_app = QApplication(sys.argv); created_err_app = True
        else: created_err_app = False
        msg_box = QMessageBox(); msg_box.setIcon(QMessageBox.Critical); msg_box.setWindowTitle("Launcher Import Error")
        msg_box.setText(f"Failed to import from rivals_dashboard.py:\n{e}\n\nEnsure files are in the correct location.")
        msg_box.exec()
        if created_err_app: err_app.quit()
    except Exception as e2: print(f"Could not show error message box: {e2}")
    sys.exit(1)

# --- Configuration ---
LAUNCHER_WINDOW_WIDTH = 580
LAUNCHER_WINDOW_HEIGHT = 380
LAUNCHER_BG_COLOR = "#202020"
LAUNCHER_BORDER_COLOR = H2_COLOR
LAUNCHER_BORDER_WIDTH = 2
LAUNCHER_OPACITY = 0.92
CONFIG_FOLDER = resource_path('config')
LAST_UPDATE_FILE = os.path.join(CONFIG_FOLDER, 'last_update.json')
ICON_PATH = resource_path('images/Marvel Rivals Dashboard.ico')
LOADING_GIF_PATH = resource_path('images/loading.gif')
LOADING_GIF_SIZE = 128
LAUNCH_SUCCESS_CLOSE_DELAY_MS = 8000 # <<< SET TO 8 SECONDS

# --- Launcher Font Configuration ---
LAUNCHER_FONT_FAMILY = "Refrigerator Deluxe" # Or "Segoe UI"
LAUNCHER_BASE_FONT_PT = 10
LAUNCHER_TITLE_FONT_PT = LAUNCHER_BASE_FONT_PT + 10
LAUNCHER_LABEL_FONT_PT = LAUNCHER_BASE_FONT_PT + 1
LAUNCHER_INFO_FONT_PT = LAUNCHER_BASE_FONT_PT - 1
LAUNCHER_BUTTON_FONT_PT = LAUNCHER_BASE_FONT_PT
LAUNCHER_CHECKBOX_FONT_PT = LAUNCHER_BASE_FONT_PT - 1
LAUNCHER_EXIT_FONT_PT = LAUNCHER_BASE_FONT_PT + 2
LAUNCHER_TOOLTIP_FONT_PT = LAUNCHER_BASE_FONT_PT - 1
LAUNCHER_COMBO_ITEM_FONT_PT = LAUNCHER_BASE_FONT_PT - 1

# --- Helper Function for Paths --- (Keep as before)
def get_script_path(script_name):
    try:
        base_path = os.path.dirname(os.path.abspath(__file__))
        if script_name == "rivals_dashboard.py": path = os.path.join(base_path, script_name)
        elif script_name == "updater_v3.py": path = os.path.join(base_path, 'scraper', script_name)
        else: path = os.path.join(base_path, script_name)
        return os.path.normpath(path)
    except Exception: return script_name

# --- OS-Specific Launch Helper --- (Keep as before)
def launch_external(target_uri_or_path):
    system = platform.system(); print(f"Attempting to launch '{target_uri_or_path}' on {system}...")
    try:
        if system == "Windows": os.startfile(target_uri_or_path); print(f"Issued launch command via os.startfile.") ; return True
        elif system == "Darwin": subprocess.Popen(['open', target_uri_or_path], close_fds=True); print(f"Launched via 'open'."); return True
        else: subprocess.Popen(['xdg-open', target_uri_or_path], close_fds=True); print(f"Launched via 'xdg-open'."); return True
    except FileNotFoundError: print(f"ERROR: Command not found for '{target_uri_or_path}'."); return False
    except Exception as e: print(f"ERROR: Failed to launch '{target_uri_or_path}': {e}"); return False

# --- Launcher Dialog ---
class LauncherDialog(QDialog):
    def __init__(self, screens, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Marvel Rivals Launcher")
        self.setModal(True)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self._drag_pos = None

        if os.path.exists(ICON_PATH): self.setWindowIcon(QIcon(ICON_PATH))
        else: print(f"Warning: Launcher icon not found at {ICON_PATH}")

        self.screens = screens
        self.selected_screen = QApplication.primaryScreen()
        self.fullscreen_mode = False
        self.debug_mode = False
        self.is_launching = False # Prevent multiple launches

        self.init_ui()
        self.setFixedSize(LAUNCHER_WINDOW_WIDTH, LAUNCHER_WINDOW_HEIGHT)
        self._read_update_info()
        self._apply_styles()
        self.setWindowOpacity(LAUNCHER_OPACITY)

        # Initialize Loading GIF Movie
        self.loading_movie = QMovie(LOADING_GIF_PATH)
        if self.loading_movie.isValid():
            self.loading_label.setMovie(self.loading_movie)
        else:
            print(f"Warning: Could not load loading GIF: {LOADING_GIF_PATH}")
            self.loading_label.setText("...")
            self.loading_label.setAlignment(Qt.AlignCenter)
            self.loading_label.setStyleSheet(f"font-size: {LAUNCHER_TITLE_FONT_PT}pt; color: white;")

    # --- UI Creation Method --- (Mostly unchanged, ensures loading_label exists)
    def init_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setSpacing(8); self.main_layout.setContentsMargins(20, 15, 20, 15)
        # Top Row
        top_row_layout = QHBoxLayout(); title_label = QLabel("MARVEL RIVALS LAUNCHER"); title_label.setObjectName("LauncherTitle")
        self.exit_button_launcher = QPushButton("✕"); self.exit_button_launcher.setObjectName("LauncherExitButton"); self.exit_button_launcher.setToolTip("Close Launcher"); self.exit_button_launcher.clicked.connect(self.reject)
        top_row_layout.addWidget(title_label); top_row_layout.addStretch(1); top_row_layout.addWidget(self.exit_button_launcher)
        self.main_layout.addLayout(top_row_layout)
        # Monitor Selection
        monitor_layout = QHBoxLayout(); monitor_label = QLabel("Monitor:"); monitor_label.setObjectName("LauncherLabel")
        self.monitor_combo = QComboBox(); self.monitor_combo.setObjectName("MonitorComboBox"); self.monitor_combo.setMinimumWidth(250); self.monitor_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        for i, screen in enumerate(self.screens):
            screen_name = screen.name() if screen.name() else f"Unknown_{i}"; geo = screen.geometry(); size_str = f"{geo.width()}x{geo.height()}"
            primary_str = " (Primary)" if screen == QApplication.primaryScreen() else ""; display_text = f"Display {i+1}{primary_str}: [{size_str}]"; tooltip_text = f"Screen {i+1}{primary_str}: {screen_name} [{size_str}]"
            self.monitor_combo.addItem(display_text, userData=screen); self.monitor_combo.setItemData(i, tooltip_text, Qt.ToolTipRole)
        primary_screen_index = self.screens.index(QApplication.primaryScreen()) if QApplication.primaryScreen() in self.screens else 0
        self.monitor_combo.setCurrentIndex(primary_screen_index); monitor_layout.addWidget(monitor_label); monitor_layout.addWidget(self.monitor_combo)
        self.main_layout.addLayout(monitor_layout)
        # Mode Selection
        mode_layout = QHBoxLayout(); mode_label = QLabel("Display Mode:"); mode_label.setObjectName("LauncherLabel")
        self.mode_combo = QComboBox(); self.mode_combo.setObjectName("ModeComboBox"); self.mode_combo.addItem("Windowed", userData=False); self.mode_combo.addItem("Fullscreen", userData=True)
        self.mode_combo.setCurrentIndex(0); self.mode_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed); mode_layout.addWidget(mode_label); mode_layout.addWidget(self.mode_combo)
        self.main_layout.addLayout(mode_layout)
        # Separator 1
        separator1 = QFrame(); separator1.setFrameShape(QFrame.Shape.HLine); separator1.setFrameShadow(QFrame.Shadow.Sunken); separator1.setObjectName("SeparatorFrame"); self.main_layout.addWidget(separator1)
        # Last Update Info
        info_layout = QGridLayout(); info_layout.setContentsMargins(0, 5, 0, 5); info_layout.setHorizontalSpacing(10); info_layout.setVerticalSpacing(3)
        info_layout.addWidget(QLabel("Data Generated:"), 0, 0, alignment=Qt.AlignRight); self.last_gen_label = QLabel("N/A"); self.last_gen_label.setObjectName("InfoValueLabel"); info_layout.addWidget(self.last_gen_label, 0, 1)
        info_layout.addWidget(QLabel("Meta Stats:"), 0, 2, alignment=Qt.AlignRight); self.last_meta_label = QLabel("N/A"); self.last_meta_label.setObjectName("InfoValueLabel"); info_layout.addWidget(self.last_meta_label, 0, 3)
        info_layout.addWidget(QLabel("Game Patch Parsed:"), 1, 0, alignment=Qt.AlignRight); self.last_patch_label = QLabel("Unknown"); self.last_patch_label.setObjectName("InfoValueLabel"); info_layout.addWidget(self.last_patch_label, 1, 1)
        info_layout.addWidget(QLabel("Info Files:"), 1, 2, alignment=Qt.AlignRight); self.last_info_label = QLabel("N/A"); self.last_info_label.setObjectName("InfoValueLabel"); info_layout.addWidget(self.last_info_label, 1, 3)
        info_layout.setColumnStretch(1, 1); info_layout.setColumnStretch(3, 1); self.main_layout.addLayout(info_layout)
        # Separator 2
        separator2 = QFrame(); separator2.setFrameShape(QFrame.Shape.HLine); separator2.setFrameShadow(QFrame.Shadow.Sunken); separator2.setObjectName("SeparatorFrame"); self.main_layout.addWidget(separator2)
        # Stretch
        self.main_layout.addStretch(1)
        # Action Buttons Layout
        button_layout = QHBoxLayout(); button_layout.setSpacing(20)
        self.launch_updater_button = QPushButton("⚙️ Launch Updater"); self.launch_updater_button.setObjectName("LaunchUpdaterButton"); self.launch_updater_button.setToolTip("Open the Data Updater Tool")
        self.launch_dashboard_button = QPushButton("⚡ Launch Dashboard"); self.launch_dashboard_button.setObjectName("LaunchDashboardButton"); self.launch_dashboard_button.setToolTip("Start the Marvel Rivals Dashboard"); self.launch_dashboard_button.setDefault(True)
        self.launch_updater_button.clicked.connect(self._trigger_launch_updater)
        self.launch_dashboard_button.clicked.connect(self.accept) # Accept triggers dashboard launch
        button_layout.addStretch(1); button_layout.addWidget(self.launch_updater_button); button_layout.addWidget(self.launch_dashboard_button); button_layout.addStretch(1)
        self.main_layout.addLayout(button_layout)
        # Debug Checkbox
        debug_layout = QHBoxLayout(); debug_layout.setContentsMargins(0, 5, 0, 0)
        self.debug_checkbox = QCheckBox("Start Dashboard in Debug Mode"); self.debug_checkbox.setObjectName("LauncherCheckbox"); self.debug_checkbox.setToolTip("Logs detailed messages to console (for troubleshooting)")
        debug_layout.addStretch(1); debug_layout.addWidget(self.debug_checkbox); debug_layout.addStretch(1)
        self.main_layout.addLayout(debug_layout)
        # Loading GIF Label (Created Here, Hidden)
        self.loading_label = QLabel(self); self.loading_label.setObjectName("LoadingGIFLabel")
        self.loading_label.setAlignment(Qt.AlignCenter); self.loading_label.setAttribute(Qt.WA_TranslucentBackground); self.loading_label.hide()

    # --- Paint Event for Background and Border --- (Keep as before)
    def paintEvent(self, event):
        painter = QPainter(self); painter.setRenderHint(QPainter.Antialiasing)
        bg_qcolor = QColor(LAUNCHER_BG_COLOR); painter.setBrush(bg_qcolor); painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(self.rect(), 10, 10)
        pen = painter.pen(); pen.setColor(QColor(LAUNCHER_BORDER_COLOR)); pen.setWidth(LAUNCHER_BORDER_WIDTH); pen.setStyle(Qt.SolidLine)
        painter.setPen(pen); painter.setBrush(Qt.NoBrush)
        adj = LAUNCHER_BORDER_WIDTH / 2.0; border_rect = self.rect().adjusted(adj, adj, -adj, -adj)
        painter.drawRoundedRect(border_rect, 10, 10)

    # --- Window Dragging Methods --- (Keep as before)
    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton: self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft(); event.accept()
        else: super().mousePressEvent(event)
    def mouseMoveEvent(self, event: QMouseEvent):
        if event.buttons() == Qt.LeftButton and self._drag_pos: self.move(event.globalPosition().toPoint() - self._drag_pos); event.accept()
        else: super().mouseMoveEvent(event)
    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton: self._drag_pos = None; event.accept()
        else: super().mouseReleaseEvent(event)

    # --- Styling Method --- (Keep as before)
    def _apply_styles(self):
        font_family = LAUNCHER_FONT_FAMILY; h1_color = H1_COLOR; h2_color = H2_COLOR; h3_color = H3_COLOR
        bg_color = LAUNCHER_BG_COLOR; text_color = "#E0E0E0"; dim_text_color = "#B0B0B0"; info_val_color = "#D0D0D0"
        border_color = "#484848"; accent_border_color = h2_color; button_bg = "#3A3A3A"; button_hover_bg = "#4A4A4A"
        button_pressed_bg = "#2A2A2A"; default_border_color = h1_color; exit_hover_bg = h3_color
        exit_pressed_bg = QColor(h3_color).darker(120).name(); exit_color = dim_text_color; exit_hover_color = "#FFFFFF"
        lbf = LAUNCHER_BASE_FONT_PT; ltf = LAUNCHER_TITLE_FONT_PT; llf = LAUNCHER_LABEL_FONT_PT; lif = LAUNCHER_INFO_FONT_PT
        lbtf = LAUNCHER_BUTTON_FONT_PT; lcf = LAUNCHER_CHECKBOX_FONT_PT; lef = LAUNCHER_EXIT_FONT_PT
        lttf = LAUNCHER_TOOLTIP_FONT_PT; lcif = LAUNCHER_COMBO_ITEM_FONT_PT
        style = f"""
        LauncherDialog {{ font-family: '{font_family}', sans-serif; }}
        QLabel {{ color: {dim_text_color}; background-color: transparent; font-size: {lif}pt; }}
        #LauncherTitle {{ color: {h1_color}; font-size: {ltf}pt; font-weight: bold; padding: 0px 5px; margin-bottom: 8px; }}
        #LauncherLabel {{ color: {text_color}; font-weight: bold; font-size: {llf}pt; padding-right: 5px; }}
        #InfoValueLabel {{ color: {info_val_color}; font-size: {lif}pt; background-color: rgba(0, 0, 0, 0.2); border: 1px solid {border_color}; border-radius: 3px; padding: 2px 4px; min-height: 18px; margin-left: 3px; }}
        QComboBox {{ color: {text_color}; background-color: {button_bg}; border: 1px solid {border_color}; border-radius: 4px; padding: 5px 8px; min-height: 26px; font-size: {lbf}pt; font-weight: normal; }}
        QComboBox:hover {{ border: 1px solid {accent_border_color}; }}
        QComboBox::drop-down {{ width: 22px; border-left: 1px solid {border_color}; background-color: {button_bg}; }}
        QComboBox::down-arrow {{ border: 2px solid {h1_color}; width: 7px; height: 7px; background: transparent; border-top-color: transparent; border-left-color: transparent; border-right-color: transparent; margin: 2px 5px 2px 2px; }}
        QComboBox QAbstractItemView {{ color: {text_color}; background-color: #282828; border: 1px solid {accent_border_color}; selection-background-color: {h2_color}; padding: 4px; font-size: {lcif}pt; }}
        QPushButton {{ background-color: {button_bg}; color: {text_color}; border: 1px solid {border_color}; padding: 7px 15px; border-radius: 5px; min-height: 28px; font-size: {lbtf}pt; font-weight: bold; }}
        QPushButton:hover:!disabled {{ background-color: {button_hover_bg}; border: 1px solid {accent_border_color}; }}
        QPushButton:pressed:!disabled {{ background-color: {button_pressed_bg}; }}
        QPushButton:disabled {{ background-color: #303030; color: #666666; border-color: #404040; }}
        #LaunchDashboardButton:default {{ border: 2px solid {default_border_color}; padding: 6px 14px; }}
        #LaunchDashboardButton:default:disabled {{ border: 2px solid #666; }}
        #LaunchUpdaterButton {{ font-size: {lbtf}pt; }} #LaunchDashboardButton {{ font-size: {lbtf}pt; }}
        #LauncherExitButton {{ background-color: transparent; color: {exit_color}; font-size: {lef}pt; font-weight: bold; border: none; border-radius: 13px; min-width: 26px; max-width: 26px; min-height: 26px; max-height: 26px; padding: 0px; margin: 0px; }}
        #LauncherExitButton:hover {{ background-color: {exit_hover_bg}; color: {exit_hover_color}; }}
        #LauncherExitButton:pressed {{ background-color: {exit_pressed_bg}; }}
        #SeparatorFrame {{ background-color: {border_color}; min-height: 1px; max-height: 1px; margin: 8px 0px; }}
        #LauncherCheckbox {{ color: {dim_text_color}; font-size: {lcf}pt; spacing: 5px; background-color: transparent; }}
        #LauncherCheckbox::indicator {{ width: 14px; height: 14px; border-radius: 3px; }}
        #LauncherCheckbox::indicator:unchecked {{ background-color: {button_bg}; border: 1px solid {border_color}; }}
        #LauncherCheckbox::indicator:checked {{ background-color: {h2_color}; border: 1px solid {accent_border_color}; }}
        #LauncherCheckbox:hover {{ color: {text_color}; }}
        QToolTip {{ color: #FFFFFF; background-color: #282828; border: 1px solid {accent_border_color}; padding: 4px; font-size: {lttf}pt; border-radius: 3px; opacity: 230; }}
        #LoadingGIFLabel {{ background-color: transparent; border: none; }}
        """
        self.setStyleSheet(style)

    # --- Action Methods ---
    def _read_update_info(self): # (Keep as before)
        data = {}; default_date = "N/A"; default_patch = "Unknown"
        if os.path.exists(LAST_UPDATE_FILE):
            try:
                with open(LAST_UPDATE_FILE, 'r', encoding='utf-8') as f: data = json.load(f)
            except Exception as e: print(f"Warning: Could not read/parse {LAST_UPDATE_FILE}: {e}")
        else: print(f"Info: {LAST_UPDATE_FILE} not found. Update info shows defaults.")
        def format_timestamp(ts_str):
            if not ts_str: return default_date
            try: dt_obj = datetime.fromisoformat(ts_str); return dt_obj.strftime("%m/%d/%Y %I:%M %p")
            except: return "Invalid Date"
        if hasattr(self, 'last_gen_label'): self.last_gen_label.setText(format_timestamp(data.get("last_json_gen")))
        if hasattr(self, 'last_meta_label'): self.last_meta_label.setText(format_timestamp(data.get("last_meta_update")))
        if hasattr(self, 'last_info_label'): self.last_info_label.setText(format_timestamp(data.get("last_info_update")))
        if hasattr(self, 'last_patch_label'): self.last_patch_label.setText(data.get("last_game_patch_parsed", default_patch))
        if hasattr(self, 'last_gen_label'): self.last_gen_label.setToolTip(f"From '{os.path.basename(LAST_UPDATE_FILE)}'\nKey: last_json_gen")
        if hasattr(self, 'last_meta_label'): self.last_meta_label.setToolTip(f"From '{os.path.basename(LAST_UPDATE_FILE)}'\nKey: last_meta_update")
        if hasattr(self, 'last_info_label'): self.last_info_label.setToolTip(f"From '{os.path.basename(LAST_UPDATE_FILE)}'\nKey: last_info_update")
        if hasattr(self, 'last_patch_label'): self.last_patch_label.setToolTip(f"From '{os.path.basename(LAST_UPDATE_FILE)}'\nKey: last_game_patch_parsed")

    # --- Loading GIF Helpers ---
    def _show_loading(self):
        if hasattr(self, 'loading_label') and hasattr(self, 'loading_movie'):
            # --- Make label cover the entire dialog ---
            dialog_rect = self.rect()
            self.loading_label.setGeometry(dialog_rect) # Set label geometry to fill dialog

            # --- Scale movie to fit the new label size ---
            if self.loading_movie.isValid():
                # Scale the movie to the dialog's size
                # Qt.KeepAspectRatio should prevent distortion, might letterbox/pillarbox
                # Use Qt.IgnoreAspectRatio if you want it to stretch fully
                self.loading_movie.setScaledSize(dialog_rect.size())
                self.loading_movie.start()

            self.loading_label.show()
            self.loading_label.raise_() # Ensure it's visually on top

            print("DEBUG: Showing loading indicator (resized to overlay).")
        else:
             print("DEBUG: Loading label/movie not found.")

    def _hide_loading(self):
        if hasattr(self, 'loading_label') and hasattr(self, 'loading_movie'):
            if self.loading_movie.isValid(): self.loading_movie.stop()
            self.loading_label.hide()
            print("DEBUG: Hiding loading indicator.")

    # --- Enable/Disable Controls during Launch ---
    def _set_controls_enabled(self, enabled):
        # Define list of widgets to enable/disable (exclude exit button)
        widgets_to_toggle = [
            self.monitor_combo, self.mode_combo, self.debug_checkbox,
            self.launch_updater_button, self.launch_dashboard_button
        ]
        for w in widgets_to_toggle:
            if hasattr(w, 'setEnabled'): w.setEnabled(enabled)

        # Reset button text ONLY when RE-ENABLING
        if enabled:
             if hasattr(self, 'launch_updater_button'): self.launch_updater_button.setText("⚙️ Launch Updater")
             if hasattr(self, 'launch_dashboard_button'): self.launch_dashboard_button.setText("⚡ Launch Dashboard")

    # --- Script Launching Logic ---
    def _launch_script_detached(self, script_path, args=None):
        """Launches a python script, returns True on success, False on failure."""
        if not os.path.exists(script_path):
            print(f"ERROR: Script not found: {script_path}"); QMessageBox.critical(self, "Error", f"Script not found:\n{script_path}"); return False

        command_list = []; python_exe = sys.executable
        is_dashboard = "rivals_dashboard.py" in script_path
        debug_dashboard = False
        if is_dashboard and hasattr(self, 'debug_checkbox'): debug_dashboard = self.debug_checkbox.isChecked()

        flags = 0; stdin=None; stdout=None; stderr=None
        if platform.system() == "Windows":
            if debug_dashboard: # Use python.exe, allow console
                python_exe = sys.executable.replace("pythonw.exe", "python.exe") # Ensure it's python.exe
                print("DEBUG: Launching dashboard with console visible (debug mode).")
            else: # Try pythonw.exe and hide console
                pythonw_path = python_exe.replace("python.exe", "pythonw.exe")
                if os.path.exists(pythonw_path): python_exe = pythonw_path
                else: print("Warning: pythonw.exe not found, console may appear.")
                # Use flags to detach and hide
                DETACHED_PROCESS = 0x00000008; CREATE_NEW_PROCESS_GROUP = 0x00000200; CREATE_NO_WINDOW = 0x08000000
                flags = DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP | CREATE_NO_WINDOW
                stdin=subprocess.DEVNULL; stdout=subprocess.DEVNULL; stderr=subprocess.DEVNULL
        # Add other platform flag logic here if needed (macOS/Linux usually detach better by default)

        command_list.append(python_exe); command_list.append(script_path)
        if args: command_list.extend(args)

        print(f"Attempting to launch script: {' '.join(command_list)}")
        try:
            # Using creationflags only on Windows
            kwargs = {'close_fds': True, 'stdin': stdin, 'stdout': stdout, 'stderr': stderr}
            if platform.system() == "Windows": kwargs['creationflags'] = flags

            subprocess.Popen(command_list, **kwargs)
            print("Script launch command issued."); return True
        except Exception as e:
            print(f"ERROR launching script {script_path}: {e}"); QMessageBox.critical(self, "Launch Error", f"Failed:\n{script_path}\n\nError: {e}"); return False

    # --- Button Trigger Slots ---
    @Slot()
    def _trigger_launch_updater(self):
        if self.is_launching: return
        self.is_launching = True; self._set_controls_enabled(False); self.launch_updater_button.setText("Starting...")
        self._show_loading(); QApplication.processEvents()

        updater_path = get_script_path("updater_v3.py")
        success = self._launch_script_detached(updater_path)

        if success:
            print(f"Updater launch initiated. Launcher will close in {LAUNCH_SUCCESS_CLOSE_DELAY_MS / 1000}s.")
            QTimer.singleShot(LAUNCH_SUCCESS_CLOSE_DELAY_MS, self.close) # Close launcher after delay
            # Keep GIF visible until close
        else:
            print("Updater launch failed.")
            self._hide_loading()
            self._set_controls_enabled(True) # Re-enable on failure
            self.is_launching = False

    @Slot() # Connected to Launch Dashboard button
    def accept(self):
        if self.is_launching: return
        self.is_launching = True; self._set_controls_enabled(False); self.launch_dashboard_button.setText("Starting...")
        self._show_loading(); QApplication.processEvents()

        # Get settings
        monitor_index = self.monitor_combo.currentIndex()
        self.selected_screen = self.screens[monitor_index] if 0 <= monitor_index < len(self.screens) else QApplication.primaryScreen()
        self.fullscreen_mode = (self.mode_combo.currentData() == True)
        self.debug_mode = self.debug_checkbox.isChecked()
        print(f"Launcher Settings: Screen='{self.selected_screen.name() if self.selected_screen else 'N/A'}', Fullscreen={self.fullscreen_mode}, Debug={self.debug_mode}")

        # Prepare args
        dashboard_args = []
        if self.selected_screen: dashboard_args.extend(["--screen", self.selected_screen.name()])
        if self.fullscreen_mode: dashboard_args.append("--fullscreen")
        if self.debug_mode: dashboard_args.append("--debug")

        dashboard_script_path = get_script_path("rivals_dashboard.py")
        success = self._launch_script_detached(dashboard_script_path, dashboard_args)

        if success:
            print(f"Dashboard launch initiated. Launcher will close in {LAUNCH_SUCCESS_CLOSE_DELAY_MS / 1000}s.")
            QTimer.singleShot(LAUNCH_SUCCESS_CLOSE_DELAY_MS, self.close) # Close launcher after delay
            # Keep GIF visible until close
        else:
            print("Dashboard launch failed.")
            self._hide_loading()
            self._set_controls_enabled(True) # Re-enable on failure
            self.is_launching = False
        # Don't call super().accept()

    # get_selection can remain as is
    def get_selection(self):
        screen = self.screens[self.monitor_combo.currentIndex()] if 0 <= self.monitor_combo.currentIndex() < len(self.screens) else QApplication.primaryScreen()
        fullscreen = (self.mode_combo.currentData() == True); debug = self.debug_checkbox.isChecked()
        return screen, fullscreen, debug

# --- Main Execution --- (Keep as before)
if __name__ == "__main__":
    try:
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling); QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)
    except AttributeError: pass
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)

    app = QApplication(sys.argv)

    available_screens = QApplication.screens()
    if not available_screens: QMessageBox.critical(None, "Fatal Error", "No screens detected."); sys.exit(1)

    launcher = LauncherDialog(available_screens)
    launcher.show()

    primary_screen = QApplication.primaryScreen()
    if primary_screen:
        try:
            available_geo = primary_screen.availableGeometry(); launcher_geo = launcher.frameGeometry()
            center_point = available_geo.center(); launcher_geo.moveCenter(center_point); launcher.move(launcher_geo.topLeft())
        except Exception as e: print(f"Warning: Could not center launcher window: {e}")

    sys.exit(app.exec())