from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QFileDialog,
    QTableWidget,
    QTableWidgetItem,
    QProgressBar,
    QHeaderView,
    QMessageBox,
    QListWidget,
    QListWidgetItem,
    QFrame,
    QAbstractItemView,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from core.batch_processor import BatchProcessor
import os
import csv


class BatchWorker(QThread):
    progress = pyqtSignal(int, int, str, dict)
    finished = pyqtSignal(dict)

    def __init__(self, folders, logic):
        super().__init__()
        self.folders = folders
        self.logic = logic
        self.processor = BatchProcessor()

    def run(self):
        results = self.processor.run_batch_compare(
            self.folders,
            self.logic,
            self.emit_progress,
        )
        self.finished.emit(results)

    def emit_progress(self, current, total, folder_name, result):
        self.progress.emit(current, total, folder_name, result)


class BatchResultDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Batch Validation")
        self.resize(1280, 760)

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(16, 16, 16, 16)
        self.layout.setSpacing(12)

        self.current_results = {}
        self.selected_folders = []
        self.folder_results = {}
        self.file_row_map = {}
        self.folder_column_map = {}

        self._build_header_ui()
        self._build_progress_ui()
        self._build_table_ui()
        self._build_footer_ui()

    def _build_header_ui(self):
        header_frame = QFrame()
        header_frame.setFrameShape(QFrame.Shape.StyledPanel)
        header_layout = QVBoxLayout(header_frame)
        header_layout.setContentsMargins(12, 12, 12, 12)
        header_layout.setSpacing(10)

        title_label = QLabel("Compare batch results across multiple folders")
        title_label.setStyleSheet("font-size: 16px; font-weight: 600;")
        subtitle_label = QLabel(
            "Add folders in comparison order. Files are matched by filename, and Inspect opens the file from the first folder."
        )
        subtitle_label.setStyleSheet("color: #666;")
        subtitle_label.setWordWrap(True)

        header_layout.addWidget(title_label)
        header_layout.addWidget(subtitle_label)

        content_layout = QHBoxLayout()
        content_layout.setSpacing(12)

        left_layout = QVBoxLayout()
        left_layout.setSpacing(6)

        folder_title = QLabel("Selected folders")
        folder_title.setStyleSheet("font-weight: 600;")
        left_layout.addWidget(folder_title)

        self.folder_list = QListWidget()
        self.folder_list.setAlternatingRowColors(True)
        self.folder_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.folder_list.setMinimumHeight(120)
        left_layout.addWidget(self.folder_list)

        self.folder_count_label = QLabel("No folders added")
        self.folder_count_label.setStyleSheet("color: #666;")
        left_layout.addWidget(self.folder_count_label)

        content_layout.addLayout(left_layout, 1)

        button_layout = QVBoxLayout()
        button_layout.setSpacing(14)

        add_btn = QPushButton("Add Folder")
        add_btn.setMinimumHeight(36)
        add_btn.clicked.connect(self.add_folder)
        remove_btn = QPushButton("Remove Selected")
        remove_btn.setMinimumHeight(36)
        remove_btn.clicked.connect(self.remove_selected_folder)
        self.run_btn = QPushButton("Run Batch")
        self.run_btn.clicked.connect(self.run_batch)
        self.run_btn.setEnabled(False)
        self.run_btn.setMinimumHeight(40)

        button_layout.addWidget(add_btn)
        button_layout.addSpacing(8)
        button_layout.addWidget(remove_btn)
        button_layout.addStretch()
        button_layout.addWidget(self.run_btn)

        content_layout.addLayout(button_layout)
        header_layout.addLayout(content_layout)

        self.layout.addWidget(header_frame)

    def _build_progress_ui(self):
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setTextVisible(True)
        self.layout.addWidget(self.progress_bar)

        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("color: #555;")
        self.layout.addWidget(self.status_label)

    def _build_table_ui(self):
        self.table = QTableWidget()
        self.table.setColumnCount(0)
        self.table.setRowCount(0)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(36)
        self.layout.addWidget(self.table)

    def _build_footer_ui(self):
        export_layout = QHBoxLayout()
        export_layout.addStretch()
        self.export_btn = QPushButton("Export Results (CSV)")
        self.export_btn.clicked.connect(self.export_results)
        self.export_btn.setEnabled(False)
        export_layout.addWidget(self.export_btn)
        self.layout.addLayout(export_layout)

    def _folder_names(self):
        return [entry["name"] for entry in self.selected_folders]

    def _refresh_folder_summary(self):
        count = len(self.selected_folders)
        if count == 0:
            self.folder_count_label.setText("No folders added")
        else:
            self.folder_count_label.setText(f"{count} folder(s) in comparison order")

    def add_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Folder")
        if not folder:
            return

        normalized = os.path.normpath(folder)
        if any(os.path.normpath(entry["path"]) == normalized for entry in self.selected_folders):
            QMessageBox.information(self, "Info", "This folder is already added.")
            return

        folder_name = os.path.basename(normalized) or normalized
        display_name = folder_name
        existing_names = set(self._folder_names())
        suffix = 2
        while display_name in existing_names:
            display_name = f"{folder_name}_{suffix}"
            suffix += 1

        self.selected_folders.append({"name": display_name, "path": normalized})
        self.folder_list.addItem(QListWidgetItem(f"{display_name}: {normalized}"))
        self.run_btn.setEnabled(len(self.selected_folders) > 0)
        self._refresh_folder_summary()
        self.populate_initial_list()

    def remove_selected_folder(self):
        row = self.folder_list.currentRow()
        if row < 0:
            return

        self.folder_list.takeItem(row)
        del self.selected_folders[row]
        self.run_btn.setEnabled(len(self.selected_folders) > 0)
        self._refresh_folder_summary()
        self.populate_initial_list()

    def populate_initial_list(self):
        self.table.clear()
        self.file_row_map = {}
        self.folder_column_map = {}
        self.current_results = {}
        self.folder_results = {}
        self.export_btn.setEnabled(False)

        folder_names = self._folder_names()
        headers = ["File"]
        for folder_name in folder_names:
            headers.extend([f"{folder_name} Status", f"{folder_name} details"])
        headers.append("Action")

        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)

        all_files = set()
        for entry in self.selected_folders:
            folder_path = entry["path"]
            for root, _, files in os.walk(folder_path):
                for file in files:
                    if file.lower().endswith((".xlsx", ".xls", ".csv")):
                        all_files.add(file)

        sorted_files = sorted(all_files)
        self.table.setRowCount(len(sorted_files))

        for i, filename in enumerate(sorted_files):
            self.file_row_map[filename] = i
            file_item = QTableWidgetItem(filename)
            file_item.setToolTip(filename)
            self.table.setItem(i, 0, file_item)
            action_col = len(headers) - 1
            if self.selected_folders:
                btn_inspect = QPushButton("Inspect")
                btn_inspect.setMinimumHeight(28)
                btn_inspect.clicked.connect(lambda _, f=filename: self.inspect_file_action(f))
                self.table.setCellWidget(i, action_col, btn_inspect)

        for idx, folder_name in enumerate(folder_names):
            status_col = 1 + (idx * 2)
            self.folder_column_map[folder_name] = {
                "status": status_col,
                "details": status_col + 1,
            }
            self.table.setColumnWidth(status_col, 95)
            self.table.setColumnWidth(status_col + 1, 280)

        if headers:
            self.table.setColumnWidth(0, 240)
            self.table.setColumnWidth(len(headers) - 1, 90)

        header = self.table.horizontalHeader()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        for col in range(1, len(headers) - 1):
            if col % 2 == 1:
                header.setSectionResizeMode(col, QHeaderView.ResizeMode.Fixed)
            else:
                header.setSectionResizeMode(col, QHeaderView.ResizeMode.Stretch)
        if headers:
            header.setSectionResizeMode(len(headers) - 1, QHeaderView.ResizeMode.Fixed)

    def run_batch(self):
        if not self.selected_folders:
            return

        self.run_btn.setEnabled(False)
        self.export_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.status_label.setText("Starting batch comparison...")

        self.worker = BatchWorker(self.selected_folders, self.parent().inspector_logic)
        self.worker.progress.connect(self.update_progress)
        self.worker.finished.connect(self.on_finished)
        self.worker.start()

    def update_progress(self, current, total, folder_name, result):
        self.progress_bar.setMaximum(max(total, 1))
        self.progress_bar.setValue(current)
        self.status_label.setText(f"Processing {folder_name}: {result['file']} ({current}/{total})")

        row = self.file_row_map.get(result["file"])
        if row is None:
            return
        self._update_table_row(row, folder_name, result)

    def _update_table_row(self, row, folder_name, res):
        cols = self.folder_column_map.get(folder_name)
        if not cols:
            return

        status_item = QTableWidgetItem(res["status"])
        if res["status"] == "PASS":
            status_item.setForeground(Qt.GlobalColor.green)
        elif res["status"] in {"FAIL", "ERROR"}:
            status_item.setForeground(Qt.GlobalColor.red)
        elif res["status"] == "NO_CONFIG":
            status_item.setForeground(Qt.GlobalColor.darkYellow)
        elif res["status"] == "MISSING":
            status_item.setForeground(Qt.GlobalColor.gray)

        details_item = QTableWidgetItem(res["details"])
        details_item.setToolTip(res["details"])
        if res["status"] == "MISSING":
            details_item.setForeground(Qt.GlobalColor.gray)

        self.table.setItem(row, cols["status"], status_item)
        self.table.setItem(row, cols["details"], details_item)

    def on_finished(self, results):
        self.current_results = results
        self.folder_results = results.get("by_folder", {})
        self.run_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.status_label.setText(
            f"Completed. Processed {results.get('processed_count', 0)} folder-file checks across {len(self.selected_folders)} folders."
        )
        self.export_btn.setEnabled(True)

        for file_name, row in self.file_row_map.items():
            for folder_name in self._folder_names():
                folder_map = self.folder_results.get(folder_name, {})
                if file_name not in folder_map:
                    self._update_table_row(
                        row,
                        folder_name,
                        {
                            "file": file_name,
                            "status": "MISSING",
                            "details": "File not found.",
                        },
                    )

    def export_results(self):
        if not self.current_results:
            return

        file_name, _ = QFileDialog.getSaveFileName(
            self,
            "Save CSV",
            "batch_results_compare.csv",
            "CSV Files (*.csv)",
        )
        if not file_name:
            return

        try:
            folder_names = self._folder_names()
            common_info_fields = [
                "vehicle",
                "sw_ver",
                "test_date",
                "categories",
                "tc_number",
                "note",
            ]
            fieldnames = ["file", *common_info_fields]
            for folder_name in folder_names:
                fieldnames.extend(
                    [
                        f"{folder_name}_status",
                        f"{folder_name}_details",
                    ]
                )

            with open(file_name, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()

                for file_name_key in sorted(self.file_row_map.keys()):
                    row = {"file": file_name_key}

                    common_source = None
                    for folder_name in folder_names:
                        candidate = self.folder_results.get(folder_name, {}).get(file_name_key)
                        if candidate and candidate.get("status") != "MISSING":
                            common_source = candidate
                            break

                    common_source = common_source or {
                        "vehicle": "",
                        "sw_ver": "",
                        "test_date": "",
                        "categories": "",
                        "tc_number": "",
                        "note": "",
                    }

                    for info_field in common_info_fields:
                        row[info_field] = common_source.get(info_field, "")

                    for folder_name in folder_names:
                        result = self.folder_results.get(folder_name, {}).get(
                            file_name_key,
                            {
                                "status": "MISSING",
                                "details": "File not found.",
                            },
                        )
                        row[f"{folder_name}_status"] = result.get("status", "")
                        row[f"{folder_name}_details"] = result.get("details", "")
                    writer.writerow(row)

            QMessageBox.information(self, "Success", "Results exported successfully.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save: {e}")

    def inspect_file_action(self, file_name):
        if not self.selected_folders:
            return

        first_folder = self.selected_folders[0]["path"]
        full_path = None
        for root, _, files in os.walk(first_folder):
            for file in files:
                if file == file_name and file.lower().endswith((".xlsx", ".xls", ".csv")):
                    full_path = os.path.join(root, file)
                    break
            if full_path:
                break

        if full_path and os.path.exists(full_path):
            self.parent().inspect_from_batch(full_path)
        else:
            QMessageBox.warning(self, "Error", f"File not found in first folder: {file_name}")
