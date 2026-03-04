import sys
from PyQt6.QtWidgets import QApplication
from ui.dat_viewer import DatViewerWindow

app = QApplication(sys.argv)
try:
    window = DatViewerWindow("dummy.dat")
    window.show()
    print("Window shown successfully")
except Exception as e:
    import traceback
    traceback.print_exc()
    print(f"Exception: {e}")
