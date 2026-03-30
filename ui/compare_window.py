import copy
import os

from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QComboBox,
    QListWidget,
    QMessageBox,
    QFrame,
    QSplitter,
    QLineEdit,
    QRadioButton,
    QButtonGroup,
    QTableWidget,
    QHeaderView,
    QCompleter,
    QGroupBox,
    QDateEdit,
    QPlainTextEdit,
    QSpinBox,
    QScrollArea,
)
from PyQt6.QtCore import Qt, QDate

from core.data_loader import ExcelLoader
from core.logic import InspectorLogic
from ui.main_window import MainWindow
from ui.widgets import TimelineWidget


class BatchCompareWindow(MainWindow):
    def __init__(self, compare_name, compare_entries, shared_logic=None, parent=None):
        QMainWindow.__init__(self, parent)
        self.compare_name = compare_name
        self.compare_entries = compare_entries
        self.compare_views = []
        self.selected_topics = []
        self.current_excel_path = None
        self.file_list = []
        self.current_file_index = -1
        self.recent_config = None
        self.batch_dialog = None
        self.dat_folder_path = None
        self.dat_file_map = {}
        self.timeline = None
        self.data_loader = ExcelLoader()
        self.inspector_logic = InspectorLogic()
        self._syncing_cursor = False
        self._syncing_range = False

        if shared_logic and shared_logic.master_config_path:
            self.inspector_logic.master_config_path = shared_logic.master_config_path
            self.inspector_logic.master_config_data = copy.deepcopy(shared_logic.master_config_data)
            self.inspector_logic.macros = copy.deepcopy(shared_logic.macros)

        self.setWindowTitle(f"SILS-validator Compare - {compare_name}")
        self.resize(1760, 1180)
        self.init_ui()
        self.load_compare_targets(compare_entries)

    def init_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)

        layout = QVBoxLayout(main_widget)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        top_bar = QHBoxLayout()
        top_bar.setSpacing(10)

        compare_title = QLabel(f"Batch Compare: {self.compare_name}")
        compare_title.setStyleSheet("font-weight: bold; font-size: 15px;")
        self.file_label = QLabel(self.compare_name)
        self.file_label.setStyleSheet("color: #666; font-style: italic; margin-left: 10px;")

        top_bar.addWidget(compare_title)
        top_bar.addWidget(self.file_label)
        top_bar.addStretch()
        layout.addLayout(top_bar)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(2)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QScrollArea.Shape.NoFrame)

        left_panel = QFrame()
        left_panel.setFrameShape(QFrame.Shape.NoFrame)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setSpacing(10)
        left_layout.setContentsMargins(10, 10, 10, 10)

        test_info_group = QGroupBox("Test Information")
        test_info_layout = QVBoxLayout(test_info_group)

        test_info_layout.addWidget(QLabel("Vehicle:"))
        self.input_vehicle = QLineEdit()
        self.input_vehicle.setPlaceholderText("e.g. Prototype-A")
        test_info_layout.addWidget(self.input_vehicle)

        test_info_layout.addWidget(QLabel("SW Version:"))
        self.input_sw_ver = QLineEdit()
        self.input_sw_ver.setPlaceholderText("e.g. v1.0.2")
        test_info_layout.addWidget(self.input_sw_ver)

        test_info_layout.addWidget(QLabel("Test Date:"))
        self.input_date = QDateEdit()
        self.input_date.setCalendarPopup(True)
        self.input_date.setDate(QDate.currentDate())
        test_info_layout.addWidget(self.input_date)

        left_layout.addWidget(test_info_group)

        test_info_layout.addWidget(QLabel("Category:"))
        cat_layout = QHBoxLayout()
        self.input_category_combo = QComboBox()
        self.input_category_combo.addItems([
            'ENCAP_DSM', 'ENCAP_OSM', 'ADDW', 'DDAW', 'AOI',
            'FATIGUE', 'EYEP', 'FMEA_DSM', 'FMEA_OSM', 'BO',
            'SBT', 'ACT', 'ONCAL', 'BLK', 'DEGRA'
        ])
        cat_layout.addWidget(self.input_category_combo)

        add_cat_btn = QPushButton("Add")
        add_cat_btn.setFixedWidth(80)
        add_cat_btn.clicked.connect(self.add_category)
        cat_layout.addWidget(add_cat_btn)
        test_info_layout.addLayout(cat_layout)

        self.category_list = QListWidget()
        self.category_list.setFixedHeight(80)
        self.category_list.setStyleSheet("QListWidget::item { height: 20px; padding: 0px; }")
        test_info_layout.addWidget(self.category_list)

        del_cat_btn = QPushButton("Delete Category")
        del_cat_btn.clicked.connect(self.delete_category)
        test_info_layout.addWidget(del_cat_btn)

        test_info_layout.addWidget(QLabel("TC Number:"))
        self.input_tc_num = QLineEdit()
        test_info_layout.addWidget(self.input_tc_num)

        test_info_layout.addWidget(QLabel("Note:"))
        self.input_note = QPlainTextEdit()
        self.input_note.setFixedHeight(60)
        test_info_layout.addWidget(self.input_note)

        load_recent_btn = QPushButton("Load Recent Config")
        load_recent_btn.clicked.connect(self.load_recent_config)
        test_info_layout.addWidget(load_recent_btn)

        lbl_topics = QLabel("Topics")
        lbl_topics.setProperty("heading", "true")
        left_layout.addWidget(lbl_topics)

        self.topic_combo = QComboBox()
        self.topic_combo.setEditable(True)
        self.topic_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.topic_combo.completer().setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self.topic_combo.completer().setFilterMode(Qt.MatchFlag.MatchContains)
        self.topic_combo.setPlaceholderText("Search Topic...")
        left_layout.addWidget(self.topic_combo)

        add_topic_btn = QPushButton("Add Topic")
        add_topic_btn.clicked.connect(self.add_topic)
        left_layout.addWidget(add_topic_btn)

        self.topic_table = QTableWidget()
        self.topic_table.setColumnCount(2)
        self.topic_table.setHorizontalHeaderLabels(["Topic Name", "Plot #"])
        self.topic_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.topic_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self.topic_table.setColumnWidth(1, 120)
        self.topic_table.verticalHeader().setDefaultSectionSize(45)
        self.topic_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        left_layout.addWidget(self.topic_table)

        delete_topic_btn = QPushButton("Delete Selected Topic")
        self._style_danger_button(delete_topic_btn)
        delete_topic_btn.clicked.connect(self.delete_topic)
        left_layout.addWidget(delete_topic_btn)

        scroll_area.setWidget(left_panel)
        splitter.addWidget(scroll_area)

        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)

        right_splitter = QSplitter(Qt.Orientation.Vertical)
        right_splitter.setHandleWidth(2)

        viz_container = QWidget()
        viz_layout = QVBoxLayout(viz_container)
        viz_layout.setSpacing(10)
        viz_layout.setContentsMargins(10, 10, 10, 10)

        lbl_viz = QLabel("Visualization & Inspector")
        lbl_viz.setProperty("heading", "true")
        viz_layout.addWidget(lbl_viz)

        self.data_display_label = QLabel("Batch compare mode")
        self.data_display_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        viz_layout.addWidget(self.data_display_label)

        self.compare_scroll = QScrollArea()
        self.compare_scroll.setWidgetResizable(True)
        self.compare_scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        self.compare_container = QWidget()
        self.compare_layout = QVBoxLayout(self.compare_container)
        self.compare_layout.setContentsMargins(0, 0, 0, 0)
        self.compare_layout.setSpacing(12)
        self.compare_scroll.setWidget(self.compare_container)
        viz_layout.addWidget(self.compare_scroll)

        right_splitter.addWidget(viz_container)

        rule_group = self.create_rule_group()
        rule_group.setMaximumHeight(340)
        self.rules_table.setColumnWidth(2, 420)
        self.rules_table.setColumnWidth(3, 90)
        self.rules_table.setColumnWidth(4, 90)
        right_splitter.addWidget(rule_group)

        right_splitter.setStretchFactor(0, 4)
        right_splitter.setStretchFactor(1, 1)

        right_layout.addWidget(right_splitter)
        splitter.addWidget(right_panel)

        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        scroll_area.setMinimumWidth(400)

        layout.addWidget(splitter)

    def _clear_compare_views(self):
        while self.compare_layout.count():
            item = self.compare_layout.takeAt(0)
            widget = item.widget()
            child_layout = item.layout()
            if widget is not None:
                widget.deleteLater()
            elif child_layout is not None:
                while child_layout.count():
                    child_item = child_layout.takeAt(0)
                    child_widget = child_item.widget()
                    if child_widget is not None:
                        child_widget.deleteLater()

    def update_rule_topics(self):
        topics = sorted(
            {
                topic
                for view in self.compare_views
                if view.get("loader") is not None
                for topic in view["loader"].get_topics()
            }
        )
        self.rule_topic_combo.clear()
        self.rule_topic_combo.addItems(topics)

    def _sync_range_from_view(self, source_index):
        if self._syncing_range:
            return
        if not (0 <= source_index < len(self.compare_views)):
            return

        source_timeline = self.compare_views[source_index].get("timeline")
        if source_timeline is None:
            return

        self.timeline = source_timeline
        start = source_timeline.spin_start.value()
        end = source_timeline.spin_end.value()

        self._syncing_range = True
        for idx, view in enumerate(self.compare_views):
            if idx == source_index:
                continue
            timeline = view.get("timeline")
            if timeline is None:
                continue
            timeline.spin_start.setValue(start)
            timeline.spin_end.setValue(end)
        self._syncing_range = False

    def on_compare_time_changed(self, source_index, time_val, frame_idx):
        if self._syncing_cursor:
            return

        self._syncing_cursor = True
        for idx, view in enumerate(self.compare_views):
            timeline = view.get("timeline")
            loader = view.get("loader")
            data_label = view.get("data_label")
            if loader is None or data_label is None:
                continue

            if idx != source_index and timeline is not None:
                timeline.set_position_by_frame(frame_idx)

            info_text = f"Time: {time_val:.3f}s | Frame: {frame_idx}"
            values = []
            for topic in self.selected_topics:
                val = loader.get_value_at_time_index(topic, frame_idx)
                values.append(f"{topic}: {val}")
            if values:
                info_text += "  " + " | ".join(values)
            data_label.setText(info_text)

        self.data_display_label.setText(f"Synced cursor: {time_val:.3f}s | Frame: {frame_idx}")
        self._syncing_cursor = False

    def load_compare_targets(self, compare_entries):
        self.compare_entries = compare_entries
        self.compare_views = []
        self.timeline = None
        self.current_excel_path = None
        self._clear_compare_views()

        all_topics = set()
        first_loaded = False

        for index, entry in enumerate(compare_entries):
            folder_name = entry.get("folder_name", f"Folder {index + 1}")
            file_path = entry.get("path")

            group = QGroupBox(folder_name)
            group_layout = QVBoxLayout(group)
            group_layout.setContentsMargins(10, 12, 10, 10)
            group_layout.setSpacing(8)

            path_label = QLabel(file_path if file_path else "File not found in this folder.")
            path_label.setStyleSheet("color: #666;")
            path_label.setWordWrap(True)
            group_layout.addWidget(path_label)

            data_label = QLabel("Time: 0.000s | Frame: 0")
            data_label.setStyleSheet("font-weight: bold;")
            group_layout.addWidget(data_label)

            timeline = None
            loader = None

            if file_path and os.path.exists(file_path):
                try:
                    loader = ExcelLoader()
                    loader.load_file(file_path)
                    all_topics.update(loader.get_topics())

                    timeline = TimelineWidget()
                    timeline.set_fs(loader.time_step)
                    timeline.set_time_axis(loader.get_time_axis())
                    timeline.enable_range_selection(True)
                    timeline.time_changed.connect(
                        lambda time_val, frame_idx, idx=index: self.on_compare_time_changed(idx, time_val, frame_idx)
                    )
                    timeline.spin_start.valueChanged.connect(
                        lambda _value, idx=index: self._sync_range_from_view(idx)
                    )
                    timeline.spin_end.valueChanged.connect(
                        lambda _value, idx=index: self._sync_range_from_view(idx)
                    )
                    group_layout.addWidget(timeline)

                    if not first_loaded:
                        self.data_loader = loader
                        self.current_excel_path = file_path
                        self.timeline = timeline
                        self.file_label.setText(os.path.basename(file_path))
                        first_loaded = True
                except Exception as exc:
                    error_label = QLabel(f"Failed to load file: {exc}")
                    error_label.setStyleSheet("color: #c00;")
                    error_label.setWordWrap(True)
                    group_layout.addWidget(error_label)
            else:
                empty_label = QLabel("No matching file in this folder.")
                empty_label.setStyleSheet("color: #999;")
                group_layout.addWidget(empty_label)

            self.compare_layout.addWidget(group)
            self.compare_views.append(
                {
                    "folder_name": folder_name,
                    "file_path": file_path,
                    "loader": loader,
                    "timeline": timeline,
                    "data_label": data_label,
                }
            )

        self.compare_layout.addStretch()

        sorted_topics = sorted(all_topics)
        self.topic_combo.clear()
        self.topic_combo.addItems(sorted_topics)
        self.rule_topic_combo.clear()
        self.rule_topic_combo.addItems(sorted_topics)
        self.rule_topic_combo.setCurrentIndex(-1)

        self.selected_topics = []
        self.topic_table.setRowCount(0)

        if self.current_excel_path:
            self._load_config_for_current_excel()
            if self.compare_views and self.compare_views[0].get("timeline") is not None:
                self._sync_range_from_view(0)
                self.update_plot()
        else:
            QMessageBox.warning(self, "Compare Error", "No files could be opened for comparison.")

    def update_plot(self):
        if not self.compare_views:
            return

        for view in self.compare_views:
            loader = view.get("loader")
            timeline = view.get("timeline")
            if loader is None or timeline is None:
                continue

            time_axis = loader.get_time_axis()
            if time_axis is None or len(time_axis) == 0:
                timeline.plot_topics([], {})
                continue

            if not self.selected_topics:
                timeline.plot_topics(time_axis, {})
                continue

            data_dict = {}
            plot_map = {}
            for i in range(self.topic_table.rowCount()):
                topic_item = self.topic_table.item(i, 0)
                if topic_item is None:
                    continue
                topic = topic_item.text()
                spin = self.topic_table.cellWidget(i, 1)
                plot_id = spin.value() if spin else 1
                vals = loader.get_data_for_topic(topic)
                if vals is not None:
                    data_dict[topic] = vals
                    plot_map[topic] = plot_id

            timeline.set_fs(loader.time_step)
            timeline.set_time_axis(time_axis)
            timeline.plot_topics(time_axis, data_dict, plot_map)

        if self.compare_views and self.compare_views[0].get("timeline") is not None:
            self._sync_range_from_view(0)

    def on_rule_selection_changed(self):
        selected_items = self.rules_table.selectedItems()
        if not selected_items:
            return

        row = selected_items[0].row()
        rules = self.inspector_logic.get_rules()
        if row >= len(rules):
            return

        rule = rules[row]

        for view in self.compare_views:
            timeline = view.get("timeline")
            if timeline is not None:
                timeline.set_selected_range(rule.start_time, rule.end_time)
                timeline.spin_start.setValue(rule.start_time)
                timeline.spin_end.setValue(rule.end_time)

        topic_item = self.rules_table.item(row, 2)
        if topic_item:
            topic_str = topic_item.text()
            topics = [t.strip() for t in topic_str.split('|') if t.strip()]

            if topics:
                first_topic = topics[0]
                self.rule_topic_combo.setCurrentText(first_topic)
                self.topic_combo.setCurrentText(first_topic)

            for topic in topics:
                if topic not in self.selected_topics:
                    self.add_topic_to_table(topic)
