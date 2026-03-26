from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QLabel, QFileDialog, QComboBox, QListWidget,
                             QMessageBox, QFrame, QSplitter, QLineEdit, QRadioButton,
                             QButtonGroup, QTableWidget, QTableWidgetItem, QHeaderView,
                             QCompleter, QGroupBox, QDateEdit, QPlainTextEdit,
                             QSpinBox, QScrollArea, QDialog)
from PyQt6.QtGui import QKeySequence, QShortcut
from PyQt6.QtCore import Qt, QDate
from core.data_loader import ExcelLoader, ADTFLoader
from core.logic import InspectorLogic, Rule, RuleType
import os

from ui.widgets import TimelineWidget, ADTFImageDisplayWidget
from ui.batch_dialog import BatchResultDialog
from ui.macro_dialog import MacroDialog
from ui.or_rule_dialog import ORRuleDialog

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SILS-validator")
        self.resize(1560, 1140)
        self.data_loader = ExcelLoader()
        self.selected_topics = []
        self.current_excel_path = None
        self.file_list = []  # List of absolute paths
        self.current_file_index = -1
        self.recent_config = None
        self.batch_dialog = None
        
        self.dat_folder_path = None
        self.dat_file_map = {} # Maps base name (e.g., 'AAAA') to absolute path

        self.init_ui()
        self.setup_shortcuts()
        
        # Schedule auto-load to run after the main window is shown and event loop starts
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(100, self.auto_load_master_config)

    def auto_load_master_config(self):
        root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        auto_config_path = os.path.join(root_dir, "master_config.json")

        if os.path.exists(auto_config_path):
            try:
                self.inspector_logic.load_master_config(auto_config_path)
                QMessageBox.information(self, "Config Loaded", f"Automatically loaded master config:\n{auto_config_path}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to auto-load master config:\n{e}")

    def init_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        
        # Main Layout
        layout = QVBoxLayout(main_widget)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Top Bar: File Loading
        top_bar = QHBoxLayout()
        top_bar.setSpacing(10)
        
        # We can style the file label to look better
        self.file_label = QLabel("No file loaded")
        self.file_label.setStyleSheet("color: #666; font-style: italic; margin-left: 10px;")
        # Load Master Config Button
        master_btn = QPushButton("Load Master Config")
        master_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        master_btn.clicked.connect(self.open_master_config_dialog)

        # Load Excel Button
        load_btn = QPushButton("Select File")
        load_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        load_btn.clicked.connect(self.load_excel_file)
        
        # Load Folder Button
        load_folder_btn = QPushButton("Select Folder")
        load_folder_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        load_folder_btn.clicked.connect(self.load_folder_dialog)
        
        # Load DAT Folder Button
        load_dat_folder_btn = QPushButton("Select DAT Folder")
        load_dat_folder_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        load_dat_folder_btn.clicked.connect(self.load_dat_folder_dialog)
        
        # Navigation Controls
        self.prev_btn = QPushButton("◀")
        self.prev_btn.setFixedSize(30, 30)
        self.prev_btn.setStyleSheet("color: white; font-weight: bold; background-color: #007BFF; padding: 0px; border-radius: 4px;")
        self.prev_btn.clicked.connect(self.load_prev_file)
        # self.prev_btn.setShortcut("Ctrl+Q") # Can use shortcut directly or global method

        self.file_dropdown = QComboBox()
        self.file_dropdown.setMinimumWidth(200)
        self.file_dropdown.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToContents)
        self.file_dropdown.currentIndexChanged.connect(self.on_file_dropdown_changed)
        
        self.next_btn = QPushButton("▶")
        self.next_btn.setFixedSize(30, 30)
        self.next_btn.setStyleSheet("color: white; font-weight: bold; background-color: #007BFF; padding: 0px; border-radius: 4px;")
        self.next_btn.clicked.connect(self.load_next_file)
        # self.next_btn.setShortcut("Ctrl+E")
        
        # Save Config Button
        save_btn = QPushButton("Save Master Config")
        save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        save_btn.clicked.connect(self.save_config)
        
        # Guide Button
        guide_btn = QPushButton("Guide")
        guide_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        guide_btn.setStyleSheet("color: white; font-weight: bold; background-color: #28a745; padding: 5px 10px; border-radius: 4px;")
        guide_btn.clicked.connect(self.show_guide_dialog)
        
        # Batch Run Button
        batch_btn = QPushButton("Batch Run")
        batch_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        batch_btn.clicked.connect(self.open_batch_dialog)
        
        top_bar.addWidget(master_btn)
        top_bar.addWidget(load_btn)
        top_bar.addWidget(load_folder_btn)
        top_bar.addWidget(load_dat_folder_btn)
        top_bar.addWidget(self.prev_btn)
        top_bar.addWidget(self.file_dropdown)
        top_bar.addWidget(self.next_btn)
        top_bar.addWidget(self.file_label)
        top_bar.addStretch()
        top_bar.addWidget(guide_btn)
        top_bar.addWidget(batch_btn)
        top_bar.addWidget(save_btn)
        
        layout.addLayout(top_bar)
        
        # Splitter for Main Content
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(2)
        
        # Left Panel (Topics) wrapped in ScrollArea
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QScrollArea.Shape.NoFrame)
        
        left_panel = QFrame()
        left_panel.setFrameShape(QFrame.Shape.NoFrame)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setSpacing(10)
        left_layout.setContentsMargins(10, 10, 10, 10)

        # -- Test Information Group --
        test_info_group = QGroupBox("Test Information")
        test_info_layout = QVBoxLayout(test_info_group)
        
        # Vehicle
        test_info_layout.addWidget(QLabel("Vehicle:"))
        self.input_vehicle = QLineEdit()
        self.input_vehicle.setPlaceholderText("e.g. Prototype-A")
        test_info_layout.addWidget(self.input_vehicle)
        
        # SW Version
        test_info_layout.addWidget(QLabel("SW Version:"))
        self.input_sw_ver = QLineEdit()
        self.input_sw_ver.setPlaceholderText("e.g. v1.0.2")
        test_info_layout.addWidget(self.input_sw_ver)
        
        # Test Date
        test_info_layout.addWidget(QLabel("Test Date:"))
        self.input_date = QDateEdit()
        self.input_date.setCalendarPopup(True)
        self.input_date.setDate(QDate.currentDate())
        test_info_layout.addWidget(self.input_date)
        
        left_layout.addWidget(test_info_group)
        
        # Category
        test_info_layout.addWidget(QLabel("Category:"))
        cat_layout = QHBoxLayout()
        self.input_category_combo = QComboBox()
        self.input_category_combo.addItems([
            'ENCAP_DSM', 'ENCAP_OSM', 'ADDW', 'DDAW', 'AOI', 
            'FATIGUE', 'EYEP', 'FMEA_DSM', 'FMEA_OSM', 'BO', 
            'SBT', 'ACT', 'ONCAL', 'BLK'
        ])
        cat_layout.addWidget(self.input_category_combo)
        
        add_cat_btn = QPushButton("Add")
        add_cat_btn.setFixedWidth(80) 
        add_cat_btn.clicked.connect(self.add_category)
        cat_layout.addWidget(add_cat_btn)
        test_info_layout.addLayout(cat_layout)

        self.category_list = QListWidget()
        self.category_list.setFixedHeight(80)
        # Reduce item height/padding
        self.category_list.setStyleSheet("QListWidget::item { height: 20px; padding: 0px; }")
        test_info_layout.addWidget(self.category_list)
        
        del_cat_btn = QPushButton("Delete Category")
        del_cat_btn.clicked.connect(self.delete_category)
        test_info_layout.addWidget(del_cat_btn)

        # TC Number
        test_info_layout.addWidget(QLabel("TC Number:"))
        self.input_tc_num = QLineEdit()
        test_info_layout.addWidget(self.input_tc_num)

        # Note
        test_info_layout.addWidget(QLabel("Note:"))
        self.input_note = QPlainTextEdit()
        self.input_note.setFixedHeight(60)
        test_info_layout.addWidget(self.input_note)     

        # Load Recent Config Button
        load_recent_btn = QPushButton("Load Recent Config")
        load_recent_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        # self._style_secondary_button(load_recent_btn) # Reverted to default (Blue)
        load_recent_btn.clicked.connect(self.load_recent_config)
        test_info_layout.addWidget(load_recent_btn)   
        # -----------------------------
        
        lbl_topics = QLabel("Topics")
        lbl_topics.setProperty("heading", "true")
        left_layout.addWidget(lbl_topics)
        
        # Topic Selection
        self.topic_combo = QComboBox()
        self.topic_combo.setEditable(True)
        self.topic_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.topic_combo.completer().setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self.topic_combo.completer().setFilterMode(Qt.MatchFlag.MatchContains)
        self.topic_combo.setPlaceholderText("Search Topic...")
        left_layout.addWidget(self.topic_combo)
        
        add_topic_btn = QPushButton("Add Topic")
        add_topic_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_topic_btn.clicked.connect(self.add_topic)
        left_layout.addWidget(add_topic_btn)
        
        # Selected Topics List -> Table with Plot #
        self.topic_table = QTableWidget()
        self.topic_table.setColumnCount(2)
        self.topic_table.setHorizontalHeaderLabels(["Topic Name", "Plot #"])
        self.topic_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.topic_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self.topic_table.setColumnWidth(1, 120)
        # Increase row height for better clickability
        self.topic_table.verticalHeader().setDefaultSectionSize(45)
        self.topic_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        left_layout.addWidget(self.topic_table)
        
        delete_topic_btn = QPushButton("Delete Selected Topic")
        delete_topic_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._style_danger_button(delete_topic_btn)
        delete_topic_btn.clicked.connect(self.delete_topic)
        left_layout.addWidget(delete_topic_btn)
        
        # left_panel.setLayout(left_layout) # Added to layout directly above
        scroll_area.setWidget(left_panel)
        splitter.addWidget(scroll_area)
        
        # Center/Right Panel (Visualization + Rules)
        right_panel = QWidget() # Container for right side
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0) # Splitter will handle margins
        
        # Vertical Splitter
        right_splitter = QSplitter(Qt.Orientation.Vertical)
        right_splitter.setHandleWidth(2)
        
        # --- Top: Visualization Container ---
        viz_container = QWidget()
        viz_layout = QVBoxLayout(viz_container)
        viz_layout.setSpacing(10)
        viz_layout.setContentsMargins(10, 10, 10, 10)
        
        lbl_viz = QLabel("Visualization & Inspector")
        lbl_viz.setProperty("heading", "true")
        viz_layout.addWidget(lbl_viz)
        
        # Visualization Data Display
        self.data_display_label = QLabel("Time: 0.00s | Frame: 0")
        self.data_display_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        viz_layout.addWidget(self.data_display_label)

        # ADTF Image Display Widget
        self.adtf_display = ADTFImageDisplayWidget()
        self.adtf_display.frame_changed.connect(self.on_adtf_frame_changed)
        viz_layout.addWidget(self.adtf_display)

        # Visualization Widget
        self.timeline = TimelineWidget()
        self.timeline.time_changed.connect(self.on_time_changed)
        viz_layout.addWidget(self.timeline)
        
        # Connect ADTF range shortcuts to timeline
        self.adtf_display.set_range_start_requested.connect(self.timeline.spin_start.setValue)
        self.adtf_display.set_range_end_requested.connect(self.timeline.spin_end.setValue)
        
        right_splitter.addWidget(viz_container)
        
        # --- Bottom: Rules Container ---
        rule_group = self.create_rule_group()
        right_splitter.addWidget(rule_group)
        
        # Set initial stretch (1:2 ratio attempt)
        right_splitter.setStretchFactor(0, 1)
        right_splitter.setStretchFactor(1, 2)
        
        right_layout.addWidget(right_splitter)
        
        splitter.addWidget(right_panel)
        
        # Set Splitter Ratios: Make left panel wider (approx 1:1.5)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1) # Equal stretch to make left side significantly larger
        
        # We can also set a minimum width for the left panel scroll area
        scroll_area.setMinimumWidth(400)
        
        layout.addWidget(splitter)
        
        # Initialize Logic
        self.inspector_logic = InspectorLogic()

        # Connections
        self.timeline.enable_range_selection(True)

    def _style_danger_button(self, btn: QPushButton):
        btn.setStyleSheet("""
            QPushButton {
                background-color: #DC3545; /* Red */
                color: white;
            }
            QPushButton:hover {
                background-color: #c82333;
            }
            QPushButton:pressed {
                background-color: #bd2130;
            }
        """)

    def _style_secondary_button(self, btn: QPushButton):
        btn.setStyleSheet("""
            QPushButton {
                background-color: #6c757d; /* Gray */
                color: white;
            }
            QPushButton:hover {
                background-color: #5a6268;
            }
            QPushButton:pressed {
                background-color: #545b62;
            }
        """)

    def create_rule_group(self):
        rule_group = QGroupBox("Add Validation Rule")
        # QGroupBox styling is handled in QSS
        rule_layout = QVBoxLayout(rule_group)
        rule_layout.setSpacing(12)
        rule_layout.setContentsMargins(15, 20, 15, 15)
        
        # Rule Form
        form_layout = QHBoxLayout()
        form_layout.setSpacing(10)
        
        self.rule_topic_combo = QComboBox()
        self.rule_topic_combo.setEditable(True)
        self.rule_topic_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.rule_topic_combo.completer().setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self.rule_topic_combo.completer().setFilterMode(Qt.MatchFlag.MatchContains)
        self.rule_topic_combo.setPlaceholderText("Topic")
        self.rule_topic_combo.currentIndexChanged.connect(self.on_rule_topic_selection_changed)
        
        self.rule_value_input = QLineEdit()
        self.rule_value_input.setPlaceholderText("Target Value")
        self.rule_value_input.setFixedWidth(120)
        
        form_layout.addWidget(QLabel("Topic:"))
        form_layout.addWidget(self.rule_topic_combo, 2)
        form_layout.addWidget(QLabel("Value:"))
        form_layout.addWidget(self.rule_value_input, 1)
        
        rule_layout.addLayout(form_layout)
        
        # Rule Type (Must vs Should Not vs Exist)
        type_layout = QHBoxLayout()
        type_layout.setSpacing(15)
        self.bg_rule_type = QButtonGroup(self)
        self.rb_must = QRadioButton("Must (Match)")
        self.rb_must.setCursor(Qt.CursorShape.PointingHandCursor)
        self.rb_should_not = QRadioButton("Should Not (No Match)")
        self.rb_should_not.setCursor(Qt.CursorShape.PointingHandCursor)
        self.rb_exist = QRadioButton("Exist (At least once)")
        self.rb_exist.setCursor(Qt.CursorShape.PointingHandCursor)
        
        self.rb_must.setChecked(True)
        self.bg_rule_type.addButton(self.rb_must)
        self.bg_rule_type.addButton(self.rb_should_not)
        self.bg_rule_type.addButton(self.rb_exist)
        self.rb_maybe = QRadioButton("Maybe")
        self.rb_maybe.setCursor(Qt.CursorShape.PointingHandCursor)
        self.rb_maybe.toggled.connect(self.on_rule_type_toggled)
        self.bg_rule_type.addButton(self.rb_maybe)
        
        type_layout.addWidget(self.rb_must)
        type_layout.addWidget(self.rb_should_not)
        type_layout.addWidget(self.rb_exist)
        type_layout.addWidget(self.rb_maybe)
        
        # Tolerance Input for Maybe
        type_layout.addWidget(QLabel("Tolerance(s):"))
        self.rule_tolerance_input = QLineEdit("0.0")
        from PyQt6.QtGui import QDoubleValidator
        self.rule_tolerance_input.setValidator(QDoubleValidator(0.0, 10.0, 2))
        self.rule_tolerance_input.setEnabled(False)
        self.rule_tolerance_input.setFixedWidth(60)
        type_layout.addWidget(self.rule_tolerance_input)
        type_layout.addStretch()
        
        add_rule_btn = QPushButton("Add Rule")
        add_rule_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_rule_btn.clicked.connect(self.add_rule)
        type_layout.addWidget(add_rule_btn)
        
        # OR Rule Button
        or_rule_btn = QPushButton("Add OR Rule")
        or_rule_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        or_rule_btn.clicked.connect(self.open_or_rule_dialog)
        type_layout.addWidget(or_rule_btn)
        
        # Macro Setup Button
        macro_btn = QPushButton("Macro Setup")
        macro_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        macro_btn.clicked.connect(self.open_macro_dialog)
        type_layout.addWidget(macro_btn)
        
        rule_layout.addLayout(type_layout)
        
        # Rules List Table
        self.rules_table = QTableWidget()
        self.rules_table.setColumnCount(7)
        self.rules_table.setHorizontalHeaderLabels(["Start", "End", "Topic", "Cond", "Value", "Tol(s)", "Delete"])
        self.rules_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        # Resize Action column to be smaller
        self.rules_table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        
        self.rules_table.cellChanged.connect(self.on_rule_changed)
        self.rules_table.itemSelectionChanged.connect(self.on_rule_selection_changed)
        rule_layout.addWidget(self.rules_table)
        
        # Buttons Layout
        btn_layout = QHBoxLayout()
        # Eval Button
        eval_btn = QPushButton("Run Evaluation")
        eval_btn.clicked.connect(self.run_evaluation)
        btn_layout.addWidget(eval_btn)
        
        rule_layout.addLayout(btn_layout)
        
        return rule_group

    def update_rule_topics(self):
        self.rule_topic_combo.clear()
        self.rule_topic_combo.addItems(self.data_loader.get_topics())

    def add_rule(self):
        topic = self.rule_topic_combo.currentText()
        value = self.rule_value_input.text()
        start, end = self.timeline.get_selected_range()
        
        if not topic or not value:
            QMessageBox.warning(self, "Input Error", "Please select a topic and enter a value.")
            return

        tolerance = 0.0
        if self.rb_must.isChecked():
            rule_type = RuleType.MUST
        elif self.rb_should_not.isChecked():
            rule_type = RuleType.SHOULD_NOT
        elif self.rb_maybe.isChecked():
            rule_type = RuleType.MAYBE
            try:
                tolerance = float(self.rule_tolerance_input.text())
            except:
                tolerance = 0.0
        else:
            rule_type = RuleType.EXIST
        
        rule = Rule(start, end, topic, value, rule_type, tolerance)
        self.inspector_logic.add_rule(rule)
        
        self.refresh_rules_table()
        
        # Auto-add topic to visualization
        if topic not in self.selected_topics:
            self.add_topic_to_table(topic)

    def on_rule_type_toggled(self):
        # Enable tolerance input only if 'Maybe' is selected
        self.rule_tolerance_input.setEnabled(self.rb_maybe.isChecked())
        
    def delete_rule_at(self, index):
        self.inspector_logic.remove_rule(index)
        self.refresh_rules_table()

    def open_or_rule_dialog(self):
        # Collect all available topics from data_loader
        topics = self.data_loader.get_topics() if self.data_loader else []
        dlg = ORRuleDialog(topics, self)
        if dlg.exec():
            conditions = dlg.get_conditions()
            if not conditions: return
            
            start, end = self.timeline.get_selected_range()
            
            # format lists
            topics_list = [c[0] for c in conditions]
            values_list = [c[1] for c in conditions]
            
            rule = Rule(start, end, topics_list, values_list, RuleType.MUST_OR)
            self.inspector_logic.add_rule(rule)
            self.refresh_rules_table()
            
            # Add all topics to visualization
            for t in topics_list:
                self.add_topic_to_table(t)
            
            QMessageBox.information(self, "Success", f"OR Rule with {len(conditions)} conditions added.")

    def on_rule_changed(self, row, col):
        # ["Start", "End", "Topic", "Cond", "Value", "Tol(s)"]
        # Attributes: start_time, end_time, topic, rule_type, target_value, tolerance
        item = self.rules_table.item(row, col)
        if item is None:
            return

        val = item.text()
        rules = self.inspector_logic.get_rules()
        if row >= len(rules):
            return

        rule = rules[row]

        try:
            updates = {}
            if col == 0:
                updates['start_time'] = float(val)
            elif col == 1:
                updates['end_time'] = float(val)
            elif col == 2:
                if rule.rule_type == RuleType.MUST_OR:
                    updates['topic'] = [t.strip() for t in val.split('|') if t.strip()]
                else:
                    updates['topic'] = val
            elif col == 3:
                if val in [RuleType.MUST, RuleType.SHOULD_NOT, RuleType.EXIST, RuleType.MUST_OR, RuleType.MAYBE]:
                    updates['rule_type'] = val
            elif col == 4:
                if rule.rule_type == RuleType.MUST_OR:
                    updates['target_value'] = [v.strip() for v in val.split('|') if v.strip()]
                else:
                    updates['target_value'] = val
            elif col == 5:
                updates['tolerance'] = float(val)

            if updates:
                self.inspector_logic.update_rule(row, **updates)
                if 'topic' in updates:
                    topics = updates['topic'] if isinstance(updates['topic'], list) else [updates['topic']]
                    for topic in topics:
                        self.add_topic_to_table(topic)
        except Exception as e:
            QMessageBox.warning(self, "Rule Update Error", f"Failed to update rule:\n{e}")
            self.refresh_rules_table()

    def on_rule_topic_selection_changed(self, index):
        topic = self.rule_topic_combo.currentText()
        if topic and topic not in self.selected_topics:
            self.add_topic_to_table(topic)

    def on_rule_selection_changed(self):
        selected_items = self.rules_table.selectedItems()
        if not selected_items: return
        
        # Get the first selected item's row
        row = selected_items[0].row()
        rules = self.inspector_logic.get_rules()
        if row >= len(rules): return
        rule = rules[row]

        # 1. Sync Timeline Range
        self.timeline.set_selected_range(rule.start_time, rule.end_time)

        # 2. Add topic(s) to visualization
        topic_item = self.rules_table.item(row, 2) # Topic is col 2
        if topic_item:
            topic_str = topic_item.text()
            # If it's an OR rule, it displays as "A | B"
            topics = [t.strip() for t in topic_str.split('|')]
            for t in topics:
                if t and t not in self.selected_topics:
                    self.add_topic_to_table(t)

    def refresh_rules_table(self):
        self.rules_table.blockSignals(True)
        rules = self.inspector_logic.get_rules()
        self.rules_table.setRowCount(len(rules))
        for i, r in enumerate(rules):
            self.rules_table.setItem(i, 0, QTableWidgetItem(f"{r.start_time:.2f}"))
            self.rules_table.setItem(i, 1, QTableWidgetItem(f"{r.end_time:.2f}"))
            
            # Topic Display
            from core.logic import RuleType
            if r.rule_type == RuleType.MUST_OR:
                topic_str = " | ".join(r.topic) if isinstance(r.topic, list) else str(r.topic)
                val_str = " | ".join(map(str, r.target_value)) if isinstance(r.target_value, list) else str(r.target_value)
            else:
                topic_str = str(r.topic)
                val_str = str(r.target_value)
                
            self.rules_table.setItem(i, 2, QTableWidgetItem(topic_str))
            self.rules_table.setItem(i, 3, QTableWidgetItem(r.rule_type))
            self.rules_table.setItem(i, 4, QTableWidgetItem(val_str))
            
            # Tolerance Column
            tol_val = f"{r.tolerance:.2f}" if hasattr(r, 'tolerance') else "0.00"
            self.rules_table.setItem(i, 5, QTableWidgetItem(tol_val))
            
            # Delete Button
            del_btn = QPushButton("Delete")
            del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self._style_danger_button(del_btn)
            # Use lambda with default argument to capture 'i' correctly
            del_btn.clicked.connect(lambda checked, idx=i: self.delete_rule_at(idx))
            
            # Container to center the button
            container = QWidget()
            layout = QHBoxLayout(container)
            layout.setContentsMargins(0,0,0,0)
            layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(del_btn)
            
            self.rules_table.setCellWidget(i, 6, container)
            
        self.rules_table.blockSignals(False)

    def run_evaluation(self):
        results = self.inspector_logic.check_rules(self.data_loader)

        fail_messages = []
        skip_count = 0
        error_messages = []

        for res in results:
            if res['status'] == 'FAIL':
                fail_messages.append(f"FAIL: {res['rule_desc']} at frames {res['fail_frames'][:5]}...")
            elif res['status'] == 'SKIP':
                skip_count += 1
            elif res['status'] == 'ERROR':
                error_messages.append(res.get('msg', res['rule_desc']))

        if error_messages:
            QMessageBox.critical(self, "Evaluation Error", "\n".join(error_messages))
            return

        if fail_messages:
            summary = "\n".join(fail_messages)
            if skip_count:
                summary += f"\n\nSkipped rules: {skip_count}"
            QMessageBox.warning(self, "Result", f"{len(fail_messages)} rules FAILED.\n\n{summary}")
            return

        if skip_count:
            QMessageBox.information(self, "Result", f"All evaluated rules PASSED!\nSkipped rules: {skip_count}")
        else:
            QMessageBox.information(self, "Result", "All rules PASSED!")

    def open_master_config_dialog(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "Open Master Config", "", "JSON Files (*.json)")
        if file_name:
            try:
                self.inspector_logic.load_master_config(file_name)
                QMessageBox.information(self, "Success", f"Master Config loaded:\n{os.path.basename(file_name)}")
                # If an excel file is already open, try to reload its config from the new master
                if self.current_excel_path:
                     self._load_config_for_current_excel()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load master config: {e}")

    def open_macro_dialog(self):
        macros = self.inspector_logic.get_macros()
        dlg = MacroDialog(macros, self)
        if dlg.exec():
            if dlg.add_requested:
                # User wants to save CURRENT rules as a macro
                rules = self.inspector_logic.get_rules()
                if not rules:
                    QMessageBox.warning(self, "Empty Rules", "No rules to save as macro.")
                    return
                
                self.inspector_logic.add_macro(
                    dlg.new_macro_info['name'],
                    dlg.new_macro_info['description'],
                    rules
                )
                QMessageBox.information(self, "Success", f"Macro '{dlg.new_macro_info['name']}' saved successfully.")
                return

            macro = dlg.selected_macro
            if macro:
                try:
                    rules_to_add = macro.get('rules', [])
                    # Support legacy single-rule macros
                    if not rules_to_add and 'topic' in macro:
                        rules_to_add = [macro]

                    for r_data in rules_to_add:
                        # Unify keys (support both legacy/code-defined and saved-to-json formats)
                        start = r_data.get('start') if 'start' in r_data else r_data.get('start_time')
                        end = r_data.get('end') if 'end' in r_data else r_data.get('end_time')
                        value = r_data.get('value') if 'value' in r_data else r_data.get('target_value')
                        
                        rule = Rule(
                            start,
                            end,
                            r_data['topic'],
                            value,
                            r_data['rule_type'],
                            r_data.get('tolerance', 0.0)
                        )
                        self.inspector_logic.add_rule(rule)
                        
                        # Fix: Handle list of topics for OR rules
                        ts = r_data['topic'] if isinstance(r_data['topic'], list) else [r_data['topic']]
                        for t in ts:
                            self.add_topic_to_table(t)
                    
                    self.refresh_rules_table()
                    QMessageBox.information(self, "Success", f"Macro '{macro['name']}' applied ({len(rules_to_add)} rules).")
                except Exception as e:
                    QMessageBox.warning(self, "Error", f"Failed to apply macro: {e}")

    def save_config(self):
        if not self.current_excel_path:
             QMessageBox.warning(self, "Error", "No Excel file loaded.")
             return

        # Update metadata from UI
        self.inspector_logic.metadata["vehicle"] = self.input_vehicle.text()
        self.inspector_logic.metadata["sw_ver"] = self.input_sw_ver.text()
        self.inspector_logic.metadata["test_date"] = self.input_date.date().toString(Qt.DateFormat.ISODate)
        
        # New Metadata
        cats = [self.category_list.item(i).text() for i in range(self.category_list.count())]
        self.inspector_logic.metadata["categories"] = cats
        self.inspector_logic.metadata["tc_number"] = self.input_tc_num.text()
        self.inspector_logic.metadata["note"] = self.input_note.toPlainText()

        # Check if master config is loaded
        if not self.inspector_logic.master_config_path:
             # Prompt to create/save master config
             file_name, _ = QFileDialog.getSaveFileName(self, "Create Master Config", "master_config.json", "JSON Files (*.json)")
             if file_name:
                 self.inspector_logic.master_config_path = file_name
                 self.inspector_logic.master_config_data = {} # Initialize empty
             else:
                 return # Cancelled

        # Save to Master Config
        try:
            file_stem = os.path.splitext(os.path.basename(self.current_excel_path))[0]
            self.inspector_logic.update_master_config(file_stem)
            QMessageBox.information(self, "Success", f"Configuration for '{file_stem}' saved to master config.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save to master config: {e}")

    def load_excel_file(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "Open Excel File", "", "Excel/CSV Files (*.xlsx *.xls *.csv)")
        if file_name:
            # Single file mode - Reset list
            self.file_list = [file_name]
            self.current_file_index = 0
            self._update_file_dropdown_ui()
            self._load_file_from_path(file_name)

    def load_folder_dialog(self):
        folder_path = QFileDialog.getExistingDirectory(self, "Select Folder")
        if folder_path:
            self.scan_folder_for_excel(folder_path)

    def scan_folder_for_excel(self, folder_path):
        excel_files = []
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                if file.lower().endswith(('.xlsx', '.xls', '.csv')):
                    full_path = os.path.join(root, file)
                    excel_files.append(full_path)
        
        if not excel_files:
            QMessageBox.warning(self, "No Files", "No Excel files found in selected folder.")
            return

        # Sort alphabetically
        self.file_list = sorted(excel_files)
        
        # Populate Dropdown
        self._update_file_dropdown_ui()
        
        # Load first file
        if self.file_list:
            self.current_file_index = 0
            if self.file_dropdown.currentIndex() != 0:
                self.file_dropdown.setCurrentIndex(0) 
            # Force load because if index was already 0 (default), setCurrentIndex(0) won't trigger signal
            self._load_file_from_path(self.file_list[0])

    def load_dat_folder_dialog(self):
        folder_path = QFileDialog.getExistingDirectory(self, "Select DAT Folder")
        if folder_path:
            self.scan_folder_for_dat(folder_path)

    def scan_folder_for_dat(self, folder_path):
        self.dat_folder_path = folder_path
        self.dat_file_map.clear()
        count = 0
        
        def resolve_lnk(lnk_path):
            try:
                import win32com.client
                shell = win32com.client.Dispatch("WScript.Shell")
                shortcut = shell.CreateShortcut(lnk_path)
                return shortcut.Targetpath
            except Exception as e:
                QMessageBox.warning(self, "Shortcut Resolve Error", f"Could not resolve shortcut:\n{lnk_path}\n\n{e}")
                return None

        for root, dirs, files in os.walk(folder_path):
            for file in files:
                full_path = os.path.join(root, file)
                if file.lower().endswith('.lnk'):
                    target_path = resolve_lnk(full_path)
                    if target_path and os.path.exists(target_path):
                        if os.path.isdir(target_path):
                            for sub_root, _, sub_files in os.walk(target_path):
                                for sub_file in sub_files:
                                    if sub_file.lower().endswith('.dat'):
                                        base_name = os.path.splitext(sub_file)[0]
                                        self.dat_file_map[base_name.lower()] = os.path.realpath(os.path.join(sub_root, sub_file))
                                        count += 1
                        elif target_path.lower().endswith('.dat'):
                            base_name = os.path.splitext(os.path.basename(target_path))[0]
                            self.dat_file_map[base_name.lower()] = os.path.realpath(target_path)
                            count += 1
                elif file.lower().endswith('.dat'):
                    base_name = os.path.splitext(file)[0]
                    self.dat_file_map[base_name.lower()] = full_path
                    count += 1
        
        if count == 0:
            QMessageBox.warning(self, "No Files", "No .dat files found in selected folder.")
        else:
            QMessageBox.information(self, "DAT Folder Loaded", f"Found {count} .dat files.\nThey will load automatically when matching Excel files are selected.")
            
            # If an excel file is already open, try to match it inside the newly selected DAT folder
            if self.current_excel_path:
                self._match_and_load_dat()

    def _update_file_dropdown_ui(self):
        self.file_dropdown.blockSignals(True)
        self.file_dropdown.clear()
        items = [f"{os.path.basename(f)} ({os.path.dirname(f)})" for f in self.file_list]
        self.file_dropdown.addItems(items)
        if 0 <= self.current_file_index < len(self.file_list):
             self.file_dropdown.setCurrentIndex(self.current_file_index)
        self.file_dropdown.blockSignals(False)

    def on_file_dropdown_changed(self, index):
        if 0 <= index < len(self.file_list):
            self.current_file_index = index
            self._load_file_from_path(self.file_list[index])

    def load_next_file(self):
        if not self.file_list: return
        new_index = self.current_file_index + 1
        if new_index < len(self.file_list):
            self.file_dropdown.setCurrentIndex(new_index)
        else:
             QMessageBox.information(self, "Info", "This is the last file.")

    def load_prev_file(self):
        if not self.file_list: return
        new_index = self.current_file_index - 1
        if new_index >= 0:
            self.file_dropdown.setCurrentIndex(new_index)
        else:
             QMessageBox.information(self, "Info", "This is the first file.")
    
    def navigate_adtf_next(self):
        """Navigate to next frame in ADTF image display"""
        if hasattr(self, 'adtf_display'):
            self.adtf_display.navigate_next()
    
    def navigate_adtf_previous(self):
        """Navigate to previous frame in ADTF image display"""
        if hasattr(self, 'adtf_display'):
            self.adtf_display.navigate_previous()

    def setup_shortcuts(self):
        # QShortcut(QKeySequence("Ctrl+Q"), self, activated=self.load_prev_file)
        # QShortcut(QKeySequence("Ctrl+E"), self, activated=self.load_next_file)
        
        self.shortcut_prev = QShortcut(QKeySequence("Ctrl+Q"), self)
        self.shortcut_prev.setContext(Qt.ShortcutContext.ApplicationShortcut)
        self.shortcut_prev.activated.connect(self.load_prev_file)
        
        self.shortcut_next = QShortcut(QKeySequence("Ctrl+E"), self)
        self.shortcut_next.setContext(Qt.ShortcutContext.ApplicationShortcut)
        self.shortcut_next.activated.connect(self.load_next_file)

        self.shortcut_recent = QShortcut(QKeySequence("Ctrl+R"), self)
        self.shortcut_recent.setContext(Qt.ShortcutContext.ApplicationShortcut)
        self.shortcut_recent.activated.connect(self.load_recent_config)
        
        self.shortcut_save = QShortcut(QKeySequence("Ctrl+S"), self)
        self.shortcut_save.setContext(Qt.ShortcutContext.ApplicationShortcut)
        self.shortcut_save.activated.connect(self.save_config)
        
        # Spacebar shortcut for ADTF image navigation
        self.shortcut_space = QShortcut(QKeySequence(Qt.Key.Key_Space), self)
        self.shortcut_space.activated.connect(self.navigate_adtf_next)

    def add_topic(self):
        topic = self.topic_combo.currentText()
        if not topic:
            return
            
        # Check duplicates
        for i in range(self.topic_table.rowCount()):
             if self.topic_table.item(i, 0).text() == topic:
                 return

        # Add to Table
        row = self.topic_table.rowCount()
        self.topic_table.insertRow(row)
        
        # Topic Name
        self.topic_table.setItem(row, 0, QTableWidgetItem(topic))
        
        # Plot # SpinBox
        spin = QSpinBox()
        spin.setRange(1, 10)
        spin.setValue(1)
        spin.valueChanged.connect(self.update_plot) # Trigger plot update on change
        self.topic_table.setCellWidget(row, 1, spin)
        
        if topic not in self.selected_topics:
            self.selected_topics.append(topic)
        
        self.update_plot()
    
    def delete_topic(self):
        rows = sorted(set(index.row() for index in self.topic_table.selectedIndexes()), reverse=True)
        for row in rows:
            topic = self.topic_table.item(row, 0).text()
            if topic in self.selected_topics:
                self.selected_topics.remove(topic)
            self.topic_table.removeRow(row)
            
        self.update_plot()

    def add_category(self):
        cat = self.input_category_combo.currentText()
        # check duplicates in list
        existing = [self.category_list.item(i).text() for i in range(self.category_list.count())]
        if cat not in existing:
            self.category_list.addItem(cat)
            
    def delete_category(self):
        row = self.category_list.currentRow()
        if row >= 0:
            self.category_list.takeItem(row)

    def update_plot(self):
        # Prepare data for all selected topics
        time_axis = self.data_loader.get_time_axis()
        
        # If no time_axis, clear and return (unless we want to support no-time plotting?)
        if time_axis is None or len(time_axis) == 0:
            self.timeline.plot_topics([], {}) # Clear
            return

        # If no selected topics, also clear
        if not self.selected_topics:
            self.timeline.plot_topics(time_axis, {})
            return
            
        data_dict = {}
        plot_map = {}
        
        for i in range(self.topic_table.rowCount()):
            topic = self.topic_table.item(i, 0).text()
            spin = self.topic_table.cellWidget(i, 1)
            plot_id = spin.value() if spin else 1
            
            vals = self.data_loader.get_data_for_topic(topic)
            if vals is not None:
                data_dict[topic] = vals
                plot_map[topic] = plot_id
                
        self.timeline.plot_topics(time_axis, data_dict, plot_map)

    def on_time_changed(self, time_val, frame_idx):
        # Update display label with values of selected topics at this frame
        info_text = f"Time: {time_val:.3f}s | Frame: {frame_idx}  "
        
        values = []
        for topic in self.selected_topics:
            val = self.data_loader.get_value_at_time_index(topic, frame_idx)
            values.append(f"{topic}: {val}")
        
        if values:
            info_text += " | ".join(values)
            
        self.data_display_label.setText(info_text)
    
    def on_adtf_frame_changed(self, current_index, total_frames):
        """Handle ADTF frame change events"""
        pass

    def open_batch_dialog(self):
        if self.batch_dialog is None:
            self.batch_dialog = BatchResultDialog(self)
        
        self.batch_dialog.show()
        self.batch_dialog.raise_()
        self.batch_dialog.activateWindow()

    def inspect_from_batch(self, file_path):
        """
        Called from BatchResultDialog to inspect a specific file.
        """
        if not os.path.exists(file_path):
            QMessageBox.warning(self, "Error", f"File does not exist: {file_path}")
            return
            
        self._load_file_from_path(file_path)

    def _load_file_from_path(self, file_name):
        # Save current state before loading new one (if we have a current file)
        if self.current_excel_path:
             self.save_current_state_to_recent()

        self.current_excel_path = file_name
        self.file_label.setText(os.path.basename(file_name))
        try:
            self.data_loader.load_file(file_name)
            
            # Populate Topic Dropdown
            topics = self.data_loader.get_topics()
            self.topic_combo.clear()
            self.topic_combo.addItems(topics)
            
            self.rule_topic_combo.clear()
            self.rule_topic_combo.addItems(topics)
            self.rule_topic_combo.setCurrentIndex(-1) # No default selection
            
            # Clear current selection
            self.selected_topics = []
            self.topic_table.setRowCount(0) # Clear table
            
            # Initialize Time Axis
            time_axis = self.data_loader.get_time_axis()
            self.timeline.set_fs(self.data_loader.time_step)
            self.timeline.set_time_axis(time_axis)
            
            # Load Config from Master if available
            self._load_config_for_current_excel()
            
            # Force update plot (will clear if no topics selected)
            self.update_plot()
            
            # Attempt to find and auto-load matching DAT file
            self._match_and_load_dat()
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load file: {str(e)}")

    def _match_and_load_dat(self):
        """Attempts to match current excel file with a DAT file and load it."""
        if not self.current_excel_path or not self.dat_file_map:
            return
            
        # Example logic: AAAA_lgresult.csv -> AAAA
        base_filename = os.path.basename(self.current_excel_path)
        name_without_ext = os.path.splitext(base_filename)[0]
        
        # Common suffix removal, adjust as needed depending on naming conventions
        name_lower = name_without_ext.lower()
        if name_lower.endswith("_lgeresult"):
            target_dat_name = name_without_ext[:-10]  # Remove '_lgeresult' (10 chars)
        elif name_lower.endswith("_lgresult"):
            target_dat_name = name_without_ext[:-9]   # Fallback for old name
        else:
            target_dat_name = name_without_ext
            
        target_lookup = target_dat_name.lower()
            
        if target_lookup in self.dat_file_map:
            matched_path = self.dat_file_map[target_lookup]

            if hasattr(self, 'adtf_display'):
                try:
                    self.adtf_display.load_adtf_file_from_path(matched_path)
                except Exception as e:
                    QMessageBox.critical(self, "DAT Load Error", f"Failed to load DAT file:\n{matched_path}\n\n{e}")

    def _load_config_for_current_excel(self):
        if not self.current_excel_path:
            return
            
        file_stem = os.path.splitext(os.path.basename(self.current_excel_path))[0]
        config_data = self.inspector_logic.get_config_for_file(file_stem)
        
        if config_data:
            try:
                self.inspector_logic.load_config_from_dict(config_data)
                self.refresh_rules_table()
                
                # Load Metadata to UI
                meta = self.inspector_logic.metadata
                self.input_vehicle.setText(meta.get("vehicle", ""))
                self.input_sw_ver.setText(meta.get("sw_ver", ""))
                
                date_str = meta.get("test_date", "")
                if date_str:
                    self.input_date.setDate(QDate.fromString(date_str, Qt.DateFormat.ISODate))
                else:
                    self.input_date.setDate(QDate.currentDate())
                    
                # Extended Metadata
                self.category_list.clear() # Clear list first
                for cat in meta.get("categories", []):
                    self.category_list.addItem(cat)
                
                self.input_tc_num.setText(meta.get("tc_number", ""))
                self.input_note.setPlainText(meta.get("note", ""))
                
                # Auto-add topics from rules to the plot table
                # We can infer topics from rules
                all_topics = []
                for r in self.inspector_logic.rules:
                    if isinstance(r.topic, list):
                        all_topics.extend(r.topic)
                    else:
                        all_topics.append(r.topic)
                
                for topic in set(all_topics):
                    self.add_topic_to_table(topic)
                    
                # Note: We don't show success msg for auto-load to avoid spam, 
                # unless explicitly requested or if it's the first load
                print(f"Loaded config for {file_stem} from master.")

            except Exception as e:
                 QMessageBox.warning(self, "Warning", f"Found config in master but failed to load: {e}")
        else:
            # Clear/Default UI if no config
            self.inspector_logic.metadata = {
                "vehicle": "", "sw_ver": "", "test_date": "",
                "categories": [], "tc_number": "", "note": ""
            }
            self.inspector_logic.rules = [] # Clear rules
            self.input_vehicle.clear()
            self.input_sw_ver.clear()
            self.input_date.setDate(QDate.currentDate())
            self.category_list.clear()
            self.input_tc_num.clear()
            self.input_note.clear()
            self.refresh_rules_table() # Clear rules
            
            # QMessageBox.information(self, "Info", f"No config found for {file_stem} in master config.")

    def add_topic_to_table(self, topic, plot_id=1):
        if not topic: return
        # Check duplicates
        for i in range(self.topic_table.rowCount()):
             if self.topic_table.item(i, 0).text() == topic:
                 return

        row = self.topic_table.rowCount()
        self.topic_table.insertRow(row)
        self.topic_table.setItem(row, 0, QTableWidgetItem(topic))
        
        spin = QSpinBox()
        spin.setButtonSymbols(QSpinBox.ButtonSymbols.NoButtons)
        spin.setRange(1, 10)
        spin.setValue(plot_id)
        spin.valueChanged.connect(self.update_plot)
        self.topic_table.setCellWidget(row, 1, spin)
        
        self.selected_topics.append(topic)
        # We delay update_plot until caller calls it or let it trigger
        self.update_plot()

    def save_current_state_to_recent(self):
        """Save the current UI state/rules to recent_config variable."""
        if not self.current_excel_path:
             return

        # Gather Metadata
        cats = [self.category_list.item(i).text() for i in range(self.category_list.count())]
        
        # Gather Rules
        rules_data = [rule.to_dict() for rule in self.inspector_logic.rules]

        self.recent_config = {
            "vehicle": self.input_vehicle.text(),
            "sw_ver": self.input_sw_ver.text(),
            "test_date": self.input_date.date().toString(Qt.DateFormat.ISODate),
            "categories": cats,
            "tc_number": self.input_tc_num.text(),
            "note": self.input_note.toPlainText(),
            "rules": rules_data,
            "selected_topics": list(self.selected_topics) # Copy list
        }

    def load_recent_config(self):
        if not self.recent_config:
            QMessageBox.warning(self, "Warning", "No recent configuration saved.")
            return
            
        try:
            # 1. Restore Metadata
            data = self.recent_config
            self.input_vehicle.setText(data.get("vehicle", ""))
            self.input_sw_ver.setText(data.get("sw_ver", ""))
            
            date_str = data.get("test_date", "")
            if date_str:
                self.input_date.setDate(QDate.fromString(date_str, Qt.DateFormat.ISODate))
            
            self.category_list.clear()
            for cat in data.get("categories", []):
                self.category_list.addItem(cat)
                
            self.input_tc_num.setText(data.get("tc_number", ""))
            self.input_note.setPlainText(data.get("note", ""))
            
            # 2. Restore Topics
            available_topics = self.data_loader.get_topics()
            saved_topics = data.get("selected_topics", [])
            
            for topic in saved_topics:
                if topic in available_topics:
                     self.add_topic_to_table(topic)
            
            # 3. Restore Rules
            self.inspector_logic.rules = [] # Clear current rules
            saved_rules = data.get("rules", [])
            for r_data in saved_rules:
                # Add rule
                new_rule = Rule.from_dict(r_data)
                self.inspector_logic.add_rule(new_rule)
            
            self.refresh_rules_table()
            
            # Sync metadata to logic
            self.inspector_logic.metadata["vehicle"] = data.get("vehicle", "")
            self.inspector_logic.metadata["sw_ver"] = data.get("sw_ver", "")
            self.inspector_logic.metadata["test_date"] = data.get("test_date", "")
            self.inspector_logic.metadata["categories"] = data.get("categories", [])
            self.inspector_logic.metadata["tc_number"] = data.get("tc_number", "")
            self.inspector_logic.metadata["note"] = data.get("note", "")
            
            QMessageBox.information(self, "Success", "Loaded recent configuration.")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load recent config: {e}")

    def show_guide_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("SILS Validator - 사용 가이드")
        dialog.setMinimumSize(850, 650)
        
        layout = QVBoxLayout(dialog)
        
        scroll_area = QScrollArea(dialog)
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        
        guide_text = """
        <h3>💡 &lt; SILS Validator - 사용 가이드 &gt;</h3>

        <b>1. 툴의 목적</b><br>
        본 툴은 기존 취득된 dat파일을 신규 SW로 SILS 재검증하고, 사용자가 정의한 특정 조건(Rule)이 올바르게 동작했는지 자동으로 검증(Validation)하기 위해 제작되었습니다.<br><br>

        <b>2. 기본 사용 방법</b><br>
        - <b>Config 불러오기</b>: 기존 설정된 Rule 파일을 <code>[Load Master Config]</code> 버튼을 통해 불러옵니다.<br>
        - <b>데이터 불러오기</b>: 상단의 <code>[Select File]</code> 또는 <code>[Select Folder]</code>로 신규 SW SILS로 취득된 lgeresult파일을 선택합니다. 주행 카메라 영상을 함께 보려면 <code>[Select DAT Folder]</code>를 눌러 영상 폴더를 지정하세요.<br>
        - 자동으로 lgeresult 파일과 dat파일 이름을 매칭하여 이미지가 표시됩니다.<br>
        - <b>Test Information</b>: 차종, 버전, 평가일, 카테고리 등 기록을 남기고 우측 상단의 <code>[Save Master Config]</code> 버튼을 통해 내용을 저장합니다.<br>
        - <b>Topics 확인</b>: 좌측 패널에서 분석할 변수(Topic)를 체킹하면 중앙 그래프 화면에 시계열 데이터가 나타납니다.<br><br>

        <b>3. 영상 및 타임라인 컨트롤 (단축키)</b><br>
        영상 창(DAT Viewer)을 클릭한 상태에서 아래 단축키로 프레임을 빠르고 정밀하게 탐색할 수 있습니다.<br>
        &nbsp;&nbsp;&nbsp;• <code>Spacebar</code> : 영상 재생 및 일시정지<br>
        &nbsp;&nbsp;&nbsp;• <code>←</code> / <code>→</code> : 1 프레임 단위 이동<br>
        &nbsp;&nbsp;&nbsp;• <code>Shift + ← / →</code> : 10 프레임 이동<br>
        &nbsp;&nbsp;&nbsp;• <code>Ctrl + ← / →</code> : 30 프레임 (1초) 이동<br>
        &nbsp;&nbsp;&nbsp;• <code>Ctrl + Shift + ← / →</code> : 300 프레임 (10초) 이동<br>
        &nbsp;&nbsp;&nbsp;• <code>Ctrl + ↑ / ↓</code> : 현재 영상이 멈춘 프레임의 시간을 Rule 시작(Start) / 끝(End) 구간으로 즉석 지정<br><br>

        <b>4. 검증 Rule 추가 (Add Validation Rule)</b><br>
        Visualization & Inspector의 시간 축을 설정하세요. 그래프의 파란 범위를 조절하거나 아래의 수치를 직접 조절하세요.<br>
        Add Validation Rule에서 Topic, Target value, 검증 방법을 선택하여 <code>[Add Rule]</code>을 선택하세요.<br><br>
        &nbsp;&nbsp;&nbsp;• <b>Must</b>: 해당 구간에서 값이 대상 값과 100% 일치해야 함 (PASS)<br>
        &nbsp;&nbsp;&nbsp;• <b>ShouldNot</b>: 해당 구간에서 해당 값이 절대 나오지 않아야 함<br>
        &nbsp;&nbsp;&nbsp;• <b>Exist</b>: 해당 구간 내에서 값이 한 번이라도 나타나야 함<br>
        &nbsp;&nbsp;&nbsp;• <b>Maybe</b>: <code>Tolerance(초)</code>로 지정한 시간만큼은 값이 달라도 허용함<br>
        &nbsp;&nbsp;&nbsp;• <b>Must (OR)</b>: 지정된 여러 토픽/값 쌍 중 하나라도 만족하면 PASS 처리<br><br>

        <b>5. 설정 저장 및 일괄 처리</b><br>
        - 세팅한 Rule과 토픽 정보는 <code>[Save Master Config]</code>(<code>Ctrl+S</code>)를 통해 통합 저장됩니다.<br>
        - 이전 데이터의 설정을 그대로 시험해보고 싶다면 <code>Ctrl+R</code>을 누르세요.<br>
        - 다량의 파일을 한 번에 검증하고 싶을 때는 <code>[Batch Run]</code> 기능을 사용하시면 됩니다.<br>
        - 이전/이후 엑셀 파일을 선택하고 싶다면 상단의 버튼 혹은 <code>Ctrl+Q/E</code> 단축키를 사용하세요.
        """
        
        label = QLabel(guide_text)
        label.setTextFormat(Qt.TextFormat.RichText)
        label.setWordWrap(True)
        label.setStyleSheet("font-size: 14px; line-height: 1.6;")
        
        content_layout.addWidget(label)
        content_widget.setLayout(content_layout)
        scroll_area.setWidget(content_widget)
        
        layout.addWidget(scroll_area)
        
        close_btn = QPushButton("닫기")
        close_btn.clicked.connect(dialog.accept)
        close_btn.setMinimumHeight(40)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setStyleSheet("font-weight: bold; background-color: #28a745; color: white; border-radius: 5px;")
        
        layout.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        
        dialog.exec()
