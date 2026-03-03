import os
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QSlider, QMessageBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap, QImage, QKeyEvent
import numpy as np

# Try importing ADTF, provide mock if not available (Mac environment)
try:
    import adtf
    ADTF_AVAILABLE = True
except ImportError:
    ADTF_AVAILABLE = False
    print("WARNING: ADTF library not found. Running in UI Mock mode.")

class DatViewerWindow(QMainWindow):
    def __init__(self, dat_file_path: str, parent=None):
        super().__init__(parent)
        self.dat_file_path = dat_file_path
        self.setWindowTitle(f"DAT Viewer - {os.path.basename(dat_file_path)}")
        self.resize(800, 600)
        
        self.total_frames = 0
        self.current_index = 0
        
        # This will hold the actual parsed ADTF frame data or mock data
        self.frames = []
        
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
        self.info_label = QLabel("Index: 0 | Time: 0.000s")
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
            if ADTF_AVAILABLE:
                self._load_with_adtf()
            else:
                self._load_mock_data()
                
            self.total_frames = len(self.frames)
            if self.total_frames > 0:
                self.slider.setMaximum(self.total_frames - 1)
                self.set_frame(0)
            else:
                self.image_label.setText("No image frames found in DAT file.")
                
        except Exception as e:
            QMessageBox.critical(self, "Error Loading DAT", f"Failed to load DAT file:\n{str(e)}")
            self.image_label.setText("Error loading file.")

    def _load_with_adtf(self):
        """
        Implementation using the ADTF python library to read .dat files.
        Executes only if the ADTF library is valid on the target machine.
        """
        import struct
        
        try:
            # First, let's try to introspect the adtf module to see what classes it actually has available
            available_attrs = dir(adtf)
            
            # Since we got an AttributeError for adtf.File, let's look for common alternative names
            # like 'adtf_file', 'Reader', 'FileReader', etc. or just print everything if we don't know it.
            if hasattr(adtf, 'File'):
                 reader = adtf.File(self.dat_file_path)
            else:
                 # Check if adtf_file is a separate installed module
                 try:
                     import adtf_file
                     # If adtf_file exists, try to guess its reader object
                     reader_class = getattr(adtf_file, 'File', getattr(adtf_file, 'Reader', getattr(adtf_file, 'FileReader', None)))
                     if reader_class:
                         reader = reader_class(self.dat_file_path)
                     else:
                         raise AttributeError(f"Could not find Reader class. adtf_file has: {dir(adtf_file)}")
                 except ImportError:
                     raise AttributeError(f"Cannot find 'File' in adtf. Available ADTF attributes are: {available_attrs}")
            
            # Extract basic information about streams
            stream_info_list = reader.get_streams()
            
            # Find a video/image stream. Usually indicated by stream type or name
            video_stream = None
            for stream in stream_info_list:
                # Common stream names or types for video in ADTF could be 'Video', 'Camera', 'Image'
                name = stream.name.lower()
                if 'video' in name or 'camera' in name or 'image' in name:
                    video_stream = reader.get_stream(stream.name)
                    break
                    
            if not video_stream:
                raise ValueError("Could not find a recognized video/image stream in the DAT file.")

            # Iterate through samples in the stream
            for sample in video_stream:
                # A sample.data is typically raw bytes.
                data_bytes = sample.data
                
                # ADTF Video samples often carry header information (like adtf::streaming::tStreamImageFormat)
                # For this implementation, we attempt to directly load the payload if it's already encoded (e.g. JPG, PNG)
                # or we convert it. Since we don't know the exact pixel format (e.g., RGB24, YUV420, Grey),
                # we'll try to let QImage auto-detect if there's a header, or assume a standard uncompressed format if known.
                
                # Option A: Assuming the bytes contain a fully encoded image (like JPEG/PNG)
                q_img = QImage()
                success = q_img.loadFromData(data_bytes)
                
                if not success:
                    # Option B: Assuming raw RGB888 data with a specific width/height.
                    # In a real ADTF environment, you extract width/height from the stream's type definition.
                    # Example arbitrary fallback (will look garbage if dimensions don't match):
                    # We would need to know exact resolution, e.g., 640x480 for raw data.
                    # QImage(data_bytes, width, height, bytes_per_line, QImage.Format.Format_RGB888)
                    print(f"Warning: Could not decode image payload using QImage.loadFromData. "
                          f"Raw byte length: {len(data_bytes)}. Needs specific format decoding.")
                    continue
                
                pixmap = QPixmap.fromImage(q_img)
                self.frames.append(pixmap)
                
        except Exception as e:
            raise RuntimeError(f"Error reading ADTF .dat file: {str(e)}")

    def _load_mock_data(self):
        """Generates mock images for UI testing on Mac."""
        self.frames = []
        for i in range(100):
            # Create a simple colored image for testing
            img = np.zeros((480, 640, 3), dtype=np.uint8)
            img[:] = [i * 2 % 255, 100, 150] # Change color based on index
            
            # Add text (requires opencv or PIL usually, but we'll just keep it simple)
            
            h, w, ch = img.shape
            bytes_per_line = ch * w
            q_img = QImage(img.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
            pixmap = QPixmap.fromImage(q_img)
            self.frames.append(pixmap)

    def set_frame(self, index: int):
        if 0 <= index < self.total_frames:
            self.current_index = index
            self.slider.blockSignals(True)
            self.slider.setValue(index)
            self.slider.blockSignals(False)
            
            # Update Image
            pixmap = self.frames[index]
            # Scale pixmap to fit label while keeping aspect ratio
            scaled_pixmap = pixmap.scaled(
                self.image_label.size(), 
                Qt.AspectRatioMode.KeepAspectRatio, 
                Qt.TransformationMode.SmoothTransformation
            )
            self.image_label.setPixmap(scaled_pixmap)
            
            # Update Info Label
            time_val = index * 0.033
            self.info_label.setText(f"Index: {index} | Time: {time_val:.3f}s")
            
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
        else:
            super().keyPressEvent(event)

    def resizeEvent(self, event):
        """Ensure image scales when window resizes"""
        super().resizeEvent(event)
        if self.total_frames > 0:
            self.set_frame(self.current_index)
