from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, 
                             QTableWidgetItem, QPushButton, QLabel, QHeaderView, 
                             QComboBox, QCompleter)
from PyQt6.QtCore import Qt

class ORRuleDialog(QDialog):
    def __init__(self, available_topics, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Create OR Rule")
        self.resize(500, 400)
        self.available_topics = available_topics
        
        layout = QVBoxLayout(self)
        
        layout.addWidget(QLabel("Add multiple conditions. Rule passes if AT LEAST ONE matches at each frame."))
        
        self.table = QTableWidget()
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["Topic", "Target Value"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setDefaultSectionSize(60)
        layout.addWidget(self.table)
        
        # Helper Buttons
        btn_layout = QHBoxLayout()
        add_btn = QPushButton("+ Add Condition")
        add_btn.clicked.connect(self.add_row)
        del_btn = QPushButton("- Remove Selected")
        del_btn.clicked.connect(self.remove_row)
        btn_layout.addWidget(add_btn)
        btn_layout.addWidget(del_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        # Bottom Buttons
        bottom_btns = QHBoxLayout()
        ok_btn = QPushButton("Create Rule")
        ok_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        bottom_btns.addStretch()
        bottom_btns.addWidget(ok_btn)
        bottom_btns.addWidget(cancel_btn)
        layout.addLayout(bottom_btns)
        
        # Add initial row
        self.add_row()

    def add_row(self):
        row = self.table.rowCount()
        self.table.insertRow(row)
        
        combo = QComboBox()
        combo.setEditable(True)
        combo.addItems(self.available_topics)
        combo.completer().setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        combo.completer().setFilterMode(Qt.MatchFlag.MatchContains)
        
        self.table.setCellWidget(row, 0, combo)
        self.table.setItem(row, 1, QTableWidgetItem(""))

    def remove_row(self):
        current_row = self.table.currentRow()
        if current_row >= 0:
            self.table.removeRow(current_row)

    def get_conditions(self):
        conditions = []
        for i in range(self.table.rowCount()):
            combo = self.table.cellWidget(i, 0)
            val_item = self.table.item(i, 1)
            if combo and val_item:
                topic = combo.currentText()
                val = val_item.text()
                if topic and val:
                    conditions.append((topic, val))
        return conditions
