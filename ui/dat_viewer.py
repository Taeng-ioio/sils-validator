import os
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QSlider, QScrollArea, QMessageBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap, QImage, QKeyEvent
import numpy as np

from core.data_loader import ADTFLoader

class DatViewerWindow(QMainWindow):
    def __init__(self, dat_file_path: str, parent=None):
        super().__init__(parent)
        self.dat_file_path = dat_file_path
        self.loader = ADTFLoader()
        self.total_frames = 0
        self.current_index = 0
        self.current_frame = None
        
        self.init_ui()
        self.load_dat_file()
        
    def init_ui(self):
        self.setWindowTitle(f"ADTF Image Viewer - Frame {self.current_index + 1}")
        self.resize(1280, 720)
        
        # Create central widget with layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Create scroll area for image
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        layout.addWidget(self.scroll_area)
        
        # Create widget to hold image
        self.image_container = QWidget()
        self.scroll_area.setWidget(self.image_container)
        self.image_layout = QVBoxLayout(self.image_container)
        
        # Create label for image display
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setStyleSheet("background-color: black;")
        self.image_label.setMinimumSize(640, 480) # Prevent total collapse on empty frames
        self.image_layout.addWidget(self.image_label)
        
        # Create label for frame info
        self.frame_info_label_window = QLabel()
        self.frame_info_label_window.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.frame_info_label_window.setStyleSheet("background-color: rgba(0, 0, 0, 150); color: white; font-weight: bold; padding: 5px;")
        self.frame_info_label_window.setText(f"Frame: {self.current_index + 1} / {self.total_frames}")
        self.image_layout.addWidget(self.frame_info_label_window)
        
        # Create slider for frame navigation
        self.frame_slider = QSlider(Qt.Orientation.Horizontal)
        self.frame_slider.setRange(0, 0)
        self.frame_slider.setValue(self.current_index)
        self.frame_slider.valueChanged.connect(self.on_frame_slider_changed)
        layout.addWidget(self.frame_slider)
        
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setFocus()
        
    def load_dat_file(self):
        try:
            if self.loader.load_file(self.dat_file_path):
                self.total_frames = self.loader.get_total_frames()
                self.current_index = 0
                self.frame_slider.setRange(0, max(0, self.total_frames - 1))
                self.current_frame = self.loader.get_frame(self.current_index)
                self.update_image_window()
            else:
                self.image_label.setText("Failed to load generic ADTF file.")
                # Enforce minimum size for the black screen layout
                self.image_label.setMinimumSize(640, 480)
        except Exception as e:
            QMessageBox.critical(self, "Error Loading DAT", f"Failed to load DAT file:\n{str(e)}")
            # Enforce minimum size for the black screen layout
            self.image_label.setMinimumSize(640, 480)
            
    def update_image_window(self):
        if self.current_frame is not None:
            # Convert numpy array to QImage
            # ADTF image is grayscale (2D), convert to RGB (3D)
            if len(self.current_frame.shape) == 2:
                # Grayscale to RGB conversion
                height, width = self.current_frame.shape
                img_rgb = np.stack([self.current_frame] * 3, axis=2)
            else:
                img_rgb = self.current_frame
                height, width, channel = img_rgb.shape
                
            bytes_per_line = 3 * width
            q_img = QImage(
                img_rgb.data,
                width,
                height,
                bytes_per_line,
                QImage.Format.Format_RGB888
            )
            
            # Scale image to fit window
            pixmap = QPixmap.fromImage(q_img)
            scaled_pixmap = pixmap.scaled(
                self.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            
            self.image_label.setPixmap(scaled_pixmap)
            
            # Prevent window from resizing when image is updated
            self.setFixedSize(self.size())
            
            self.setWindowTitle(f"ADTF Image Viewer - Frame {self.current_index + 1} / {self.total_frames}")
            self.frame_info_label_window.setText(f"Frame: {self.current_index + 1} / {self.total_frames}")
        else:
            self.image_label.clear()
            self.setWindowTitle(f"ADTF Image Viewer - Frame {self.current_index + 1} (Empty)")
            
    def navigate_next(self):
        if self.current_index < self.total_frames - 1:
            self.current_index += 1
            self.current_frame = self.loader.get_frame(self.current_index)
            self.frame_slider.blockSignals(True)
            self.frame_slider.setValue(self.current_index)
            self.frame_slider.blockSignals(False)
            self.update_image_window()
            
    def navigate_previous(self):
        if self.current_index > 0:
            self.current_index -= 1
            self.current_frame = self.loader.get_frame(self.current_index)
            self.frame_slider.blockSignals(True)
            self.frame_slider.setValue(self.current_index)
            self.frame_slider.blockSignals(False)
            self.update_image_window()
            
    def on_frame_slider_changed(self, value):
        if value != self.current_index:
            self.current_index = value
            self.current_frame = self.loader.get_frame(self.current_index)
            self.update_image_window()
            
    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key.Key_Space:
            self.navigate_next()
        elif event.key() == Qt.Key.Key_Left:
            self.navigate_previous()
        elif event.key() == Qt.Key.Key_Right:
            self.navigate_next()
        else:
            super().keyPressEvent(event)
            
    def closeEvent(self, event):
        if hasattr(self, 'loader') and self.loader:
            try:
                self.loader.close()
            except Exception:
                pass
        event.accept()
