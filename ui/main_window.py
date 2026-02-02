from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QLabel, QFileDialog, QComboBox, QListWidget, 
                             QMessageBox, QFrame, QSplitter, QLineEdit, QRadioButton, 
                             QButtonGroup, QTableWidget, QTableWidgetItem, QHeaderView,
                             QCompleter, QSlider, QDoubleSpinBox, QGroupBox, QDateEdit,
                             QPlainTextEdit, QSpinBox)
from PyQt6.QtCore import Qt, QDate
from core.data_loader import ExcelLoader
from core.logic import InspectorLogic, Rule, RuleType
import os

from PyQt6.QtCore import Qt
from core.data_loader import ExcelLoader
from core.logic import InspectorLogic, Rule, RuleType
import os

from ui.widgets import TimelineWidget
from ui.batch_dialog import BatchResultDialog

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SILS-validator")
        self.resize(1200, 800)
        
        self.data_loader = ExcelLoader()
        self.selected_topics = []
        self.current_excel_path = None

        self.init_ui()

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
        
        load_btn = QPushButton("Select Excel File")
        load_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        load_btn.clicked.connect(self.load_excel_file)
        
        # Save Config Button (Auto Name)
        save_btn = QPushButton("Save Config (Auto)")
        save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        save_btn.clicked.connect(self.save_config)
        
        # Batch Run Button
        batch_btn = QPushButton("Batch Run")
        batch_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        batch_btn.clicked.connect(self.open_batch_dialog)
        
        top_bar.addWidget(load_btn)
        top_bar.addWidget(self.file_label)
        top_bar.addStretch()
        top_bar.addWidget(batch_btn)
        top_bar.addWidget(save_btn)
        
        layout.addLayout(top_bar)
        
        # Splitter for Main Content
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(2)
        
        # Left Panel: Topics
        left_panel = QFrame() # Changed to Frame for background/border style
        left_panel.setFrameShape(QFrame.Shape.NoFrame) # Let CSS handle it
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
        add_cat_btn.setFixedWidth(50)
        add_cat_btn.clicked.connect(self.add_category)
        cat_layout.addWidget(add_cat_btn)
        test_info_layout.addLayout(cat_layout)

        self.category_list = QListWidget()
        self.category_list.setFixedHeight(80) # Small height
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
        self.topic_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.topic_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        left_layout.addWidget(self.topic_table)
        
        delete_topic_btn = QPushButton("Delete Selected Topic")
        delete_topic_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._style_danger_button(delete_topic_btn)
        delete_topic_btn.clicked.connect(self.delete_topic)
        left_layout.addWidget(delete_topic_btn)
        
        # left_panel.setLayout(left_layout) # Added to layout directly above
        splitter.addWidget(left_panel)
        
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
        
        # Set Splitter Ratios
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 4)
        
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
        
        type_layout.addWidget(self.rb_must)
        type_layout.addWidget(self.rb_should_not)
        type_layout.addWidget(self.rb_exist)
        type_layout.addStretch()
        
        add_rule_btn = QPushButton("Add Rule")
        add_rule_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_rule_btn.clicked.connect(self.add_rule)
        type_layout.addWidget(add_rule_btn)
        
        rule_layout.addLayout(type_layout)
        
        # Rules List Table
        self.rules_table = QTableWidget()
        self.rules_table.setColumnCount(6)
        self.rules_table.setHorizontalHeaderLabels(["Start", "End", "Topic", "Cond", "Value", "Delete"])
        self.rules_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        # Resize Action column to be smaller
        self.rules_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        
        self.rules_table.cellChanged.connect(self.on_rule_changed)
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

        if self.rb_must.isChecked():
            rule_type = RuleType.MUST
        elif self.rb_should_not.isChecked():
            rule_type = RuleType.SHOULD_NOT
        else:
            rule_type = RuleType.EXIST
        
        rule = Rule(start, end, topic, value, rule_type)
        self.inspector_logic.add_rule(rule)
        
        self.refresh_rules_table()
        
    def delete_rule_at(self, index):
        self.inspector_logic.remove_rule(index)
        self.refresh_rules_table()

    def on_rule_changed(self, row, col):
        # ["Start", "End", "Topic", "Cond", "Value"]
        # Attributes: start_time, end_time, topic, rule_type, target_value
        val = self.rules_table.item(row, col).text()
        
        try:
            updates = {}
            if col == 0:
                updates['start_time'] = float(val)
            elif col == 1:
                updates['end_time'] = float(val)
            elif col == 2:
                updates['topic'] = val
            elif col == 3:
                # Basic validation for Rule Type
                if val in [RuleType.MUST, RuleType.SHOULD_NOT, RuleType.EXIST]:
                    updates['rule_type'] = val
            elif col == 4:
                updates['target_value'] = val
            
            if updates:
                self.inspector_logic.update_rule(row, **updates)
        except Exception as e:
            # Revert or warn? For now just print/ignore to avoid annoying popups on partial edit
            print(f"Update failed: {e}")

    def refresh_rules_table(self):
        self.rules_table.blockSignals(True)
        rules = self.inspector_logic.get_rules()
        self.rules_table.setRowCount(len(rules))
        for i, r in enumerate(rules):
            self.rules_table.setItem(i, 0, QTableWidgetItem(f"{r.start_time:.2f}"))
            self.rules_table.setItem(i, 1, QTableWidgetItem(f"{r.end_time:.2f}"))
            self.rules_table.setItem(i, 2, QTableWidgetItem(r.topic))
            self.rules_table.setItem(i, 3, QTableWidgetItem(r.rule_type))
            self.rules_table.setItem(i, 4, QTableWidgetItem(str(r.target_value)))
            
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
            
            self.rules_table.setCellWidget(i, 5, container)
            
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

        # Replace extension with .json
        base_name = os.path.splitext(self.current_excel_path)[0]
        json_path = base_name + ".json"
        
        try:
            self.inspector_logic.save_rules_to_json(json_path)
            QMessageBox.information(self, "Success", f"Configuration saved to:\n{os.path.basename(json_path)}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save: {e}")

    def load_excel_file(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "Open Excel File", "", "Excel Files (*.xlsx *.xls)")
        if file_name:
            self._load_file_from_path(file_name)

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
        if time_axis is None and self.selected_topics:
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
        dlg = BatchResultDialog(self)
        dlg.exec()

    def inspect_from_batch(self, file_path):
        """
        Called from BatchResultDialog to inspect a specific file.
        """
        if not os.path.exists(file_path):
            QMessageBox.warning(self, "Error", f"File does not exist: {file_path}")
            return
            
        self._load_file_from_path(file_path)

    def _load_file_from_path(self, file_name):
        self.current_excel_path = file_name
        self.file_label.setText(os.path.basename(file_name))
        try:
            self.data_loader.load_file(file_name)
            
            # Populate Topic Dropdown
            self.topic_combo.clear()
            self.topic_combo.addItems(self.data_loader.get_topics())
            
            # Clear current selection
            self.selected_topics = []
            self.topic_table.setRowCount(0) # Clear table
            
            # Initialize Time Axis
            time_axis = self.data_loader.get_time_axis()
            self.timeline.set_time_axis(time_axis)
            
            # Auto Load Config if exists
            base_name = os.path.splitext(file_name)[0]
            json_path = base_name + ".json"
            if os.path.exists(json_path):
                try:
                    self.inspector_logic.load_rules_from_json(json_path)
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
                    rule_topics = set(r.topic for r in self.inspector_logic.rules)
                    for topic in rule_topics:
                        self.add_topic_to_table(topic)
                        
                    QMessageBox.information(self, "Success", f"Loaded {os.path.basename(file_name)}\nand configuration {os.path.basename(json_path)}")
                except Exception as e:
                     QMessageBox.warning(self, "Warning", f"Loaded Excel but failed to load config: {e}")
            else:
                # Clear/Default UI if no config
                self.inspector_logic.metadata = {
                    "vehicle": "", "sw_ver": "", "test_date": "",
                    "categories": [], "tc_number": "", "note": ""
                }
                self.input_vehicle.clear()
                self.input_sw_ver.clear()
                self.input_date.setDate(QDate.currentDate())
                self.category_list.clear()
                self.input_tc_num.clear()
                self.input_note.clear()
                self.refresh_rules_table() # Clear rules
                
                QMessageBox.information(self, "Success", f"Loaded {os.path.basename(file_name)} successfully.\n(No config found)")
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load file: {str(e)}")

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
        spin.setRange(1, 10)
        spin.setValue(plot_id)
        spin.valueChanged.connect(self.update_plot)
        self.topic_table.setCellWidget(row, 1, spin)
        
        self.selected_topics.append(topic)
        # We delay update_plot until caller calls it or let it trigger
        self.update_plot()

