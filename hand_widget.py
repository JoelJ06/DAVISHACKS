import cv2
import mediapipe as mp
import numpy as np
import pyautogui

from PyQt5.QtWidgets import QWidget, QLabel, QVBoxLayout
from PyQt5.QtCore    import Qt, QTimer
from PyQt5.QtGui     import QImage, QPixmap

class ClickController:
    """Pinch (thumb‑index) on right hand toggles mouseDown/mouseUp."""
    def __init__(self):
        self.down   = False
        self.thresh = 40

    def update(self, thumb, index):
        d    = np.hypot(thumb[0]-index[0], thumb[1]-index[1])
        prev = self.down
        self.down = (d < self.thresh)
        if self.down and not prev:
            pyautogui.mouseDown()
        elif not self.down and prev:
            pyautogui.mouseUp()

class HandTrackerWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.video = QLabel(alignment=Qt.AlignCenter)
        QVBoxLayout(self).addWidget(self.video)

        pyautogui.FAILSAFE = False
        self.ctrl = ClickController()
        self.sw, self.sh = pyautogui.size()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._frame)

    def start_tracking(self):
        self.cap   = cv2.VideoCapture(0)
        self.hands = mp.solutions.hands.Hands(
            max_num_hands=2,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        self.timer.start(30)

    def stop_tracking(self):
        self.timer.stop()
        if hasattr(self, 'cap'):
            self.cap.release()

    def _frame(self):
        ret, frame = self.cap.read()
        if not ret: return

        frame = cv2.flip(frame, 1)
        rgb   = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        res   = self.hands.process(rgb)
        h, w, _ = frame.shape
        left_found = False

        if res.multi_hand_landmarks and res.multi_handedness:
            for lm, hd in zip(res.multi_hand_landmarks, res.multi_handedness):
                label = hd.classification[0].label
                ip = lm.landmark[8]   # index tip
                tp = lm.landmark[4]   # thumb tip
                ix, iy = int(ip.x * w), int(ip.y * h)
                tx, ty = int(tp.x * w), int(tp.y * h)

                mp.solutions.drawing_utils.draw_landmarks(
                    frame, lm, mp.solutions.hands.HAND_CONNECTIONS
                )

                if label == "Left":
                    # left hand → move cursor
                    sx = int(ix * self.sw / w)
                    sy = int(iy * self.sh / h)
                    pyautogui.moveTo(sx, sy)
                    cv2.circle(frame, (ix, iy), 10, (0,255,0), -1)
                    left_found = True

                else:
                    # right hand → pinch click
                    self.ctrl.update((tx,ty),(ix,iy))
                    color = (0,0,255) if self.ctrl.down else (0,255,0)
                    cv2.line(frame, (ix,iy), (tx,ty), color, 3)

        if not left_found:
            # release any held click if no left hand present
            self.ctrl.update((0,0),(9999,9999))

        # preview
        h2, w2, _ = frame.shape
        img = QImage(frame.data, w2, h2, 3*w2, QImage.Format_RGB888).rgbSwapped()
        self.video.setPixmap(QPixmap.fromImage(img))

    def closeEvent(self, event):
        if hasattr(self, 'cap'):
            self.cap.release()
        super().closeEvent(event)