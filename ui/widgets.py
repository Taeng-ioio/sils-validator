import pyqtgraph as pg
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QSlider, QDoubleSpinBox, QPushButton, QFileDialog,
                             QMainWindow, QScrollArea)
from PyQt6.QtCore import pyqtSignal, Qt, QTimer
from PyQt6.QtGui import QImage, QPixmap
import numpy as np

class TimelineWidget(QWidget):
    time_changed = pyqtSignal(float, int) # timestamp, frame_index

    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        # Plot Widget Container (GraphicsLayoutWidget for subplots)
        self.plot_layout = pg.GraphicsLayoutWidget()
        self.plot_layout.setBackground('w')
        self.layout.addWidget(self.plot_layout)

        # We will keep track of created plots
        self.plots = [] 
        
        # Synchronization Lists
        self.cursors = [] 
        self.regions = []
        
        # Flags to prevent recursion during sync
        self.updating_cursor = False
        self.updating_region = False

        self.current_time_data = None
        self.fs = 0.033
        
        # Integrated Range Controls
        self._setup_range_controls()

    def _setup_range_controls(self):
        controls_layout = QHBoxLayout()
        
        # Start (A)
        controls_layout.addWidget(QLabel("Range Start (A):"))
        self.spin_start = QDoubleSpinBox()
        self.spin_start.setRange(0, 99999)
        self.spin_start.setSingleStep(0.033)
        self.spin_start.setDecimals(3)
        self.spin_start.valueChanged.connect(self.update_timeline_from_inputs)
        controls_layout.addWidget(self.spin_start)
        
        self.slider_start = QSlider(Qt.Orientation.Horizontal)
        self.slider_start.setRange(0, 1000)
        self.slider_start.valueChanged.connect(self.on_slider_start_changed)
        controls_layout.addWidget(self.slider_start)

        # End (B)
        controls_layout.addWidget(QLabel("Range End (B):"))
        self.spin_end = QDoubleSpinBox()
        self.spin_end.setRange(0, 99999)
        self.spin_end.setSingleStep(0.033)
        self.spin_end.setDecimals(3)
        self.spin_end.valueChanged.connect(self.update_timeline_from_inputs)
        controls_layout.addWidget(self.spin_end)
        
        self.slider_end = QSlider(Qt.Orientation.Horizontal)
        self.slider_end.setRange(0, 1000)
        self.slider_end.valueChanged.connect(self.on_slider_end_changed)
        controls_layout.addWidget(self.slider_end)
        
        self.layout.addLayout(controls_layout)

    def set_fs(self, fs):
        self.fs = fs
        self.spin_start.setSingleStep(fs)
        self.spin_end.setSingleStep(fs)

    def set_time_axis(self, time_data):
        self.current_time_data = time_data
        if time_data is not None and len(time_data) > 0:
            bounds = (time_data[0], time_data[-1])
            # Update bounds for all plots and items
            for p in self.plots:
                p.setXRange(*bounds)
            
            for c in self.cursors:
                c.setBounds(bounds)
                
            for r in self.regions:
                r.setBounds(bounds)
            
    def plot_topics(self, time_axis, data_dict, plot_map=None):
        self.plot_layout.clear()
        self.plots = []
        self.cursors = []
        self.regions = []
        
        if not data_dict:
            return

        if plot_map is None:
            plot_map = {t: 1 for t in data_dict.keys()}

        # Group topics by plot_id
        grouped = {}
        for topic, pid in plot_map.items():
            if topic in data_dict:
                if pid not in grouped: grouped[pid] = []
                grouped[pid].append(topic)
        
        # Sort plot ids
        sorted_pids = sorted(grouped.keys())
        colors = ['r', 'g', 'b', 'c', 'm', 'k', 'y', 'w']
        
        # Create plots
        for i, pid in enumerate(sorted_pids):
            # Create a PlotItem
            p = self.plot_layout.addPlot(row=i, col=0)
            p.showGrid(x=True, y=True)
            p.addLegend()
            
            # Link X axis to first plot
            if i > 0:
                p.setXLink(self.plots[0])
            
            topics = grouped[pid]
            for j, topic in enumerate(topics):
                color = colors[j % len(colors)]
                p.plot(time_axis, data_dict[topic], pen=pg.mkPen(color, width=2), name=topic)
            
            # Add Cursor (Time Line) - Green for visibility
            cursor = pg.InfiniteLine(angle=90, movable=True, pen=pg.mkPen('g', width=2))
            cursor.sigPositionChanged.connect(self.on_cursor_dragged)
            p.addItem(cursor)
            self.cursors.append(cursor)
            
            # Add Region Item
            region = pg.LinearRegionItem()
            region.setZValue(10)
            region.setBrush(pg.mkBrush(0, 0, 255, 30))
            
            # Customize Region Lines (Handles)
            # Left Line
            region.lines[0].setPen(pg.mkPen('b', width=2, style=Qt.PenStyle.SolidLine))

            # Right Line
            region.lines[1].setPen(pg.mkPen('b', width=2, style=Qt.PenStyle.SolidLine))

            region.sigRegionChanged.connect(self.on_region_dragged)
            p.addItem(region)
            self.regions.append(region)
            self.plots.append(p)
            
        # Restore the regions from the active spin box inputs
        self.update_timeline_from_inputs()

    def on_cursor_dragged(self, sender):
        if self.updating_cursor: return
        self.updating_cursor = True
        
        val = sender.value()
        
        # Sync other cursors
        for c in self.cursors:
            if c != sender:
                c.setValue(val)
                
        # Emit signal (once)
        if self.current_time_data is not None:
             frame_idx = int(round(val / self.fs))
             frame_idx = max(0, min(frame_idx, len(self.current_time_data) - 1))
             # Snap to time from current_time_data
             snapped_time = self.current_time_data[frame_idx]
             self.time_changed.emit(snapped_time, frame_idx)
             
        self.updating_cursor = False

    def on_region_dragged(self, sender):
        if self.updating_region: return
        self.updating_region = True
        
        region_vals = sender.getRegion()
        
        # Sync other regions and update handle orientations
        for r in self.regions:
            if r != sender:
                r.setRegion(region_vals)
            

        # Update inputs
        start, end = region_vals
        self.spin_start.blockSignals(True)
        self.spin_end.blockSignals(True)
        self.spin_start.setValue(start)
        self.spin_end.setValue(end)
        
        # Slider sync
        max_time = 1.0
        if self.current_time_data is not None and len(self.current_time_data) > 0:
            max_time = self.current_time_data[-1]
            if max_time <= 0: max_time = 1.0

        self.slider_start.blockSignals(True)
        self.slider_end.blockSignals(True)
        self.slider_start.setValue(int((start / max_time) * 1000))
        self.slider_end.setValue(int((end / max_time) * 1000))
        self.slider_start.blockSignals(False)
        self.slider_end.blockSignals(False)
        
        self.spin_start.blockSignals(False)
        self.spin_end.blockSignals(False)
        
        self.updating_region = False

    def set_position_by_frame(self, frame_idx):
        if self.current_time_data is not None and 0 <= frame_idx < len(self.current_time_data):
             t = self.current_time_data[frame_idx]
             self.updating_cursor = True
             for c in self.cursors:
                 c.setValue(t)
             self.updating_cursor = False

    def enable_range_selection(self, enabled=True):
        for r in self.regions:
            r.setVisible(enabled)

    def on_region_changed(self):
        pass

    def update_timeline_from_inputs(self):
        start = self.spin_start.value()
        end = self.spin_end.value()
        
        self.updating_region = True
        for r in self.regions:
            r.setRegion((start, end))
        self.updating_region = False
        
        # Keep sliders in sync
        max_time = 1.0
        if self.current_time_data is not None and len(self.current_time_data) > 0:
            max_time = self.current_time_data[-1]
            if max_time <= 0: max_time = 1.0

        self.slider_start.blockSignals(True)
        self.slider_end.blockSignals(True)
        self.slider_start.setValue(int((start / max_time) * 1000))
        self.slider_end.setValue(int((end / max_time) * 1000))
        self.slider_start.blockSignals(False)
        self.slider_end.blockSignals(False)

    def get_selected_range(self):
        if self.regions:
            return self.regions[0].getRegion()
        return (0, 0)
    
    def set_selected_range(self, start, end):
        self.updating_region = True
        for r in self.regions:
            r.setRegion((start, end))
            r.setVisible(True)
        self.updating_region = False

    def on_slider_start_changed(self, val):
        max_time = 1.0
        if self.current_time_data is not None and len(self.current_time_data) > 0:
            max_time = self.current_time_data[-1]
            if max_time <= 0: max_time = 1.0
            
        time_val = (val / 1000.0) * max_time
        self.spin_start.setValue(time_val) 
        
    def on_slider_end_changed(self, val):
        max_time = 1.0
        if self.current_time_data is not None and len(self.current_time_data) > 0:
            max_time = self.current_time_data[-1]
            if max_time <= 0: max_time = 1.0
            
        time_val = (val / 1000.0) * max_time
        self.spin_end.setValue(time_val)


