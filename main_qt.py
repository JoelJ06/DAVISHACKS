import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QTabWidget
from eye_widget  import EyeTrackerWidget
from hand_widget import HandTrackerWidget

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Adaptive Hands‑Free Control")
        self.resize(800, 600)

        tabs = QTabWidget()
        tabs.addTab(EyeTrackerWidget(),  "Eye Control")
        tabs.addTab(HandTrackerWidget(), "Hand Control")
        self.setCentralWidget(tabs)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec_())