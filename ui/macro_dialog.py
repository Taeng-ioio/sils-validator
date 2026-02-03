from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QPushButton, QListWidget, 
                             QListWidgetItem, QLabel, QMessageBox, QHBoxLayout)
from PyQt6.QtCore import Qt
from core.logic import RuleType

# Example Macros Logic
# Users can add more entries here to define new macros.
EXAMPLE_MACROS = [
    {
        "name": "Check System Ready (Start)",
        "description": "Topic: SystemState, Time: 0-0.5s, Must be 1",
        "topic": "SystemState",
        "start": 0.0,
        "end": 0.5,
        "rule_type": RuleType.MUST,
        "value": "1"
    },
    {
        "name": "Battery Voltage Stability",
        "description": "Topic: BatteryVoltage, Time: 0-10s, Must be 12.5",
        "topic": "BatteryVoltage",
        "start": 0.0,
        "end": 10.0,
        "rule_type": RuleType.MUST,
        "value": "12.5"
    },
    {
        "name": "No Error Flags",
        "description": "Topic: ErrorFlag, Time: 0-100s, Should Not be 1",
        "topic": "ErrorFlag",
        "start": 0.0,
        "end": 100.0,
        "rule_type": RuleType.SHOULD_NOT,
        "value": "1"
    }
]

class MacroDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Macro Setup")
        self.resize(400, 300)
        
        self.layout = QVBoxLayout(self)
        
        self.layout.addWidget(QLabel("Select a Macro to Apply:"))
        
        self.list_widget = QListWidget()
        self.list_widget.itemDoubleClicked.connect(self.apply_selected)
        self.layout.addWidget(self.list_widget)
        
        # Populate List
        for macro in EXAMPLE_MACROS:
            item = QListWidgetItem(f"{macro['name']} - {macro['description']}")
            item.setData(Qt.ItemDataRole.UserRole, macro)
            self.list_widget.addItem(item)
            
        btn_layout = QHBoxLayout()
        apply_btn = QPushButton("Apply")
        apply_btn.clicked.connect(self.apply_selected)
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.reject)
        
        btn_layout.addWidget(apply_btn)
        btn_layout.addWidget(close_btn)
        self.layout.addLayout(btn_layout)
        
        self.selected_macro = None
        
    def apply_selected(self):
        item = self.list_widget.currentItem()
        if not item:
            QMessageBox.warning(self, "No Selection", "Please select a macro.")
            return
            
        self.selected_macro = item.data(Qt.ItemDataRole.UserRole)
        self.accept()
