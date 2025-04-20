# main_modern.py

import sys
import threading
from pathlib import Path

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QStackedWidget,
    QAction, QActionGroup, QToolBar, QStatusBar,
    QToolButton
)
from PyQt5.QtGui import QIcon, QFont
from PyQt5.QtCore import Qt, QSize

from eye_widget import EyeTrackerWidget
from hand_widget import HandTrackerWidget
import audio
class ListeningOverlay(QToolButton):
    """An always‑on‑top “Steven is listening…” badge that ignores clicks."""
    def __init__(self):
        super().__init__()
        # Make it a frameless, always‑on‑top tooltip window
        self.setWindowFlags(
            Qt.ToolTip |
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint
        )
        # Let clicks pass through
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)

        # Icon + text
        self.setIcon(QIcon(str(Path(__file__).parent / "icons/mic.svg")))
        self.setIconSize(QSize(32, 32))
        self.setText(" Steven is listening…")
        self.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.setFont(QFont("Sans Serif", 11, QFont.Bold))
        self.setStyleSheet("""
            QToolButton {
                background-color: #3B4252;
                color: #ECEFF4;
                border: 2px solid #81A1C1;
                border-radius: 8px;
                padding: 6px;
            }
        """)
        self.adjustSize()

        # Position top‑right
        geom = QApplication.primaryScreen().availableGeometry()
        x = geom.x() + geom.width() - self.width() - 20
        y = geom.y() + 20
        self.move(x, y)
        self.show()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Adaptive Hands‑Free Control")
        self.resize(1000, 700)

        # — stack of eye/hand widgets —
        self.stack    = QStackedWidget()
        self.eye_tab  = EyeTrackerWidget()
        self.hand_tab = HandTrackerWidget()
        self.stack.addWidget(self.eye_tab)
        self.stack.addWidget(self.hand_tab)
        self.setCentralWidget(self.stack)

        # when eye calibration completes, collapse into corner
        self.eye_tab.calibration_complete.connect(self._collapse_to_corner)

        # — always‑on‑top Steven badge —
        self.listen_overlay = ListeningOverlay()



        # — toolbar for switching modes —
        tb = QToolBar("Mode")
        tb.setIconSize(QSize(48,48))
        tb.setMovable(False)
        self.addToolBar(tb)

        mode_group = QActionGroup(self)
        mode_group.setExclusive(True)

        # Eye Control button
        eye_icon = QIcon(str(Path(__file__).parent / "icons/eye.svg"))
        act_eye = QAction(eye_icon, "Eye Control", self, checkable=True)
        act_eye.triggered.connect(lambda: self._switch_mode(0))
        mode_group.addAction(act_eye)
        tb.addAction(act_eye)

        # Hand Control button
        hand_icon = QIcon(str(Path(__file__).parent / "icons/hand.svg"))
        act_hand = QAction(hand_icon, "Hand Control", self, checkable=True)
        act_hand.triggered.connect(lambda: self._switch_mode(1))
        mode_group.addAction(act_hand)
        tb.addAction(act_hand)

        # static mic icon in toolbar (purely decorative)
        mic_btn = QToolButton(self)
        mic_btn.setIcon(QIcon(str(Path(__file__).parent / "icons/mic.svg")))
        mic_btn.setIconSize(QSize(32,32))
        mic_btn.setToolTip("🎤 Steven is listening")
        tb.addWidget(mic_btn)

        # default to Eye Control
        act_eye.setChecked(True)
        self._switch_mode(0)

        # status bar
        self.setStatusBar(QStatusBar(self))

    def _switch_mode(self, index: int):
        # stop whichever was running
        self.eye_tab.stop_tracking()
        self.hand_tab.stop_tracking()

        # switch the visible tab
        self.stack.setCurrentIndex(index)
        if index == 0:
            self.eye_tab.start_tracking()
            self.statusBar().showMessage("👁  Eye Control Mode", 2000)
        else:
            self.hand_tab.start_tracking()
            self.statusBar().showMessage("✋  Hand Control Mode", 2000)
            # as soon as they pick Hand Control, collapse the UI
            self._collapse_to_corner()

        # keep Steven badge above everything
        self.listen_overlay.raise_()
        self.listen_overlay.show()

    def _collapse_to_corner(self):
        """Shrink into a small always‑on‑top window in the top‑right corner."""
        # hide toolbar & status bar
        for tb in self.findChildren(QToolBar):
            tb.hide()
        self.statusBar().hide()

        # hide the entire central stack
        self.stack.hide()

        # resize & reposition this QMainWindow
        w, h = 200, 150
        geom = QApplication.primaryScreen().availableGeometry()
        x = geom.x() + geom.width() - w - 20
        y = geom.y() + 20

        # make it frameless & always‑on‑top
        self.setWindowFlags(
            self.windowFlags()
            | Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
        )
        self.setGeometry(x, y, w, h)
        self.show()

    def closeEvent(self, event):
        # clean up everything
        self.eye_tab.stop_tracking()
        self.hand_tab.stop_tracking()
        self.listen_overlay.hide()
        super().closeEvent(event)


if __name__ == "__main__":
    app = QApplication(sys.argv)

    # — dark, modern stylesheet —
    app.setStyleSheet("""
      QMainWindow { background: #2E3440; }
      QToolBar { background: #3B4252; spacing: 12px; padding: 6px; }
      QToolButton { background: transparent; border: none; }
      QToolButton:hover { background: rgba(200,200,200,0.1); border-radius: 4px; }
      QStatusBar { background: #3B4252; color: #D8DEE9; }
    """)

    win = MainWindow()
    win.show()
    sys.exit(app.exec_())