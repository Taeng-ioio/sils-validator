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
        # We need a reference plot for time line and region (usually the first one)
        self.ref_plot = None 

        # Time Indicator (Vertical Line)
        self.time_line = pg.InfiniteLine(angle=90, movable=True, pen=pg.mkPen('b', width=2))
        self.time_line.sigPositionChanged.connect(self.on_line_dragged)
        
        # Region Item (Range Selection)
        self.region_item = pg.LinearRegionItem()
        self.region_item.setZValue(10)
        self.region_item.sigRegionChanged.connect(self.on_region_changed)
        self.region_item.setVisible(False)
        
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

    def set_time_axis(self, time_data):
        self.current_time_data = time_data
        if time_data is not None and len(time_data) > 0:
            # Update bounds for all plots
            for p in self.plots:
                p.setXRange(time_data[0], time_data[-1])
            
            self.time_line.setBounds((time_data[0], time_data[-1]))
            
    def plot_topics(self, time_axis, data_dict, plot_map=None):
        """
        data_dict: { "topic_name": [values...], ... }
        plot_map: { "topic_name": plot_id (int), ... }
                  If None, all go to plot 1.
        """
        # Remove items from previous usage to be safe (BEFORE clearing layout)
        if self.ref_plot is not None:
            try:
                self.ref_plot.removeItem(self.time_line)
                self.ref_plot.removeItem(self.region_item)
            except:
                pass

        if self.time_line.scene() is not None:
             self.time_line.scene().removeItem(self.time_line)
        if self.region_item.scene() is not None:
             self.region_item.scene().removeItem(self.region_item)

        self.plot_layout.clear()
        self.plots = []
        self.ref_plot = None
        
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
                # Unique color per topic in this plot (or global? let's cycle)
                # To distinguish topics easily, we might want a hashed color or simple cycle
                color = colors[j % len(colors)]
                p.plot(time_axis, data_dict[topic], pen=pg.mkPen(color, width=2), name=topic)
            
            self.plots.append(p)

        if self.plots:
            self.ref_plot = self.plots[0]
            # Add timeline and region to the ALL plots -> Actually, 
            # infinite line can be added to all. Region usually on one or all.
            # Visual clutter if on all. Let's add timeline line to ALL, region to ALL (synced).
            # Actually, LinearRegionItem is an Item, it can only belong to ONE ViewBox/PlotItem.
            # So we usually put it on the top plot or create one for each plot.
            # For Simplicity: Put Region on ALL plots (create new items?)
            # Or just put on the first one. Let's put InfiniteLine on ALL.
            
            # Re-initialize shared items for the FIRST plot logic
            # Use a helper to manage the multi-plot cursors if needed
            # But pg.InfiniteLine can only be in one plot.
            # We need multiple lines synced? Or just add it to the first plot and draw a line across?
            # Easier: Add separate InfiniteLine instances for each plot, sync signals.
            # OR: usage of linkView?
            
            # Simple approach: Primary controls on TOP plot.
            self.ref_plot.addItem(self.time_line)
            self.ref_plot.addItem(self.region_item)
            
            # For other plots, we want to see the vertical line too.
            # We can create aux lines.
            self.aux_lines = []
            for p in self.plots[1:]:
                l = pg.InfiniteLine(angle=90, movable=False, pen=pg.mkPen('b', width=2, style=Qt.PenStyle.DashLine))
                p.addItem(l)
                self.aux_lines.append(l)
                
            # Sync needed in on_line_dragged
            
    def on_line_dragged(self):
        val = self.time_line.value()
        
        # Sync aux lines
        if hasattr(self, 'aux_lines'):
            for l in self.aux_lines:
                l.setValue(val)
                
        # Find nearest frame index
        if self.current_time_data is not None:
            # Simple assumption: uniform sampling
            frame_idx = int(round(val / self.fs))
            # Clamp
            frame_idx = max(0, min(frame_idx, len(self.current_time_data) - 1))
            
            # Snap line to frame
            snapped_time = self.current_time_data[frame_idx]
            
            # Avoid feedback loop if we move programmatically
            # self.time_line.setValue(snapped_time) # Optional snapping behavior
            
            self.time_changed.emit(snapped_time, frame_idx)

    def set_position_by_frame(self, frame_idx):
        if self.current_time_data is not None and 0 <= frame_idx < len(self.current_time_data):
             t = self.current_time_data[frame_idx]
             self.time_line.setValue(t)
             # Aux lines will update on signal or we set them here
             if hasattr(self, 'aux_lines'):
                 for l in self.aux_lines:
                     l.setValue(t)

    def enable_range_selection(self, enabled=True):
        if not hasattr(self, 'region_item'):
            self.region_item = pg.LinearRegionItem()
            self.region_item.setZValue(10)
            self.region_item.sigRegionChanged.connect(self.on_region_changed)
            self.plot_widget.addItem(self.region_item)
        
        self.region_item.setVisible(enabled)

    def on_region_changed(self):
        if not hasattr(self, 'region_item'): return
        
        start, end = self.region_item.getRegion()
        
        # Update inputs without triggering loop
        self.spin_start.blockSignals(True)
        self.spin_end.blockSignals(True)
        self.slider_start.blockSignals(True)
        self.slider_end.blockSignals(True)
        
        self.spin_start.setValue(start)
        self.spin_end.setValue(end)
        
        # Map to slider
        max_time = 1.0
        if self.current_time_data is not None and len(self.current_time_data) > 0:
            max_time = self.current_time_data[-1]
            if max_time <= 0: max_time = 1.0

        self.slider_start.setValue(int((start / max_time) * 1000))
        self.slider_end.setValue(int((end / max_time) * 1000))

        self.spin_start.blockSignals(False)
        self.spin_end.blockSignals(False)
        self.slider_start.blockSignals(False)
        self.slider_end.blockSignals(False)

    def update_timeline_from_inputs(self):
        start = self.spin_start.value()
        end = self.spin_end.value()
        
        if hasattr(self, 'region_item'):
            self.region_item.blockSignals(True)
            self.region_item.setRegion((start, end))
            self.region_item.blockSignals(False)

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

    def get_selected_range(self):
        if hasattr(self, 'region_item') and self.region_item.isVisible():
            return self.region_item.getRegion()
        return (0, 0)
    
    def set_selected_range(self, start, end):
        self.enable_range_selection(True)
        # Block signals to prevent feedback loop if calling from UI
        self.region_item.setRegion((start, end))
