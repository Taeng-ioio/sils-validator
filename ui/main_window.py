from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QLabel, QFileDialog, QComboBox, QListWidget, 
                             QMessageBox, QFrame, QSplitter, QLineEdit, QRadioButton, 
                             QButtonGroup, QTableWidget, QTableWidgetItem, QHeaderView,
                             QCompleter, QSlider, QDoubleSpinBox, QGroupBox, QDateEdit,
                             QPlainTextEdit, QSpinBox, QScrollArea)
from PyQt6.QtGui import QAction, QKeySequence, QShortcut
from PyQt6.QtCore import Qt, QDate
from core.data_loader import ExcelLoader
from core.logic import InspectorLogic, Rule, RuleType
import os

from ui.widgets import TimelineWidget
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
        self.file_list = [] # List of absolute paths
        self.current_file_index = -1
        self.file_list = [] # List of absolute paths
        self.current_file_index = -1
        self.recent_config = None
        self.batch_dialog = None

        self.init_ui()
        self.setup_shortcuts()

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
        
        # Batch Run Button
        batch_btn = QPushButton("Batch Run")
        batch_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        batch_btn.clicked.connect(self.open_batch_dialog)
        
        top_bar.addWidget(master_btn)
        top_bar.addWidget(load_btn)
        top_bar.addWidget(load_folder_btn)
        top_bar.addWidget(self.prev_btn)
        top_bar.addWidget(self.file_dropdown)
        top_bar.addWidget(self.next_btn)
        top_bar.addWidget(self.file_label)
        top_bar.addStretch()
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

        # Visualization Widget
        self.timeline = TimelineWidget()
        self.timeline.time_changed.connect(self.on_time_changed)
        viz_layout.addWidget(self.timeline) 
        
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
        val = self.rules_table.item(row, col).text()
        # Current rules
        rules = self.inspector_logic.get_rules()
        if row >= len(rules): return
        rule = rules[row]
        
        try:
            updates = {}
            if col == 0:
                updates['start_time'] = float(val)
            elif col == 1:
                updates['end_time'] = float(val)
            elif col == 2:
                if rule.rule_type == RuleType.MUST_OR:
                    updates['topic'] = [t.strip() for t in val.split('|')]
                else:
                    updates['topic'] = val
            elif col == 3:
                # Basic validation for Rule Type
                if val in [RuleType.MUST, RuleType.SHOULD_NOT, RuleType.EXIST, RuleType.MUST_OR, RuleType.MAYBE]:
                    updates['rule_type'] = val
            elif col == 4:
                if rule.rule_type == RuleType.MUST_OR:
                    updates['target_value'] = [v.strip() for v in val.split('|')]
                else:
                    updates['target_value'] = val
            elif col == 5:
                updates['tolerance'] = float(val)
            
            if updates:
                self.inspector_logic.update_rule(row, **updates)
                if 'topic' in updates:
                    ts = updates['topic'] if isinstance(updates['topic'], list) else [updates['topic']]
                    for t in ts:
                        self.add_topic_to_table(t)
        except Exception as e:
            # Revert or warn? For now just print/ignore to avoid annoying popups on partial edit
            print(f"Update failed: {e}")

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
        
        msg = ""
        fail_count = 0
        for res in results:
            if res['status'] == 'FAIL':
                fail_count += 1
                msg += f"FAIL: {res['rule_desc']} at frames {res['fail_frames'][:5]}...\n"
        
        if fail_count == 0:
            QMessageBox.information(self, "Result", "All rules PASSED!")
        else:
            QMessageBox.warning(self, "Result", f"{fail_count} rules FAILED.\n\n{msg}")

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

    def setup_shortcuts(self):
        # QShortcut(QKeySequence("Ctrl+Q"), self, activated=self.load_prev_file)
        # QShortcut(QKeySequence("Ctrl+E"), self, activated=self.load_next_file)
        
        self.shortcut_prev = QShortcut(QKeySequence("Ctrl+Q"), self)
        self.shortcut_prev.activated.connect(self.load_prev_file)
        
        self.shortcut_next = QShortcut(QKeySequence("Ctrl+E"), self)
        self.shortcut_next.activated.connect(self.load_next_file)

        self.shortcut_recent = QShortcut(QKeySequence("Ctrl+R"), self)
        self.shortcut_recent.activated.connect(self.load_recent_config)

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
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load file: {str(e)}")

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

