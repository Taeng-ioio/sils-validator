import os
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QSlider, QMessageBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap, QImage, QKeyEvent
import numpy as np

# Import the user's working ADTFLoader
from core.data_loader import ADTFLoader

class DatViewerWindow(QMainWindow):
    def __init__(self, dat_file_path: str, parent=None):
        super().__init__(parent)
        self.dat_file_path = dat_file_path
        self.setWindowTitle(f"DAT Viewer - {os.path.basename(dat_file_path)}")
        self.resize(1280, 720)
        
        self.total_frames = 0
        self.current_index = 0
        
        self.loader = ADTFLoader()
        
        self.init_ui()
        self.load_dat_file()

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Image Display Label
        self.image_label = QLabel("Loading images...")
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setStyleSheet("background-color: black; color: white;")
        layout.addWidget(self.image_label, stretch=1)
        
        # Info Label (Index and Time)
        info_layout = QHBoxLayout()
        self.info_label = QLabel("Frame: 0 / 0 | Time: 0.000s")
        self.info_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        info_layout.addWidget(self.info_label)
        layout.addLayout(info_layout)
        
        # Slider
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setMinimum(0)
        self.slider.valueChanged.connect(self.on_slider_changed)
        layout.addWidget(self.slider)

    def load_dat_file(self):
        try:
            success = self.loader.load_file(self.dat_file_path)
            if success:
                self.total_frames = self.loader.get_total_frames()
                if self.total_frames > 0:
                    self.slider.setMaximum(self.total_frames - 1)
                    self.set_frame(0)
                else:
                    self.image_label.setText("No image frames found in DAT file.")
            else:
                self.image_label.setText("Failed to read ADTF data.")
                
        except Exception as e:
            QMessageBox.critical(self, "Error Loading DAT", f"Failed to load DAT file:\n{str(e)}")
            self.image_label.setText(f"Error loading file: {e}")

    def set_frame(self, index: int):
        if 0 <= index < self.total_frames:
            self.current_index = index
            self.slider.blockSignals(True)
            self.slider.setValue(index)
            self.slider.blockSignals(False)
            
            img_data = self.loader.get_frame(index)
            if img_data is not None:
                if len(img_data.shape) == 2:
                    img_rgb = np.stack([img_data] * 3, axis=2)
                else:
                    img_rgb = img_data
                
                height, width, channel = img_rgb.shape
                bytes_per_line = 3 * width
                # Prevent segfaults by passing image correctly
                q_img = QImage(
                    img_rgb.data, width, height, bytes_per_line, QImage.Format.Format_RGB888
                )
                
                pixmap = QPixmap.fromImage(q_img)
                scaled_pixmap = pixmap.scaled(
                    self.image_label.size(), 
                    Qt.AspectRatioMode.KeepAspectRatio, 
                    Qt.TransformationMode.SmoothTransformation
                )
                self.image_label.setPixmap(scaled_pixmap)
            else:
                err_msg = getattr(self.loader, 'last_error', "Unknown error")
                self.image_label.setText(f"Error decoding frame:\n{err_msg}")
            
            time_val = index * 0.033
            self.info_label.setText(f"Frame: {index + 1} / {self.total_frames} | Time: {time_val:.3f}s")
            
    def on_slider_changed(self, value):
        self.set_frame(value)

    def keyPressEvent(self, event: QKeyEvent):
        if not self.total_frames:
            super().keyPressEvent(event)
            return

        step = 10 if event.modifiers() & Qt.KeyboardModifier.ShiftModifier else 1

        if event.key() == Qt.Key.Key_Left:
            new_index = max(0, self.current_index - step)
            self.set_frame(new_index)
        elif event.key() == Qt.Key.Key_Right:
            new_index = min(self.total_frames - 1, self.current_index + step)
            self.set_frame(new_index)
        # Spacebar feature just in case
        elif event.key() == Qt.Key.Key_Space:
            new_index = min(self.total_frames - 1, self.current_index + 1)
            self.set_frame(new_index)
        else:
            super().keyPressEvent(event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.total_frames > 0:
            self.set_frame(self.current_index)
            
    def closeEvent(self, event):
        if hasattr(self, 'loader') and self.loader:
            try:
                self.loader.close()
            except Exception:
                pass
        event.accept()
