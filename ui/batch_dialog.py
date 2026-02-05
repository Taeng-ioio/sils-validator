from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QLabel, QFileDialog, QTableWidget, QTableWidgetItem, 
                             QProgressBar, QHeaderView, QMessageBox)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from core.batch_processor import BatchProcessor
import os
import csv



class BatchWorker(QThread):
    progress = pyqtSignal(int, int, dict) # changed str to dict for result_entry
    finished = pyqtSignal(list)
    
    def __init__(self, folder, logic):
        super().__init__()
        self.folder = folder
        self.logic = logic
        self.processor = BatchProcessor()
        
    def run(self):
        results = self.processor.run_batch(self.folder, self.logic, self.emit_progress)
        self.finished.emit(results)
        
    def emit_progress(self, current, total, result):
        self.progress.emit(current, total, result)

class BatchResultDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Batch Validation")
        self.resize(800, 600)
        
        self.layout = QVBoxLayout(self)
        
        # Top Bar: Folder Selection
        top_layout = QHBoxLayout()
        self.folder_label = QLabel("No folder selected")
        select_btn = QPushButton("Select Folder")
        select_btn.clicked.connect(self.select_folder)
        
        self.run_btn = QPushButton("Run Batch")
        self.run_btn.clicked.connect(self.run_batch)
        self.run_btn.setEnabled(False)
        
        top_layout.addWidget(select_btn)
        top_layout.addWidget(self.folder_label)
        top_layout.addStretch()
        top_layout.addWidget(self.run_btn)
        
        self.layout.addLayout(top_layout)
        
        # Progress Bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.layout.addWidget(self.progress_bar)
        
        self.status_label = QLabel("")
        self.layout.addWidget(self.status_label)
        
        # Results Table
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["File", "Status", "Fail Count", "Details", "Action"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(4, 80)
        self.layout.addWidget(self.table)
        
        # Export Button
        export_layout = QHBoxLayout()
        export_layout.addStretch()
        self.export_btn = QPushButton("Export Results (CSV)")
        self.export_btn.clicked.connect(self.export_results)
        self.export_btn.setEnabled(False)
        export_layout.addWidget(self.export_btn)
        self.layout.addLayout(export_layout)
        
        self.current_results = []
        self.selected_folder = None
        self.file_row_map = {} # Map filename to row index
        
    def select_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Folder")
        if folder:
            self.selected_folder = folder
            self.folder_label.setText(folder)
            self.run_btn.setEnabled(True)
            self.populate_initial_list(folder)
            
    def populate_initial_list(self, folder):
        self.table.setRowCount(0)
        self.file_row_map = {}
        
        data_files = []
        for root, dirs, files in os.walk(folder):
            for file in files:
                if file.lower().endswith(('.xlsx', '.xls', '.csv')):
                    full_path = os.path.join(root, file)
                    data_files.append(full_path)
        
        self.table.setRowCount(len(data_files))
        for i, path in enumerate(data_files):
            rel_path = os.path.relpath(path, folder)
            self.file_row_map[rel_path] = i
            
            self.table.setItem(i, 0, QTableWidgetItem(rel_path))
            self.table.setItem(i, 1, QTableWidgetItem("Ready"))
            self.table.setItem(i, 2, QTableWidgetItem("-"))
            self.table.setItem(i, 3, QTableWidgetItem(""))
            
    def run_batch(self):
        if not self.selected_folder:
            return
            
        # Don't clear table, just reset UI state
        self.run_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.status_label.setText("Starting...")
        
        # Pass inspector logic from main window
        self.worker = BatchWorker(self.selected_folder, self.parent().inspector_logic)
        self.worker.progress.connect(self.update_progress)
        self.worker.finished.connect(self.on_finished)
        self.worker.start()
        
    def update_progress(self, current, total, result):
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(current)
        self.status_label.setText(f"Processing: {result['file']} ({current}/{total})")
        
        # Update Row
        if result['file'] in self.file_row_map:
            row = self.file_row_map[result['file']]
            self._update_table_row(row, result)
            
    def _update_table_row(self, row, res):
        status_item = QTableWidgetItem(res['status'])
        if res['status'] == 'PASS':
            status_item.setForeground(Qt.GlobalColor.green)
        elif res['status'] == 'FAIL':
            status_item.setForeground(Qt.GlobalColor.red)
        elif res['status'] == 'NO_CONFIG':
            status_item.setForeground(Qt.GlobalColor.darkYellow)
            
        self.table.setItem(row, 1, status_item)
        self.table.setItem(row, 2, QTableWidgetItem(str(res['fail_count'])))
        self.table.setItem(row, 3, QTableWidgetItem(res['details']))
        
        btn_inspect = QPushButton("Inspect")
        btn_inspect.clicked.connect(lambda _, r=res: self.inspect_file_action(r))
        self.table.setCellWidget(row, 4, btn_inspect)
        
    def on_finished(self, results):
        self.current_results = results # This should match what we updated incrementally
        self.run_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.status_label.setText(f"Completed. Processed {len(results)} files.")
        self.export_btn.setEnabled(True)
        
        # Final pass just in case (optional, since we updated incrementally)
        # self.populate_table(results) 
        
    def populate_table(self, results):
        self.table.setRowCount(len(results))
        for i, res in enumerate(results):
            self.table.setItem(i, 0, QTableWidgetItem(res['file']))
            self._update_table_row(i, res)
            
    def export_results(self):
        if not self.current_results:
            return
            
        file_name, _ = QFileDialog.getSaveFileName(self, "Save CSV", "batch_results.csv", "CSV Files (*.csv)")
        if file_name:
            try:
                with open(file_name, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=[
                        "file", "status", "fail_count", "details", 
                        "vehicle", "sw_ver", "test_date",
                        "categories", "tc_number", "note"
                    ])
                    writer.writeheader()
                    writer.writerows(self.current_results)
                QMessageBox.information(self, "Success", "Results exported successfully.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save: {e}")

    def inspect_file_action(self, res):
        if not self.selected_folder:
            return
        
        full_path = os.path.join(self.selected_folder, res['file'])
        if os.path.exists(full_path):
            self.parent().inspect_from_batch(full_path)
            # self.accept() # Removed to keep dialog open
        else:
            QMessageBox.warning(self, "Error", f"File not found: {full_path}")
