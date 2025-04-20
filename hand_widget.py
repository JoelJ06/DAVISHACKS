# hand_widget.py

import cv2
import mediapipe as mp
import numpy as np
import pyautogui

from PyQt5.QtWidgets import QWidget, QLabel, QVBoxLayout
from PyQt5.QtCore    import Qt, QTimer
from PyQt5.QtGui     import QImage, QPixmap

class ClickController:
    def __init__(self):
        self.down   = False
        self.thresh = 40

    def update(self, thumb_pos, index_pos):
        d = np.hypot(thumb_pos[0]-index_pos[0], thumb_pos[1]-index_pos[1])
        prev = self.down
        self.down = d < self.thresh
        
        # Handle regular clicking
        if self.down and not prev:
            pyautogui.mouseDown()
        elif not self.down and prev:
            pyautogui.mouseUp()
        
        self.scroll_mode = False
        self.last_y = None
            
    def update_with_landmarks(self, tp, ip, landmarks):
        # First process basic click detection
        self.update(tp, ip)
        
        # Check if pointer and middle fingers are pinched for scrolling
        pointer_tip = landmarks.landmark[8]
        middle_tip = landmarks.landmark[12]
        pinch_distance = np.hypot(pointer_tip.x - middle_tip.x, pointer_tip.y - middle_tip.y)
        
        if pinch_distance < 0.05:  # Threshold for pinch detection
            # We're in scroll mode
            current_y = (pointer_tip.y + middle_tip.y) / 2  # Average Y position
            
            if self.scroll_mode and self.last_y is not None:
                # Calculate scroll amount
                y_diff = current_y - self.last_y
                if abs(y_diff) > 0.01:  # Threshold to prevent tiny movements
                    scroll_amount = int(y_diff * 200)  # Adjust sensitivity
                    pyautogui.scroll(-scroll_amount)
            
            self.last_y = current_y
            self.scroll_mode = True
            # Cancel any click that was detected
            if self.down:
                pyautogui.mouseUp()
        
            
            self.scroll_mode = False
            self.last_y = None

class HandTrackerWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.video = QLabel(alignment=Qt.AlignCenter)
        QVBoxLayout(self).addWidget(self.video)

        pyautogui.FAILSAFE = False
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._frame)

        self.ctrl       = ClickController()
        self.screen_w, self.screen_h = pyautogui.size()

    def start_tracking(self):
        self.cap   = cv2.VideoCapture(0)
        self.hands = mp.solutions.hands.Hands(
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        self.timer.start(30)

    def stop_tracking(self):
        self.timer.stop()
        if hasattr(self, 'cap') and self.cap:
            self.cap.release()
            self.cap = None

    def _frame(self):
        ret, fr = self.cap.read()
        if not ret:
            return

        fr = cv2.flip(fr, 1)  # mirror so it matches the eye‑tracker
        h, w, _ = fr.shape
        rgb = cv2.cvtColor(fr, cv2.COLOR_BGR2RGB)
        res = self.hands.process(rgb)

        left_found = False

        if res.multi_hand_landmarks and res.multi_handedness:
            for lm, hd in zip(res.multi_hand_landmarks, res.multi_handedness):
                label = hd.classification[0].label
                ip = lm.landmark[8]  # index tip
                tp = lm.landmark[4]  # thumb tip
                ix, iy = int(ip.x*w), int(ip.y*h)
                tx, ty = int(tp.x*w), int(tp.y*h)

                mp.solutions.drawing_utils.draw_landmarks(
                    fr, lm, mp.solutions.hands.HAND_CONNECTIONS
                )

                if label == "Left":
                    # move cursor
                    sx = int(ix * self.screen_w / w)
                    sy = int(iy * self.screen_h / h)
                    pyautogui.moveTo(sx, sy)
                    cv2.circle(fr, (ix, iy), 10, (0,255,0), -1)
                    left_found = True
                else:
                    # right hand triggers click
                    self.ctrl.update((tx,ty), (ix,iy))
                    clr = (0,0,255) if self.ctrl.down else (0,255,0)
                    cv2.line(fr, (ix,iy), (tx,ty), clr, 3)

        if not left_found:
            # lift click if no left hand present
            self.ctrl.update((0,0),(9999,9999))

        # display preview
        h2, w2, _ = fr.shape
        img = QImage(fr.data, w2, h2, 3*w2, QImage.Format_RGB888).rgbSwapped()
        self.video.setPixmap(QPixmap.fromImage(img))

    def closeEvent(self, event):
        self.stop_tracking()
        super().closeEvent(event)