class ADTFImageDisplayWidget(QWidget):
    frame_changed = pyqtSignal(int, int)  # current_index, total_frames
    set_range_start_requested = pyqtSignal(float)
    set_range_end_requested = pyqtSignal(float)
    
    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        # Controls layout
        controls_layout = QHBoxLayout()
        
        # Frame info label
        self.frame_info_label = QLabel("Frame: 0 / 0")
        self.frame_info_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        controls_layout.addWidget(self.frame_info_label)
        
        # Playback system
        self.play_timer = QTimer(self)
        self.play_timer.timeout.connect(self.play_next_frame)
        self.is_playing = False
        
        self.layout.addLayout(controls_layout)
        
        # ADTF loader
        from core.data_loader import ADTFLoader
        self.adtf_loader = ADTFLoader()
        
        # Current frame
        self.current_frame = None
        self.current_index = 0
        self.total_frames = 0
        
        # Set focus policy to receive keyboard events
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        
        # Separate image window
        self.image_window = None

    def load_adtf_file_from_path(self, file_path):
        """Loads ADTF file directly from a given absolute path."""
        if self.adtf_loader.load_file(file_path):
            self.total_frames = self.adtf_loader.get_total_frames()
            self.current_index = 0
            self.current_frame = self.adtf_loader.get_frame(0)
            self.update_image_window()
            self.frame_changed.emit(0, self.total_frames)

            # Open separate image window
            self.open_image_window()
    
    def toggle_playback(self):
        if self.is_playing:
            self.play_timer.stop()
            self.is_playing = False
        else:
            self.play_timer.start(33) # roughly 30 fps
            self.is_playing = True
            
    def play_next_frame(self):
        if self.current_index < self.total_frames - 1:
            self.navigate_next(1)
        else:
            self.toggle_playback() # Auto stop at the end
            
    def open_image_window(self):
        """Opens a separate window to display the image"""
        prev_geometry = None
        if self.image_window is not None:
            prev_geometry = self.image_window.geometry()
            self.image_window.close()
        
        self.image_window = QMainWindow()
        self.image_window.setWindowTitle(f"ADTF Image Viewer - Frame {self.current_index + 1}")
        
        if prev_geometry:
            self.image_window.setGeometry(prev_geometry)
        else:
            self.image_window.resize(1280, 720)
        
        # Create central widget with layout
        central_widget = QWidget()
        self.image_window.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Point the old image_layout to the main central layout
        self.image_layout = layout
        
        from PyQt6.QtWidgets import QSizePolicy
        
        # Create label for image display
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setStyleSheet("background-color: black;")
        self.image_label.setScaledContents(True) # Allow smooth user-driven scaling stretching
        self.image_label.setMinimumSize(1, 1)    # Crucial: Allow label to shrink below its pixmap size
        self.image_layout.addWidget(self.image_label, stretch=1)
        
        # Create label for frame info
        self.frame_info_label_window = QLabel()
        self.frame_info_label_window.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.frame_info_label_window.setStyleSheet("background-color: rgba(0, 0, 0, 150); color: white; font-weight: bold; padding: 5px;")
        self.frame_info_label_window.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        
        # Add index * (1.0/30.0) calculation requirement here
        time_s = self.current_index * (1.0 / 30.0)
        self.frame_info_label_window.setText(f"Index: {self.current_index} | Time: {time_s:.3f}s / {self.total_frames}")
        self.image_layout.addWidget(self.frame_info_label_window)
        
        # Create slider for frame navigation
        self.frame_slider = QSlider(Qt.Orientation.Horizontal)
        self.frame_slider.setRange(0, max(0, self.total_frames - 1))
        self.frame_slider.setValue(self.current_index)
        self.frame_slider.valueChanged.connect(self.on_frame_slider_changed)
        self.frame_slider.setFocusPolicy(Qt.FocusPolicy.NoFocus) # Prevent slider from stealing arrow keys
        self.frame_slider.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        layout.addWidget(self.frame_slider)
        
        # Make sure the window gets focus and handles key events
        self.image_window.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.image_window.setFocus()
        
        # Setup precise keyboard shortcuts instead of relying on eventFilters that might be swallowed
        from PyQt6.QtGui import QShortcut, QKeySequence
        QShortcut(QKeySequence(Qt.Key.Key_Space), self.image_window).activated.connect(self.toggle_playback)
        
        QShortcut(QKeySequence(Qt.Key.Key_Left), self.image_window).activated.connect(lambda: self.navigate_previous(1))
        QShortcut(QKeySequence(Qt.Modifier.SHIFT | Qt.Key.Key_Left), self.image_window).activated.connect(lambda: self.navigate_previous(10))
        QShortcut(QKeySequence(Qt.Modifier.CTRL | Qt.Key.Key_Left), self.image_window).activated.connect(lambda: self.navigate_previous(30))
        QShortcut(QKeySequence(Qt.Modifier.CTRL | Qt.Modifier.SHIFT | Qt.Key.Key_Left), self.image_window).activated.connect(lambda: self.navigate_previous(300))
        
        QShortcut(QKeySequence(Qt.Modifier.CTRL | Qt.Key.Key_Up), self.image_window).activated.connect(
            lambda: self.set_range_start_requested.emit(self.current_index * (1.0 / 30.0))
        )
        QShortcut(QKeySequence(Qt.Modifier.CTRL | Qt.Key.Key_Down), self.image_window).activated.connect(
            lambda: self.set_range_end_requested.emit(self.current_index * (1.0 / 30.0))
        )
        
        QShortcut(QKeySequence(Qt.Key.Key_Right), self.image_window).activated.connect(lambda: self.navigate_next(1))
        QShortcut(QKeySequence(Qt.Modifier.SHIFT | Qt.Key.Key_Right), self.image_window).activated.connect(lambda: self.navigate_next(10))
        QShortcut(QKeySequence(Qt.Modifier.CTRL | Qt.Key.Key_Right), self.image_window).activated.connect(lambda: self.navigate_next(30))
        QShortcut(QKeySequence(Qt.Modifier.CTRL | Qt.Modifier.SHIFT | Qt.Key.Key_Right), self.image_window).activated.connect(lambda: self.navigate_next(300))
        
        # Update the display
        self.update_image_window()
        
        # Show window
        self.image_window.show()
    
    def update_image_window(self):
        """Updates the image in the separate window"""
        if self.current_frame is not None and self.image_window is not None:
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
                self.image_window.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            
            self.image_label.setPixmap(scaled_pixmap)
            
            # Update window title with frame index
            self.image_window.setWindowTitle(f"ADTF Image Viewer - Frame {self.current_index + 1} / {self.total_frames}")
            
            # Update frame info label in window
            time_s = self.current_index * (1.0 / 30.0)
            self.frame_info_label_window.setText(f"Index: {self.current_index} | Time: {time_s:.3f}s / {self.total_frames}")
        
        # Update frame info in main widget
        self.frame_info_label.setText(f"Frame: {self.current_index + 1} / {self.total_frames}")
    
    def navigate_next(self, step=1):
        """Navigate to next frame"""
        if self.current_index < self.total_frames - 1:
            self.current_index = min(self.total_frames - 1, self.current_index + step)
            self.current_frame = self.adtf_loader.get_frame(self.current_index)
            self.update_image_window()
            # update slider without triggering double events
            if self.image_window:
                self.frame_slider.blockSignals(True)
                self.frame_slider.setValue(self.current_index)
                self.frame_slider.blockSignals(False)
            self.frame_changed.emit(self.current_index, self.total_frames)
    
    def on_frame_slider_changed(self, value):
        """Handle frame slider change"""
        if value != self.current_index:
            self.current_index = value
            self.current_frame = self.adtf_loader.get_frame(self.current_index)
            self.update_image_window()
            self.frame_changed.emit(self.current_index, self.total_frames)
    
    def navigate_previous(self, step=1):
        """Navigate to previous frame"""
        if self.current_index > 0:
            self.current_index = max(0, self.current_index - step)
            self.current_frame = self.adtf_loader.get_frame(self.current_index)
            self.update_image_window()
            if self.image_window:
                self.frame_slider.blockSignals(True)
                self.frame_slider.setValue(self.current_index)
                self.frame_slider.blockSignals(False)
            self.frame_changed.emit(self.current_index, self.total_frames)
    
    def get_current_frame_index(self):
        return self.current_index
    
    def get_total_frames(self):
        return self.total_frames
    
        # The eventFilter logic handling left/right keys is removed as it's superseded by QShortcut
        return super().eventFilter(obj, event)
    
    def closeEvent(self, event):
        """Clean up when widget is closed"""
        self.adtf_loader.close()
        event.accept()
