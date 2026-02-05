import pyqtgraph as pg
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QSlider, QDoubleSpinBox)
from PyQt6.QtCore import pyqtSignal, Qt


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

    # ... (End B controls are same, skipping for brevity in replacement if unchanged, but I must replace contiguous block)
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
        # Determine visibility based on enabled
        # But we create them in plot_topics now.
        # Just toggle visibility of all existing regions
        for r in self.regions:
            r.setVisible(enabled)

    def on_region_changed(self):
        # Legacy stub or redirect?
        # The logic is moved to on_region_dragged
        pass

    def update_timeline_from_inputs(self):
        start = self.spin_start.value()
        end = self.spin_end.value()
        
        self.updating_region = True
        for r in self.regions:
            r.setRegion((start, end))
        self.updating_region = False

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
