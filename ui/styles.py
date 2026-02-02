
STYLESHEET = """
/* Global Reset */
QWidget {
    font-family: 'Segoe UI', 'Roboto', sans-serif;
    font-size: 14px;
    color: #333333;
    background-color: #F4F6F9; /* Light Gray Background */
}

/* Main Window */
QMainWindow {
    background-color: #F4F6F9;
}

/* Frames & Panels with "Card" look */
QFrame, QGroupBox {
    background-color: #FFFFFF;
    border: 1px solid #E0E0E0;
    border-radius: 8px;
}

QGroupBox {
    margin-top: 20px;
    font-weight: bold;
    color: #555;
    background-color: #FFFFFF;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 5px;
    color: #007BFF;
}

/* Splitter */
QSplitter::handle {
    background-color: #E0E0E0;
    width: 2px;
}

/* Labels */
QLabel {
    background-color: transparent;
    border: none;
    color: #333;
    padding: 2px;
}
QLabel[heading="true"] {
    font-size: 16px;
    font-weight: bold;
    color: #007BFF;
    margin-bottom: 5px;
}

/* Buttons */
QPushButton {
    background-color: #007BFF; /* Primary Blue */
    color: white;
    border: none;
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: bold;
}
QPushButton:hover {
    background-color: #0056b3;
}
QPushButton:pressed {
    background-color: #004085;
}
QPushButton:disabled {
    background-color: #CCCCCC;
    color: #666666;
}

/* Secondary / Danger Buttons (using ObjectID or property logic if possible, otherwise generic override in code) */
/* For now, Delete buttons will need manual style patch or object name. */

/* Inputs */
QLineEdit, QComboBox, QDoubleSpinBox, QSpinBox {
    background-color: #FFFFFF;
    border: 1px solid #CED4DA;
    border-radius: 4px;
    padding: 6px;
    selection-background-color: #007BFF;
    color: #333;
}
QLineEdit:focus, QComboBox:focus, QDoubleSpinBox:focus {
    border: 1px solid #007BFF;
}

QComboBox::drop-down {
    border: none;
    background: transparent;
}
QComboBox::down-arrow {
    image: none; /* Can replace with icon if needed, or stick to default */
    border-left: 1px solid #CED4DA; /* Visual separator */
    width: 10px;
    height: 10px;
    /* Drawing a simple arrow with border/background is hard in pure QSS without image resource */
}

/* Lists and Tables */
QListWidget, QTableWidget {
    background-color: #FFFFFF;
    border: 1px solid #E0E0E0;
    border-radius: 6px;
    gridline-color: #F0F0F0;
    outline: none;
}
QListWidget::item, QTableWidget::item {
    padding: 8px;
    border-bottom: 1px solid #F9F9F9;
}
QListWidget::item:selected, QTableWidget::item:selected {
    background-color: #E8F0FE; /* Light Blue selection */
    color: #007BFF;
}
QHeaderView::section {
    background-color: #FFFFFF;
    padding: 8px;
    border: none;
    border-bottom: 2px solid #007BFF;
    font-weight: bold;
    color: #555;
}

/* Scrollbars - styling them to be cleaner */
QScrollBar:vertical {
    border: none;
    background: #F1F1F1;
    width: 10px;
    margin: 0px 0px 0px 0px;
    border-radius: 5px;
}
QScrollBar::handle:vertical {
    background: #C1C1C1;
    min-height: 20px;
    border-radius: 5px;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

QScrollBar:horizontal {
    border: none;
    background: #F1F1F1;
    height: 10px;
    margin: 0px 0px 0px 0px;
    border-radius: 5px;
}
QScrollBar::handle:horizontal {
    background: #C1C1C1;
    min-width: 20px;
    border-radius: 5px;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0px;
}

/* Radio Buttons - High Visibility Selection */
QRadioButton {
    spacing: 8px;
    padding: 6px 10px;
    border-radius: 4px;
    color: #555;
    background-color: #FFFFFF; /* Ensure background for consistency */
}

QRadioButton::indicator {
    width: 16px;
    height: 16px;
    border-radius: 9px; /* Round */
    border: 1px solid #ADB5BD;
    background-color: #FFFFFF;
}

QRadioButton::indicator:checked {
    border: 5px solid #007BFF; /* Creates a "dot" effect by using thick border */
    background-color: #FFFFFF; 
    /* Alternatively for a filled circle: 
       background-color: #007BFF; border: 2px solid white; outline: 1px solid #007BFF; (not supported)
       Current trick: Thick blue border with tiny white hole, or thick white border with blue center?
       Let's do: Thick Blue Border makes it look like a Ring. 
       Let's do: border 4px solid #007BFF; background #FFF ? No.
       Let's try standard 'Dot' simulated by border.
       border: 4px solid #FFFFFF; background-color: #007BFF; (with shadow or outer ring?)
       QSS is limited.
       Let's try: border: 5px solid #007BFF is a solid blue circle if radius is correct? No inner hole.
       Let's try: border: 4px solid white; background-color: #007BFF; ... wait, we need the outer ring.
    */
    border: 1px solid #007BFF;
    background-color: qradialgradient(
        cx: 0.5, cy: 0.5, radius: 0.4,
        fx: 0.5, fy: 0.5,
        stop: 0 #007BFF,
        stop: 1 #007BFF
    );
    /* Actually simple trick: image: none; background-color: #007BFF  + small white border? */
}

/* Better "Dot" simulation */
QRadioButton::indicator:checked {
    background-color: white;
    border: 5px solid #007BFF; /* Thick border makes it look like a donut/dot inverted? No. */
}

/* Let's keep it simple and clean: Filled Blue Circle */
QRadioButton::indicator:checked {
    background-color: #007BFF;
    border: 1px solid #007BFF;
    image: url(none); /* Remove default */
}
/* But we usually want a dot inside. 
   How about use the unicode dot? No.
   Let's stick to the "Selected Box" style being the primary indicator, and the circle being just solid blue.
*/

QRadioButton:checked {
    background-color: #E8F0FE; /* Light Blue Background */
    color: #007BFF; /* Primary Blue Text */
    font-weight: bold;
    border: 1px solid #007BFF;
}
QRadioButton:hover {
    background-color: #F8F9FA;
}
"""
