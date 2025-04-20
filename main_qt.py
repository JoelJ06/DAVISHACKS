# main_modern.py
import sys
from pathlib import Path
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QStackedWidget, QAction, QActionGroup,
    QToolBar, QStatusBar
)
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import QSize

from eye_widget  import EyeTrackerWidget
from hand_widget import HandTrackerWidget

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Adaptive Hands‑Free Control")
        self.resize(1000, 700)

        # Central stack widget
        self.stack = QStackedWidget()
        self.eye_tab  = EyeTrackerWidget()
        self.hand_tab = HandTrackerWidget()
        self.stack.addWidget(self.eye_tab)
        self.stack.addWidget(self.hand_tab)
        self.setCentralWidget(self.stack)

        # Toolbar with big icons
        tb = QToolBar("Mode")
        tb.setIconSize(QSize(48,48))
        tb.setMovable(False)
        self.addToolBar(tb)

        # Exclusive action group
        group = QActionGroup(self)
        group.setExclusive(True)

        # Eye Control button
        eye_icon = QIcon(str(Path(__file__).parent / "icons/eye.svg"))
        act_eye = QAction(eye_icon, "Eye Control", self, checkable=True)
        act_eye.triggered.connect(lambda: self.switch_mode(0))
        group.addAction(act_eye)
        tb.addAction(act_eye)

        # Hand Control button
        hand_icon = QIcon(str(Path(__file__).parent / "icons/hand.svg"))
        act_hand = QAction(hand_icon, "Hand Control", self, checkable=True)
        act_hand.triggered.connect(lambda: self.switch_mode(1))
        group.addAction(act_hand)
        tb.addAction(act_hand)

        # Default to Eye Control
        act_eye.setChecked(True)
        self.switch_mode(0)

        # Status bar for feedback
        self.setStatusBar(QStatusBar(self))

    def switch_mode(self, index: int):
        # stop both before starting the selected one
        self.eye_tab.stop_tracking()
        self.hand_tab.stop_tracking()
        self.stack.setCurrentIndex(index)
        if index == 0:
            self.eye_tab.start_tracking()
            self.statusBar().showMessage("Eye Control Mode Active", 3000)
        else:
            self.hand_tab.start_tracking()
            self.statusBar().showMessage("Hand Control Mode Active", 3000)

    def closeEvent(self, event):
        # ensure resources freed
        self.eye_tab.stop_tracking()
        self.hand_tab.stop_tracking()
        super().closeEvent(event)

if __name__ == "__main__":
    app = QApplication(sys.argv)

    # Simple dark theme
    app.setStyleSheet("""
      QMainWindow { background: #2E3440; }
      QToolBar { background: #3B4252; spacing: 12px; padding: 6px; }
      QToolButton { background: transparent; border: none; }
      QToolButton:checked { background: #81A1C1; border-radius: 8px; }
      QStatusBar { background: #3B4252; color: #D8DEE9; }
    """)

    win = MainWindow()
    win.show()
    sys.exit(app.exec_())