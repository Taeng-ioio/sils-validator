from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QPushButton, QListWidget, 
                             QListWidgetItem, QLabel, QMessageBox, QHBoxLayout, QInputDialog)
from PyQt6.QtCore import Qt

class MacroDialog(QDialog):
    def __init__(self, macros, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Macro Setup")
        self.resize(500, 400)
        
        self.layout = QVBoxLayout(self)
        self.layout.addWidget(QLabel("Select a Macro to Apply:"))
        
        self.list_widget = QListWidget()
        self.list_widget.itemDoubleClicked.connect(self.apply_selected)
        self.layout.addWidget(self.list_widget)
        
        # Populate List
        self.macros = macros
        self._refresh_list()
            
        btn_layout = QHBoxLayout()
        apply_btn = QPushButton("Apply Selected")
        apply_btn.clicked.connect(self.apply_selected)
        
        add_btn = QPushButton("Add Current Rules as Macro")
        add_btn.clicked.connect(self.on_add_current)
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.reject)
        
        btn_layout.addWidget(apply_btn)
        btn_layout.addWidget(add_btn)
        btn_layout.addWidget(close_btn)
        self.layout.addLayout(btn_layout)
        
        self.selected_macro = None
        self.add_requested = False
        self.new_macro_info = None

    def _refresh_list(self):
        self.list_widget.clear()
        for macro in self.macros:
            item = QListWidgetItem(f"{macro['name']} - {macro['description']} ({len(macro.get('rules', []))} rules)")
            item.setData(Qt.ItemDataRole.UserRole, macro)
            self.list_widget.addItem(item)
        
    def apply_selected(self):
        item = self.list_widget.currentItem()
        if not item:
            QMessageBox.warning(self, "No Selection", "Please select a macro.")
            return
            
        self.selected_macro = item.data(Qt.ItemDataRole.UserRole)
        self.accept()

    def on_add_current(self):
        name, ok = QInputDialog.getText(self, "New Macro", "Enter Macro Name:")
        if not ok or not name: return
        
        desc, ok = QInputDialog.getText(self, "New Macro", "Enter Description:")
        if not ok: desc = ""
        
        self.new_macro_info = {"name": name, "description": desc}
        self.add_requested = True
        self.accept()
