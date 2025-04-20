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
        self.eye_tab  = EyeTrackerWidget()
        self.hand_tab = HandTrackerWidget()

        tabs.addTab(self.eye_tab,  "Eye Control")
        tabs.addTab(self.hand_tab, "Hand Control")
        tabs.currentChanged.connect(self.on_tab_changed)

        self.setCentralWidget(tabs)
        # start with eye‑tracking active:
        self.eye_tab.start_tracking()

    def on_tab_changed(self, index):
        # stop both first…
        self.eye_tab.stop_tracking()
        self.hand_tab.stop_tracking()
        # …then start only the newly selected one
        if index == 0:
            self.eye_tab.start_tracking()
        else:
            self.hand_tab.start_tracking()

    def closeEvent(self, event):
        # ensure cleanup
        self.eye_tab.stop_tracking()
        self.hand_tab.stop_tracking()
        super().closeEvent(event)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec_())