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
    QComboBox,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from core.batch_processor import BatchProcessor
from openpyxl import Workbook
from openpyxl.styles import Alignment, PatternFill
from openpyxl.utils import get_column_letter
import os


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
        self.file_categories = {}
        self.diff_only_enabled = False

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

        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Category Filter"))

        self.category_filter_combo = QComboBox()
        self.category_filter_combo.addItem("All")
        self.category_filter_combo.setMinimumWidth(240)
        self.category_filter_combo.setEnabled(False)
        self.category_filter_combo.currentTextChanged.connect(self.apply_filters)
        filter_layout.addWidget(self.category_filter_combo)

        self.diff_only_btn = QPushButton("Diff Only")
        self.diff_only_btn.setCheckable(True)
        self.diff_only_btn.setEnabled(False)
        self.diff_only_btn.toggled.connect(self.apply_filters)
        filter_layout.addWidget(self.diff_only_btn)
        filter_layout.addStretch()

        self.layout.addLayout(filter_layout)

    def _build_table_ui(self):
        self.table = QTableWidget()
        self.table.setColumnCount(0)
        self.table.setRowCount(0)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setWordWrap(True)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(36)
        self.layout.addWidget(self.table)

    def _build_footer_ui(self):
        export_layout = QHBoxLayout()
        export_layout.addStretch()
        self.export_btn = QPushButton("Export Results (Excel)")
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

    def _parse_categories(self, raw_categories):
        if not raw_categories:
            return []
        return [category.strip() for category in str(raw_categories).split("|") if category.strip()]

    def _reset_category_filter(self):
        self.file_categories = {}
        self.category_filter_combo.blockSignals(True)
        self.category_filter_combo.clear()
        self.category_filter_combo.addItem("All")
        self.category_filter_combo.setCurrentIndex(0)
        self.category_filter_combo.setEnabled(False)
        self.category_filter_combo.blockSignals(False)

    def _reset_diff_filter(self):
        self.diff_only_enabled = False
        self.diff_only_btn.blockSignals(True)
        self.diff_only_btn.setChecked(False)
        self.diff_only_btn.setEnabled(False)
        self.diff_only_btn.blockSignals(False)

    def _refresh_category_filter_options(self):
        selected = self.category_filter_combo.currentText() or "All"
        all_categories = sorted(
            {
                category
                for categories in self.file_categories.values()
                for category in categories
            }
        )

        self.category_filter_combo.blockSignals(True)
        self.category_filter_combo.clear()
        self.category_filter_combo.addItem("All")
        self.category_filter_combo.addItems(all_categories)
        self.category_filter_combo.setEnabled(True)

        selected_index = self.category_filter_combo.findText(selected)
        self.category_filter_combo.setCurrentIndex(selected_index if selected_index >= 0 else 0)
        self.category_filter_combo.blockSignals(False)

    def _is_diff_row(self, file_name):
        row_statuses = []
        for folder_name in self._folder_names():
            result = self.folder_results.get(folder_name, {}).get(
                file_name,
                {
                    "status": "MISSING",
                    "details": "File not found.",
                },
            )
            row_statuses.append(result.get("status", ""))
        return len(set(row_statuses)) > 1

    def apply_filters(self, *_):
        selected_category = self.category_filter_combo.currentText() or "All"
        self.diff_only_enabled = self.diff_only_btn.isChecked()

        for file_name, row in self.file_row_map.items():
            categories = self.file_categories.get(file_name, set())
            category_filtered = (
                selected_category != "All" and selected_category not in categories
            )
            diff_filtered = self.diff_only_enabled and not self._is_diff_row(file_name)
            self.table.setRowHidden(row, category_filtered or diff_filtered)

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
        self._reset_category_filter()
        self._reset_diff_filter()

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
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)

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
        details_item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        if res["status"] == "MISSING":
            details_item.setForeground(Qt.GlobalColor.gray)

        self.table.setItem(row, cols["status"], status_item)
        self.table.setItem(row, cols["details"], details_item)
        self.table.resizeRowToContents(row)

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
            collected_categories = set()
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
                else:
                    candidate = folder_map.get(file_name) or {}
                    collected_categories.update(
                        self._parse_categories(candidate.get("categories", ""))
                    )

            self.file_categories[file_name] = collected_categories

        self._refresh_category_filter_options()
        self.diff_only_btn.setEnabled(len(self._folder_names()) > 1)
        self.apply_filters()

    def _visible_file_names(self):
        visible_file_names = []
        for row in range(self.table.rowCount()):
            if self.table.isRowHidden(row):
                continue
            file_item = self.table.item(row, 0)
            if file_item:
                visible_file_names.append(file_item.text())
        return visible_file_names

    def _build_export_rows(self):
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

        rows = []
        for file_name_key in self._visible_file_names():
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

            rows.append(row)

        return fieldnames, rows

    def _export_results_excel(self, file_name, fieldnames, rows):
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "Batch Results"

        status_fills = {
            "PASS": PatternFill(fill_type="solid", fgColor="C6EFCE"),
            "FAIL": PatternFill(fill_type="solid", fgColor="FFC7CE"),
        }
        wrap_alignment = Alignment(wrap_text=True, vertical="top")

        for col_idx, fieldname in enumerate(fieldnames, start=1):
            sheet.cell(row=1, column=col_idx, value=fieldname)

        for row_idx, row_data in enumerate(rows, start=2):
            max_line_count = 1
            for col_idx, fieldname in enumerate(fieldnames, start=1):
                value = row_data.get(fieldname, "")
                cell = sheet.cell(row=row_idx, column=col_idx, value=value)

                if fieldname.endswith("_status"):
                    cell_fill = status_fills.get(str(value))
                    if cell_fill:
                        cell.fill = cell_fill

                if fieldname.endswith("_details") or fieldname == "note":
                    cell.alignment = wrap_alignment
                    max_line_count = max(max_line_count, str(value).count("\n") + 1)

            if max_line_count > 1:
                sheet.row_dimensions[row_idx].height = max(20, min(15 * max_line_count, 120))

        for col_idx, fieldname in enumerate(fieldnames, start=1):
            if fieldname == "file":
                width = 28
            elif fieldname == "note":
                width = 48
            elif fieldname.endswith("_status"):
                width = 12
            elif fieldname.endswith("_details"):
                width = 50
            else:
                width = 18
            sheet.column_dimensions[get_column_letter(col_idx)].width = width

        workbook.save(file_name)

    def export_results(self):
        if not self.current_results:
            return

        file_name, _ = QFileDialog.getSaveFileName(
            self,
            "Save Results",
            "batch_results_compare.xlsx",
            "Excel Files (*.xlsx)",
        )
        if not file_name:
            return

        try:
            fieldnames, rows = self._build_export_rows()
            extension = os.path.splitext(file_name)[1].lower()

            if extension != ".xlsx":
                file_name += ".xlsx"
            self._export_results_excel(file_name, fieldnames, rows)

            QMessageBox.information(self, "Success", "Results exported successfully.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save: {e}")

    def inspect_file_action(self, file_name):
        if not self.selected_folders:
            return

        compare_entries = []
        for entry in self.selected_folders:
            folder_name = entry["name"]
            folder_path = entry["path"]
            matched_path = None

            for root, _, files in os.walk(folder_path):
                for file in files:
                    if file == file_name and file.lower().endswith((".xlsx", ".xls", ".csv")):
                        matched_path = os.path.join(root, file)
                        break
                if matched_path:
                    break

            compare_entries.append(
                {
                    "folder_name": folder_name,
                    "path": matched_path,
                }
            )

        if any(entry.get("path") for entry in compare_entries):
            self.parent().inspect_from_batch_compare(file_name, compare_entries)
        else:
            QMessageBox.warning(self, "Error", f"File not found in selected folders: {file_name}")
