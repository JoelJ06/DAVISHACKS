import cv2
import mediapipe as mp
import numpy as np
import pyautogui

from PyQt5.QtWidgets import QWidget, QLabel, QVBoxLayout
from PyQt5.QtCore    import Qt, QTimer
from PyQt5.QtGui     import QImage, QPixmap

class ClickController:
    def __init__(self):
        self.down = False
        self.thresh = 40
    def update(self, tp, ip):
        d = np.hypot(tp[0]-ip[0], tp[1]-ip[1])
        prev = self.down
        self.down = d < self.thresh
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
        self.cap   = None
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._frame)

        self.ctrl  = ClickController()
        self.sw, self.sh = pyautogui.size()

    def showEvent(self,e):
        # start camera
        self.cap   = cv2.VideoCapture(0)
        self.hands = mp.solutions.hands.Hands(
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5)
        self.timer.start(30)
        super().showEvent(e)

    def hideEvent(self,e):
        # stop camera
        self.timer.stop()
        self.cap.release()
        super().hideEvent(e)

    def _frame(self):
        ret,fr = self.cap.read()
        if not ret: return
        fr = cv2.flip(fr,1)  # mirror to match eye widget

        rgb = cv2.cvtColor(fr, cv2.COLOR_BGR2RGB)
        res = self.hands.process(rgb)

        left_found = False
        h,w,_ = fr.shape

        if res.multi_hand_landmarks and res.multi_handedness:
            for lm,hd in zip(res.multi_hand_landmarks, res.multi_handedness):
                label = hd.classification[0].label
                ip = lm.landmark[8]
                tp = lm.landmark[4]
                ix,iy = int(ip.x*w), int(ip.y*h)
                tx,ty = int(tp.x*w), int(tp.y*h)
                mp.solutions.drawing_utils.draw_landmarks(
                    fr, lm, mp.solutions.hands.HAND_CONNECTIONS)

                if label=="Left":
                    # mirror: left label→ cursor
                    sx = int(ix*self.sw/w)
                    sy = int(iy*self.sh/h)
                    pyautogui.moveTo(sx,sy)
                    cv2.circle(fr,(ix,iy),10,(0,255,0),-1)
                    left_found=True
                else:
                    # right label→ click
                    self.ctrl.update((tx,ty),(ix,iy))
                    clr = (0,0,255) if self.ctrl.down else (0,255,0)
                    cv2.line(fr,(ix,iy),(tx,ty),clr,3)

        if not left_found:
            self.ctrl.update((0,0),(9999,9999))

        # preview
        h2,w2,_=fr.shape
        img=QImage(fr.data,w2,h2,3*w2,QImage.Format_RGB888).rgbSwapped()
        self.video.setPixmap(QPixmap.fromImage(img))

    def closeEvent(self,e):
        if self.cap: self.cap.release()
        super().closeEvent(e)