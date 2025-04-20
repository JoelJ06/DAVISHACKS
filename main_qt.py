# main_modern.py

import sys
import os
import threading
from pathlib import Path

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QStackedWidget,
    QAction, QActionGroup, QToolBar, QStatusBar,
    QToolButton, QShortcut
)
from PyQt5.QtGui import QIcon, QFont, QKeySequence
from PyQt5.QtCore import Qt, QSize

from eye_widget import EyeTrackerWidget
from hand_widget import HandTrackerWidget
import audio  # your voice assistant module

class ListeningOverlay(QToolButton):
    """An always‑on‑top “Steven is listening…” badge that ignores clicks."""
    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.ToolTip |
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
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
        geom = QApplication.primaryScreen().availableGeometry()
        self.move(geom.right() - self.width() - 20, geom.top() + 20)
        self.show()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Adaptive Hands‑Free Control")
        self.resize(1000, 700)
        self._collapsed = False

        # central stack
        self.stack    = QStackedWidget()
        self.eye_tab  = EyeTrackerWidget()
        self.hand_tab = HandTrackerWidget()
        self.stack.addWidget(self.eye_tab)
        self.stack.addWidget(self.hand_tab)
        self.setCentralWidget(self.stack)

        # collapse on calibration
        self.eye_tab.calibration_complete.connect(self._collapse_to_corner)

        # overlay badge
        self.listen_overlay = ListeningOverlay()

        # optional: start audio assistant
        # threading.Thread(target=audio.run_assistant, daemon=True).start()

        # toolbar
        tb = QToolBar("Mode")
        tb.setIconSize(QSize(48,48))
        tb.setMovable(False)
        self.addToolBar(tb)
        mode_group = QActionGroup(self)
        mode_group.setExclusive(True)

        eye_icon = QIcon(str(Path(__file__).parent / "icons/eye.svg"))
        act_eye = QAction(eye_icon, "Eye Control", self, checkable=True)
        act_eye.triggered.connect(lambda: self._switch_mode(0))
        mode_group.addAction(act_eye)
        tb.addAction(act_eye)

        hand_icon = QIcon(str(Path(__file__).parent / "icons/hand.svg"))
        act_hand = QAction(hand_icon, "Hand Control", self, checkable=True)
        act_hand.triggered.connect(lambda: self._switch_mode(1))
        mode_group.addAction(act_hand)
        tb.addAction(act_hand)

        mic_btn = QToolButton(self)
        mic_btn.setIcon(QIcon(str(Path(__file__).parent / "icons/mic.svg")))
        mic_btn.setIconSize(QSize(32,32))
        mic_btn.setToolTip("🎤 Steven is listening")
        tb.addWidget(mic_btn)

        act_eye.setChecked(True)
        self._switch_mode(0)
        self.setStatusBar(QStatusBar(self))

        # Q shortcut as application‑wide
        self._restart_sc = QShortcut(QKeySequence("Q"), self)
        self._restart_sc.setContext(Qt.ApplicationShortcut)
        self._restart_sc.activated.connect(self._restart_app)

    def keyPressEvent(self, event):
        # fallback if QShortcut ever fails
        if event.key() == Qt.Key_Q:
            self._restart_app()
        else:
            super().keyPressEvent(event)

    def _restart_app(self):
        """Re‑launch this script, returning to the initial screen."""
        python = sys.executable
        os.execv(python, [python] + sys.argv)

    def _switch_mode(self, index: int):
        self.eye_tab.stop_tracking()
        self.hand_tab.stop_tracking()
        self.stack.setCurrentIndex(index)
        if index == 0:
            self.eye_tab.start_tracking()
            self.statusBar().showMessage("👁  Eye Control Mode", 2000)
        else:
            self.hand_tab.start_tracking()
            self.statusBar().showMessage("✋  Hand Control Mode", 2000)
            self._collapse_to_corner()
        self.listen_overlay.raise_()
        self.listen_overlay.show()

    def _collapse_to_corner(self):
        if self._collapsed:
            return
        self._collapsed = True
        for tb in self.findChildren(QToolBar):
            tb.hide()
        self.statusBar().hide()
        self.stack.hide()
        flags = (self.windowFlags()
                 | Qt.FramelessWindowHint
                 | Qt.WindowStaysOnTopHint
                 | Qt.Tool)
        self.setWindowFlags(flags)
        geom = QApplication.primaryScreen().availableGeometry()
        w, h = 200, 150
        self.setGeometry(geom.right()-w-20, geom.top()+20, w, h)
        self.show()

    def closeEvent(self, event):
        self.eye_tab.stop_tracking()
        self.hand_tab.stop_tracking()
        self.listen_overlay.hide()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
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